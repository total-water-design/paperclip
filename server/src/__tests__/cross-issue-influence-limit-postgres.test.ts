import { randomUUID } from "node:crypto";
import { and, eq } from "drizzle-orm";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import {
  activityLog,
  agents,
  companies,
  createDb,
  heartbeatRuns,
  issues,
} from "@paperclipai/db";
import {
  getEmbeddedPostgresTestSupport,
  startEmbeddedPostgresTestDatabase,
} from "./helpers/embedded-postgres.js";
import {
  CROSS_ISSUE_INFLUENCE_ENFORCE_AT,
  observeCrossIssueInfluence,
} from "../services/cross-issue-influence-limit.js";

const embeddedPostgresSupport = await getEmbeddedPostgresTestSupport();
const describeEmbeddedPostgres = embeddedPostgresSupport.supported ? describe : describe.skip;

describeEmbeddedPostgres("cross-issue influence limit PostgreSQL serialization", () => {
  let db!: ReturnType<typeof createDb>;
  let tempDb: Awaited<ReturnType<typeof startEmbeddedPostgresTestDatabase>> | null = null;

  beforeAll(async () => {
    tempDb = await startEmbeddedPostgresTestDatabase("paperclip-cross-issue-cap-");
    db = createDb(tempDb.connectionString);
  }, 20_000);

  afterEach(async () => {
    await db.delete(activityLog);
    await db.delete(issues);
    await db.delete(heartbeatRuns);
    await db.delete(agents);
    await db.delete(companies);
  });

  async function seedRun(input: {
    companyId?: string;
    agentId?: string;
    runId?: string;
    contextSnapshot?: unknown;
  } = {}) {
    const companyId = input.companyId ?? randomUUID();
    const agentId = input.agentId ?? randomUUID();
    const runId = input.runId ?? randomUUID();
    await db.insert(companies).values({
      id: companyId,
      name: "Paperclip",
      issuePrefix: `C${companyId.replace(/-/g, "").slice(0, 6).toUpperCase()}`,
      defaultResponsibleUserId: "board-user",
    });
    await db.insert(agents).values({
      id: agentId,
      companyId,
      name: "Cross-issue Coder",
      role: "engineer",
      adapterType: "codex_local",
      adapterConfig: {},
      runtimeConfig: {},
      permissions: {},
    });
    await db.insert(heartbeatRuns).values({
      id: runId,
      companyId,
      agentId,
      status: "running",
      responsibleUserId: "board-user",
      contextSnapshot: input.contextSnapshot ?? { trigger: "heartbeat_timer", reason: "interval_elapsed" },
    });
    return { companyId, agentId, runId };
  }

  async function insertIssue(input: {
    companyId: string;
    assigneeAgentId: string;
    checkoutRunId?: string | null;
    identifier?: string;
  }) {
    const id = randomUUID();
    await db.insert(issues).values({
      id,
      companyId: input.companyId,
      title: "Source issue",
      status: "in_progress",
      priority: "medium",
      assigneeAgentId: input.assigneeAgentId,
      checkoutRunId: input.checkoutRunId ?? null,
      executionRunId: input.checkoutRunId ?? null,
      identifier: input.identifier ?? null,
    });
    return id;
  }

  const attempt = (input: { companyId: string; agentId: string; runId: string }, targetIssueId = randomUUID()) =>
    observeCrossIssueInfluence(db, {
      ...input,
      targetIssueId,
      targetIssueIdentifier: "CAP-2",
      kind: "comment",
      now: CROSS_ISSUE_INFLUENCE_ENFORCE_AT,
    });

  it("keeps scoped snapshot attribution unchanged", async () => {
    const sourceIssueId = randomUUID();
    const run = await seedRun({ contextSnapshot: { issueId: sourceIssueId } });
    const checkoutIssueId = await insertIssue({ ...run, assigneeAgentId: run.agentId, checkoutRunId: run.runId });

    await attempt(run);

    const [recorded] = await db.select({ details: activityLog.details }).from(activityLog);
    expect(recorded?.details).toMatchObject({ sourceIssueId });
    expect(recorded?.details).not.toMatchObject({ sourceIssueId: checkoutIssueId });
  });

  it("attributes an unscoped timer run from its unique same-agent checkout", async () => {
    const run = await seedRun();
    const sourceIssueId = await insertIssue({ ...run, assigneeAgentId: run.agentId, checkoutRunId: run.runId });

    await expect(attempt(run)).resolves.toMatchObject({ allowed: true });
    const [recorded] = await db.select({ details: activityLog.details }).from(activityLog);
    expect(recorded?.details).toMatchObject({ sourceIssueId });
  });

  it("rejects an unscoped run without a checkout", async () => {
    const run = await seedRun();
    await expect(attempt(run)).rejects.toMatchObject({ status: 403 });
  });

  it("rejects checkout linkage owned by another agent", async () => {
    const run = await seedRun();
    const otherAgentId = randomUUID();
    await db.insert(agents).values({
      id: otherAgentId,
      companyId: run.companyId,
      name: "Other agent",
      role: "engineer",
      adapterType: "codex_local",
      adapterConfig: {},
      runtimeConfig: {},
      permissions: {},
    });
    await insertIssue({ ...run, assigneeAgentId: otherAgentId, checkoutRunId: run.runId });
    await expect(attempt(run)).rejects.toMatchObject({ status: 403 });
  });

  it("rejects checkout linkage from another company", async () => {
    const run = await seedRun();
    const other = await seedRun();
    await insertIssue({
      companyId: other.companyId,
      assigneeAgentId: other.agentId,
      checkoutRunId: run.runId,
    });
    await expect(attempt(run)).rejects.toMatchObject({ status: 403 });
  });

  it("rejects ambiguous same-agent checkout linkage", async () => {
    const run = await seedRun();
    await insertIssue({ ...run, assigneeAgentId: run.agentId, checkoutRunId: run.runId });
    await insertIssue({ ...run, assigneeAgentId: run.agentId, checkoutRunId: run.runId });
    await expect(attempt(run)).rejects.toMatchObject({ status: 403 });
  });

  it("does not let an arbitrary run header spoof checkout attribution", async () => {
    const run = await seedRun();
    await insertIssue({ ...run, assigneeAgentId: run.agentId, checkoutRunId: run.runId });
    await expect(attempt({ ...run, runId: randomUUID() })).rejects.toMatchObject({ status: 403 });
  });

  afterAll(async () => {
    await tempDb?.cleanup();
  });

  it("allows exactly one of concurrent attempts 20 and 21", async () => {
    const companyId = randomUUID();
    const agentId = randomUUID();
    const runId = randomUUID();
    const sourceIssueId = randomUUID();
    const targetIssueId = randomUUID();

    await db.insert(companies).values({
      id: companyId,
      name: "Paperclip",
      issuePrefix: `C${companyId.replace(/-/g, "").slice(0, 6).toUpperCase()}`,
      defaultResponsibleUserId: "board-user",
    });
    await db.insert(agents).values({
      id: agentId,
      companyId,
      name: "Concurrent Coder",
      role: "engineer",
      adapterType: "codex_local",
      adapterConfig: {},
      runtimeConfig: {},
      permissions: {},
    });
    await db.insert(heartbeatRuns).values({
      id: runId,
      companyId,
      agentId,
      status: "running",
      responsibleUserId: "board-user",
      contextSnapshot: { issueId: sourceIssueId },
    });
    await db.insert(activityLog).values(
      Array.from({ length: 18 }, () => ({
        companyId,
        actorType: "agent" as const,
        actorId: agentId,
        agentId,
        runId,
        action: "issue.cross_issue_influence_observed",
        entityType: "issue",
        entityId: targetIssueId,
      })),
    );

    const input = {
      companyId,
      runId,
      agentId,
      targetIssueId,
      targetIssueIdentifier: "CAP-2",
      kind: "comment" as const,
      now: CROSS_ISSUE_INFLUENCE_ENFORCE_AT,
    };
    // A comment, a PATCH, and an issue-thread interaction resolution race for the
    // last slot of the shared budget: the row lock must let exactly one of 19/20
    // through per attempt and fail the twenty-first closed.
    const decisions = await Promise.all([
      observeCrossIssueInfluence(db, input),
      observeCrossIssueInfluence(db, { ...input, kind: "update" }),
      observeCrossIssueInfluence(db, { ...input, kind: "interaction_resolution" }),
    ]);

    expect(decisions.map((decision) => decision?.allowed).sort()).toEqual([false, true, true]);
    expect(decisions.map((decision) => decision?.count).sort((a, b) => Number(a) - Number(b)))
      .toEqual([19, 20, 21]);

    const recorded = await db
      .select({ action: activityLog.action })
      .from(activityLog)
      .where(and(eq(activityLog.companyId, companyId), eq(activityLog.runId, runId)));
    expect(recorded.filter((row) => row.action === "issue.cross_issue_influence_observed")).toHaveLength(20);
    expect(recorded.filter((row) => row.action === "issue.cross_issue_influence_cap_rejected")).toHaveLength(1);
  });
});
