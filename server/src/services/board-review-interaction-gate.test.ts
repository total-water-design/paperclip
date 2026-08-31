import { randomUUID } from "node:crypto";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import {
  companies,
  createDb,
  issueThreadInteractions,
  issues,
} from "@paperclipai/db";
import { eq, inArray } from "drizzle-orm";
import {
  boardReviewInteractionGateViolation,
  reconcileBoardReviewInteractionGate,
} from "./board-review-interaction-gate.js";
import {
  getEmbeddedPostgresTestSupport,
  startEmbeddedPostgresTestDatabase,
} from "../__tests__/helpers/embedded-postgres.js";

const validIssue = {
  status: "in_review",
  assigneeAgentId: null,
  assigneeUserId: "board-user",
  reviewPolicy: null,
};

describe("Board review interaction gate", () => {
  it("allows ordinary interactions outside the human-only policy", () => {
    expect(boardReviewInteractionGateViolation({
      issue: { ...validIssue, status: "in_progress", assigneeUserId: null },
      kind: "ask_user_questions",
      resolverPolicy: "anyone",
    })).toBeNull();
  });

  it.each([
    [{ ...validIssue, status: "blocked" }, "human_only interactions require issue status in_review"],
    [{ ...validIssue, assigneeUserId: null }, "human_only interactions require an exclusively Board-assigned issue"],
    [{ ...validIssue, assigneeAgentId: "agent-id" }, "human_only interactions require an exclusively Board-assigned issue"],
  ])("rejects an invalid human-only issue state", (issue, message) => {
    expect(boardReviewInteractionGateViolation({
      issue,
      kind: "request_confirmation",
      resolverPolicy: "human_only",
    })).toBe(message);
  });

  it("enforces the gate inherited from issue review policy", () => {
    expect(boardReviewInteractionGateViolation({
      issue: { ...validIssue, status: "todo", reviewPolicy: "human_only" },
      kind: "request_confirmation",
    })).toContain("in_review");
  });

  it("accepts compatibility board_only only for a valid Board review", () => {
    expect(boardReviewInteractionGateViolation({
      issue: validIssue,
      kind: "request_item_verdicts",
      resolverPolicy: "board_only",
    })).toBeNull();
  });

  it("rejects an unknown action class", () => {
    expect(boardReviewInteractionGateViolation({
      issue: validIssue,
      kind: "arbitrary_action",
      resolverPolicy: "human_only",
    })).toContain("approved Board action class");
  });
});

const embeddedPostgresSupport = await getEmbeddedPostgresTestSupport();
const describeEmbeddedPostgres = embeddedPostgresSupport.supported ? describe : describe.skip;

describeEmbeddedPostgres("Board review interaction reconciler", () => {
  let db!: ReturnType<typeof createDb>;
  let tempDb: Awaited<ReturnType<typeof startEmbeddedPostgresTestDatabase>> | null = null;

  beforeAll(async () => {
    tempDb = await startEmbeddedPostgresTestDatabase("paperclip-board-review-gate-");
    db = createDb(tempDb.connectionString);
  }, 30_000);

  afterEach(async () => {
    await db.delete(issueThreadInteractions);
    await db.delete(issues);
    await db.delete(companies);
  });

  afterAll(async () => {
    await tempDb?.cleanup();
  });

  it("retroactively withdraws invalid cards, clears stopped Board assignments, and preserves valid/history fields", async () => {
    const companyId = randomUUID();
    await db.insert(companies).values({
      id: companyId,
      name: "Board gate reconciliation",
      issuePrefix: `BR${randomUUID().slice(0, 6).toUpperCase()}`,
    });

    const seededIssues = [
      { title: "Invalid card", status: "in_progress", assigneeUserId: "board-user" },
      { title: "Valid review", status: "in_review", assigneeUserId: "board-user" },
      { title: "Stopped Board work", status: "blocked", assigneeUserId: "board-user" },
      { title: "Active Board work", status: "todo", assigneeUserId: "board-user" },
    ].map((row) => ({ id: randomUUID(), companyId, priority: "medium", ...row }));
    await db.insert(issues).values(seededIssues);

    const invalidInteractionId = randomUUID();
    const validInteractionId = randomUUID();
    const createdAt = new Date("2026-08-31T20:00:00.000Z");
    const payload = { version: 1, prompt: "Preserve this evidence" };
    await db.insert(issueThreadInteractions).values([
      {
        id: invalidInteractionId,
        companyId,
        issueId: seededIssues[0]!.id,
        kind: "request_confirmation",
        effectiveResolverPolicy: "human_only",
        requestedResolverPolicy: "human_only",
        payload,
        createdAt,
      },
      {
        id: validInteractionId,
        companyId,
        issueId: seededIssues[1]!.id,
        kind: "request_confirmation",
        effectiveResolverPolicy: "human_only",
        requestedResolverPolicy: "human_only",
        payload: { version: 1, prompt: "Valid Board review" },
      },
    ]);

    const beforePending = await db.select({ id: issueThreadInteractions.id })
      .from(issueThreadInteractions)
      .where(eq(issueThreadInteractions.status, "pending"));
    const beforeBoardAssigned = await db.select({ id: issues.id })
      .from(issues)
      .where(eq(issues.assigneeUserId, "board-user"));

    const result = await reconcileBoardReviewInteractionGate(db);

    const afterPending = await db.select({ id: issueThreadInteractions.id })
      .from(issueThreadInteractions)
      .where(eq(issueThreadInteractions.status, "pending"));
    const afterBoardAssigned = await db.select({ id: issues.id })
      .from(issues)
      .where(eq(issues.assigneeUserId, "board-user"));
    const interactions = await db.select().from(issueThreadInteractions)
      .where(inArray(issueThreadInteractions.id, [invalidInteractionId, validInteractionId]));
    const invalid = interactions.find((row) => row.id === invalidInteractionId)!;
    const valid = interactions.find((row) => row.id === validInteractionId)!;
    const issueRows = await db.select().from(issues)
      .where(inArray(issues.id, seededIssues.map((row) => row.id)));

    expect({ beforePending: beforePending.length, afterPending: afterPending.length }).toEqual({
      beforePending: 2,
      afterPending: 1,
    });
    expect({ beforeBoardAssigned: beforeBoardAssigned.length, afterBoardAssigned: afterBoardAssigned.length }).toEqual({
      beforeBoardAssigned: 4,
      afterBoardAssigned: 3,
    });
    expect(result).toEqual({
      cancelledInteractionIds: [invalidInteractionId],
      removedBoardAssignmentIssueIds: [seededIssues[2]!.id],
    });
    expect(invalid).toMatchObject({ status: "withdrawn", payload, createdAt });
    expect(invalid.resolvedAt).toBeInstanceOf(Date);
    expect(valid.status).toBe("pending");
    expect(issueRows.find((row) => row.id === seededIssues[2]!.id)).toMatchObject({
      title: "Stopped Board work",
      assigneeUserId: null,
    });
    expect(issueRows.find((row) => row.id === seededIssues[3]!.id)?.assigneeUserId).toBe("board-user");

    await expect(reconcileBoardReviewInteractionGate(db)).resolves.toEqual({
      cancelledInteractionIds: [],
      removedBoardAssignmentIssueIds: [],
    });
  });
});
