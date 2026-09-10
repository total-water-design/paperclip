import { randomUUID } from "node:crypto";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import {
  agents,
  approvals,
  companies,
  createDb,
  issueApprovals,
  issues,
} from "@paperclipai/db";
import { approvalService } from "../services/approvals.js";
import { boardApprovalRequestIdentity } from "../services/approval-governance.js";
import {
  getEmbeddedPostgresTestSupport,
  startEmbeddedPostgresTestDatabase,
} from "./helpers/embedded-postgres.js";

const embeddedPostgresSupport = await getEmbeddedPostgresTestSupport();
const describeEmbeddedPostgres = embeddedPostgresSupport.supported ? describe : describe.skip;

describeEmbeddedPostgres("approval service semantic reuse", () => {
  let db!: ReturnType<typeof createDb>;
  let tempDb: Awaited<ReturnType<typeof startEmbeddedPostgresTestDatabase>> | null = null;

  beforeAll(async () => {
    tempDb = await startEmbeddedPostgresTestDatabase("paperclip-approval-reuse-");
    db = createDb(tempDb.connectionString);
  }, 30_000);

  afterEach(async () => {
    await db.delete(issueApprovals);
    await db.delete(approvals);
    await db.delete(issues);
    await db.delete(agents);
    await db.delete(companies);
  });

  afterAll(async () => {
    await tempDb?.cleanup();
  });

  async function seed() {
    const company = await db.insert(companies).values({
      name: `Approval Reuse ${randomUUID()}`,
      issuePrefix: `AR${randomUUID().slice(0, 6).toUpperCase()}`,
    }).returning().then((rows) => rows[0]!);
    const agent = await db.insert(agents).values({
      companyId: company.id,
      name: "Approval requester",
      role: "manager",
      status: "idle",
    }).returning().then((rows) => rows[0]!);
    const issue = await db.insert(issues).values({
      companyId: company.id,
      title: "Release candidate",
      status: "in_progress",
      assigneeAgentId: agent.id,
    }).returning().then((rows) => rows[0]!);
    return { company, agent, issue };
  }

  it("atomically creates one approval for concurrent equivalent requests", async () => {
    const { company, agent, issue } = await seed();
    const payload = {
      title: "Approve production deployment",
      action: "deploy",
      scope: "alpha",
      candidateSha: "0123456789abcdef0123456789abcdef01234567",
    };
    const identity = boardApprovalRequestIdentity({
      type: "request_board_approval",
      payload,
      issueIds: [issue.id],
    });
    const input = {
      companyId: company.id,
      data: {
        type: "request_board_approval",
        requestedByAgentId: agent.id,
        status: "pending",
        payload,
      },
      issueIds: [issue.id],
      linkedByAgentId: agent.id,
      openDeduplicationKey: identity.openDeduplicationKey,
      authorizationFingerprint: identity.authorizationFingerprint,
      reuseApprovedAuthorization: identity.exactIdentityEstablished,
    };

    const results = await Promise.all(Array.from({ length: 4 }, () =>
      approvalService(db).createOrReuseBoardApproval(input),
    ));

    expect(results.filter((result) => result.created)).toHaveLength(1);
    expect(new Set(results.map((result) => result.approval.id))).toHaveLength(1);
    expect(await db.select().from(approvals)).toHaveLength(1);
    expect(await db.select().from(issueApprovals)).toHaveLength(1);
  });

  it("reuses a legacy pending request with the same issue and action title", async () => {
    const { company, agent, issue } = await seed();
    const legacy = await db.insert(approvals).values({
      companyId: company.id,
      type: "request_board_approval",
      requestedByAgentId: agent.id,
      status: "pending",
      payload: {
        title: "Authorize bounded collection",
        summary: "First wording for the same bounded operation.",
      },
    }).returning().then((rows) => rows[0]!);
    await db.insert(issueApprovals).values({
      companyId: company.id,
      issueId: issue.id,
      approvalId: legacy.id,
      linkedByAgentId: agent.id,
    });

    const payload = {
      title: "Authorize bounded collection",
      summary: "Reworded supporting detail for the same bounded operation.",
    };
    const identity = boardApprovalRequestIdentity({
      type: "request_board_approval",
      payload,
      issueIds: [issue.id],
    });
    const result = await approvalService(db).createOrReuseBoardApproval({
      companyId: company.id,
      data: {
        type: "request_board_approval",
        requestedByAgentId: agent.id,
        status: "pending",
        payload,
      },
      issueIds: [issue.id],
      linkedByAgentId: agent.id,
      openDeduplicationKey: identity.openDeduplicationKey,
      authorizationFingerprint: identity.authorizationFingerprint,
      reuseApprovedAuthorization: identity.exactIdentityEstablished,
    });

    expect(result).toMatchObject({ created: false, approval: { id: legacy.id } });
    expect(await db.select().from(approvals)).toHaveLength(1);
  });

  it("requires action, bounded scope, and immutable identity to reuse an approved authorization", async () => {
    const { company, agent, issue } = await seed();
    const approvedPayload = {
      action: "deploy",
      environment: "alpha",
      candidateSha: "0123456789abcdef0123456789abcdef01234567",
      idempotencyKey: "original-request",
    };
    const approved = await db.insert(approvals).values({
      companyId: company.id,
      type: "request_board_approval",
      requestedByAgentId: agent.id,
      status: "approved",
      payload: approvedPayload,
    }).returning().then((rows) => rows[0]!);
    await db.insert(issueApprovals).values({
      companyId: company.id,
      issueId: issue.id,
      approvalId: approved.id,
      linkedByAgentId: agent.id,
    });

    const request = async (payload: Record<string, unknown>) => {
      const identity = boardApprovalRequestIdentity({
        type: "request_board_approval",
        payload,
        issueIds: [issue.id],
      });
      return approvalService(db).createOrReuseBoardApproval({
        companyId: company.id,
        data: {
          type: "request_board_approval",
          requestedByAgentId: agent.id,
          status: "pending",
          payload,
        },
        issueIds: [issue.id],
        linkedByAgentId: agent.id,
        openDeduplicationKey: identity.openDeduplicationKey,
        authorizationFingerprint: identity.authorizationFingerprint,
        reuseApprovedAuthorization: identity.exactIdentityEstablished,
      });
    };

    const keyOnly = await request({ idempotencyKey: "original-request" });
    expect(keyOnly.created).toBe(true);
    expect(keyOnly.approval.id).not.toBe(approved.id);

    const exact = await request({ ...approvedPayload, idempotencyKey: "new-request" });
    expect(exact).toMatchObject({ created: false, approval: { id: approved.id } });

    const differentSha = await request({
      ...approvedPayload,
      idempotencyKey: "another-request",
      candidateSha: "abcdef0123456789abcdef0123456789abcdef01",
    });
    expect(differentSha.created).toBe(true);
    expect(differentSha.approval.id).not.toBe(approved.id);
  });

  it("enforces one keyed open Board approval at the database boundary", async () => {
    const { company, agent } = await seed();
    const key = "a".repeat(64);
    await db.insert(approvals).values({
      companyId: company.id,
      type: "request_board_approval",
      requestedByAgentId: agent.id,
      status: "pending",
      payload: { title: "Authorize production deployment" },
      openDeduplicationKey: key,
    });
    await expect(db.insert(approvals).values({
      companyId: company.id,
      type: "request_board_approval",
      requestedByAgentId: agent.id,
      status: "revision_requested",
      payload: { title: "Authorize production deployment again" },
      openDeduplicationKey: key,
    })).rejects.toThrow();
  });

  it("returns the oldest canonical legacy record for the named duplicate pair", async () => {
    const { company, agent, issue } = await seed();
    const payloads = [
      {
        id: "544365d1-e653-4c55-a290-fca919ffbf1f",
        title: "Authorize bounded read-only staged-host topology collection",
        summary: "Original operational fixture wording",
      },
      {
        id: "d93fefee-488a-4d93-a43a-7199d88d0ab9",
        title: "Authorize bounded read-only staged-host topology collection",
        summary: "Reworded operational fixture support",
      },
    ];
    for (const [index, payload] of payloads.entries()) {
      const row = await db.insert(approvals).values({
        id: payload.id,
        companyId: company.id,
        type: "request_board_approval",
        requestedByAgentId: agent.id,
        status: "pending",
        payload,
        createdAt: new Date(Date.UTC(2026, 0, index + 1)),
      }).returning().then((rows) => rows[0]!);
      await db.insert(issueApprovals).values({
        companyId: company.id,
        issueId: issue.id,
        approvalId: row.id,
        linkedByAgentId: agent.id,
      });
    }
    const payload = {
      title: "Authorize bounded read-only staged-host topology collection",
      summary: "A third wording must not create a third open record",
    };
    const identity = boardApprovalRequestIdentity({
      type: "request_board_approval",
      payload,
      issueIds: [issue.id],
    });
    const result = await approvalService(db).createOrReuseBoardApproval({
      companyId: company.id,
      data: { type: "request_board_approval", requestedByAgentId: agent.id, status: "pending", payload },
      issueIds: [issue.id],
      linkedByAgentId: agent.id,
      openDeduplicationKey: identity.openDeduplicationKey,
      authorizationFingerprint: identity.authorizationFingerprint,
      reuseApprovedAuthorization: false,
    });
    expect(result).toMatchObject({ created: false, approval: { id: payloads[0]!.id } });
    expect(await db.select().from(approvals)).toHaveLength(2);
  });

  it("cancels the named stale fixture once without writing Board decision fields", async () => {
    const { company, agent } = await seed();
    const stale = await db.insert(approvals).values({
      id: "eb43b4e8-65c0-4cc8-b2c6-917ccf71c1fc",
      companyId: company.id,
      type: "request_board_approval",
      requestedByAgentId: agent.id,
      status: "revision_requested",
      payload: { title: "Authorize bounded TOT-1912 smoke probes" },
      decisionNote: "Board requested revision",
      decidedByUserId: "board-user",
      decidedAt: new Date("2026-01-01T00:00:00Z"),
    }).returning().then((rows) => rows[0]!);
    const results = await Promise.all([
      approvalService(db).cancel(stale.id, "Stale request", { agentId: agent.id }),
      approvalService(db).cancel(stale.id, "Stale request", { agentId: agent.id }),
    ]);
    expect(results.filter((result) => result.applied)).toHaveLength(1);
    expect(results.every((result) => result.approval.status === "cancelled")).toBe(true);
    const current = await db.select().from(approvals).then((rows) => rows[0]!);
    expect(current).toMatchObject({
      cancellationReason: "Stale request",
      cancelledByAgentId: agent.id,
      decisionNote: "Board requested revision",
      decidedByUserId: "board-user",
    });
    expect(current.cancelledAt).toBeInstanceOf(Date);
    expect(current.decidedAt?.toISOString()).toBe("2026-01-01T00:00:00.000Z");
  });

  it("does not let cancellation override an approved decision", async () => {
    const { company, agent } = await seed();
    const approved = await db.insert(approvals).values({
      companyId: company.id,
      type: "request_board_approval",
      requestedByAgentId: agent.id,
      status: "approved",
      payload: {},
    }).returning().then((rows) => rows[0]!);
    await expect(approvalService(db).cancel(approved.id, "Too late", { agentId: agent.id }))
      .rejects.toThrow("Only pending or revision requested approvals can be cancelled");
  });

  it("rejects resubmission that would collide with a canonical open request", async () => {
    const { company, agent, issue } = await seed();
    const payload = { title: "Authorize production deployment", environment: "alpha" };
    const rows = await db.insert(approvals).values([
      {
        companyId: company.id,
        type: "request_board_approval",
        requestedByAgentId: agent.id,
        status: "revision_requested",
        payload: { title: "Needs revision" },
      },
      {
        companyId: company.id,
        type: "request_board_approval",
        requestedByAgentId: agent.id,
        status: "pending",
        payload,
      },
    ]).returning();
    await db.insert(issueApprovals).values(rows.map((approval) => ({
      companyId: company.id,
      issueId: issue.id,
      approvalId: approval.id,
      linkedByAgentId: agent.id,
    })));
    await expect(approvalService(db).resubmit(rows[0]!.id, payload))
      .rejects.toThrow(`Equivalent open Board approval ${rows[1]!.id} already exists`);
  });
});
