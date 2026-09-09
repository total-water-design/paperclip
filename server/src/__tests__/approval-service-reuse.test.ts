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
      fingerprint: identity.fingerprint,
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
      fingerprint: identity.fingerprint,
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
        fingerprint: identity.fingerprint,
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
});
