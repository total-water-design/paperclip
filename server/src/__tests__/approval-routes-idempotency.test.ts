import express from "express";
import request from "supertest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockApprovalService = vi.hoisted(() => ({
  list: vi.fn(),
  getById: vi.fn(),
  create: vi.fn(),
  createOrReuseBoardApproval: vi.fn(),
  cancel: vi.fn(),
  approve: vi.fn(),
  reject: vi.fn(),
  requestRevision: vi.fn(),
  resubmit: vi.fn(),
  listComments: vi.fn(),
  addComment: vi.fn(),
}));

const mockHeartbeatService = vi.hoisted(() => ({
  wakeup: vi.fn(),
}));

const mockIssueApprovalService = vi.hoisted(() => ({
  listIssuesForApproval: vi.fn(),
  linkManyForApproval: vi.fn(),
}));

const mockIssueService = vi.hoisted(() => ({
  listReviewAttention: vi.fn(),
}));

const mockSecretService = vi.hoisted(() => ({
  normalizeHireApprovalPayloadForPersistence: vi.fn(),
}));

const mockLogActivity = vi.hoisted(() => vi.fn());
const mockAccessService = vi.hoisted(() => ({
  decide: vi.fn(),
}));

function registerModuleMocks() {
  vi.doMock("../services/index.js", () => ({
    accessService: () => mockAccessService,
    approvalService: () => mockApprovalService,
    heartbeatService: () => mockHeartbeatService,
    issueApprovalService: () => mockIssueApprovalService,
    logActivity: mockLogActivity,
    secretService: () => mockSecretService,
  }));
  vi.doMock("../services/issues.js", () => ({ issueService: () => mockIssueService }));
}

async function createApp(actorOverrides: Record<string, unknown> = {}) {
  const [{ errorHandler }, { approvalRoutes }] = await Promise.all([
    import("../middleware/index.js"),
    import("../routes/approvals.js"),
  ]);
  const app = express();
  app.use(express.json());
  app.use((req, _res, next) => {
    (req as any).actor = {
      type: "board",
      userId: "user-1",
      companyIds: ["company-1"],
      source: "session",
      isInstanceAdmin: false,
      ...actorOverrides,
    };
    next();
  });
  app.use("/api", approvalRoutes(createRouteDb()));
  app.use(errorHandler);
  return app;
}

function createRouteDb(contextSnapshot: Record<string, unknown> = {}, runId = "run-1", agentId = "agent-1") {
  const runRows = [{
    id: runId,
    companyId: "company-1",
    agentId,
    contextSnapshot,
  }];
  return {
    select: vi.fn((selection: Record<string, unknown> = {}) => ({
      from: vi.fn(() => ({
        where: vi.fn(() => ({
          then: async (resolve: (rows: unknown[]) => unknown) => resolve(
            Object.keys(selection).includes("contextSnapshot")
              ? runRows
              : Object.keys(selection).includes("role")
                ? [{ id: agentId, companyId: "company-1", role: contextSnapshot.agentRole ?? "ceo" }]
                : [],
          ),
        })),
      })),
    })),
  } as any;
}

async function createAgentApp(options: { runId?: string; contextSnapshot?: Record<string, unknown> } = {}) {
  const [{ errorHandler }, { approvalRoutes }] = await Promise.all([
    import("../middleware/index.js"),
    import("../routes/approvals.js"),
  ]);
  const app = express();
  app.use(express.json());
  app.use((req, _res, next) => {
    (req as any).actor = {
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      runId: options.runId ?? "run-1",
      source: "api_key",
      isInstanceAdmin: false,
    };
    next();
  });
  app.use("/api", approvalRoutes(createRouteDb(options.contextSnapshot, options.runId ?? "run-1")));
  app.use(errorHandler);
  return app;
}

describe("approval routes idempotent retries", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.doUnmock("../services/index.js");
    vi.doUnmock("../routes/approvals.js");
    vi.doUnmock("../routes/authz.js");
    vi.doUnmock("../services/issues.js");
    vi.doUnmock("../middleware/index.js");
    registerModuleMocks();
    vi.clearAllMocks();
    mockApprovalService.list.mockReset();
    mockApprovalService.getById.mockReset();
    mockApprovalService.create.mockReset();
    mockApprovalService.createOrReuseBoardApproval.mockReset();
    mockApprovalService.cancel.mockReset();
    mockApprovalService.approve.mockReset();
    mockApprovalService.reject.mockReset();
    mockApprovalService.requestRevision.mockReset();
    mockApprovalService.resubmit.mockReset();
    mockApprovalService.listComments.mockReset();
    mockApprovalService.addComment.mockReset();
    mockHeartbeatService.wakeup.mockReset();
    mockIssueApprovalService.listIssuesForApproval.mockReset();
    mockIssueApprovalService.linkManyForApproval.mockReset();
    mockIssueService.listReviewAttention.mockReset();
    mockSecretService.normalizeHireApprovalPayloadForPersistence.mockReset();
    mockLogActivity.mockReset();
    mockAccessService.decide.mockReset();
    mockAccessService.decide.mockResolvedValue({
      allowed: true,
      action: "company_scope:read",
      reason: "allow_test",
      explanation: "Allowed by test mock.",
    });
    mockHeartbeatService.wakeup.mockResolvedValue({ id: "wake-1" });
    mockIssueApprovalService.listIssuesForApproval.mockResolvedValue([{ id: "issue-1" }]);
    mockIssueService.listReviewAttention.mockResolvedValue(new Map([
      ["issue-1", { state: "stalled" }],
    ]));
    mockLogActivity.mockResolvedValue(undefined);
  });

  it("does not emit duplicate approval side effects when approve is already resolved", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-1",
      companyId: "company-1",
      type: "hire_agent",
      status: "approved",
      payload: {},
      requestedByAgentId: "agent-1",
    });
    mockApprovalService.approve.mockResolvedValue({
      approval: {
        id: "approval-1",
        companyId: "company-1",
        type: "hire_agent",
        status: "approved",
        payload: {},
        requestedByAgentId: "agent-1",
      },
      applied: false,
    });

    const res = await request(await createApp())
      .post("/api/approvals/approval-1/approve")
      .send({});

    expect(res.status).toBe(200);
    expect(mockIssueApprovalService.listIssuesForApproval).not.toHaveBeenCalled();
    expect(mockHeartbeatService.wakeup).not.toHaveBeenCalled();
    expect(mockLogActivity).not.toHaveBeenCalled();
  });

  it("does not emit duplicate rejection logs when reject is already resolved", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-1",
      companyId: "company-1",
      type: "hire_agent",
      status: "rejected",
      payload: {},
    });
    mockApprovalService.reject.mockResolvedValue({
      approval: {
        id: "approval-1",
        companyId: "company-1",
        type: "hire_agent",
        status: "rejected",
        payload: {},
      },
      applied: false,
    });

    const res = await request(await createApp())
      .post("/api/approvals/approval-1/reject")
      .send({});

    expect(res.status).toBe(200);
    expect(mockLogActivity).not.toHaveBeenCalled();
  });

  it("rejects approval decisions for companies outside the caller scope", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-2",
      companyId: "company-2",
      type: "hire_agent",
      status: "pending",
      payload: {},
    });

    const res = await request(await createApp())
      .post("/api/approvals/approval-2/approve")
      .send({});

    expect(res.status).toBe(404);
    expect(res.body.error).toBe("Approval not found");
    expect(mockApprovalService.approve).not.toHaveBeenCalled();
  });

  it("rejects approval revision requests for companies outside the caller scope", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-3",
      companyId: "company-2",
      type: "hire_agent",
      status: "pending",
      payload: {},
    });

    const res = await request(await createApp())
      .post("/api/approvals/approval-3/request-revision")
      .send({ decisionNote: "Need changes" });

    expect(res.status).toBe(404);
    expect(res.body.error).toBe("Approval not found");
    expect(mockApprovalService.requestRevision).not.toHaveBeenCalled();
  });

  it("derives approval attribution from the authenticated actor on approve", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-4",
      companyId: "company-1",
      type: "hire_agent",
      status: "pending",
      payload: {},
      requestedByAgentId: null,
    });
    mockApprovalService.approve.mockResolvedValue({
      approval: {
        id: "approval-4",
        companyId: "company-1",
        type: "hire_agent",
        status: "approved",
        payload: {},
        requestedByAgentId: null,
      },
      applied: true,
    });

    const res = await request(await createApp())
      .post("/api/approvals/approval-4/approve")
      .send({ decidedByUserId: "forged-user", decisionNote: "ship it" });

    expect(res.status).toBe(200);
    expect(mockApprovalService.approve).toHaveBeenCalledWith("approval-4", "user-1", "ship it");
  });

  it("derives approval attribution from the authenticated actor on reject", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-5",
      companyId: "company-1",
      type: "hire_agent",
      status: "pending",
      payload: {},
    });
    mockApprovalService.reject.mockResolvedValue({
      approval: {
        id: "approval-5",
        companyId: "company-1",
        type: "hire_agent",
        status: "rejected",
        payload: {},
      },
      applied: true,
    });

    const res = await request(await createApp())
      .post("/api/approvals/approval-5/reject")
      .send({ decidedByUserId: "forged-user", decisionNote: "not now" });

    expect(res.status).toBe(200);
    expect(mockApprovalService.reject).toHaveBeenCalledWith("approval-5", "user-1", "not now");
  });

  it("derives approval attribution from the authenticated actor on request revision", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-6",
      companyId: "company-1",
      type: "hire_agent",
      status: "pending",
      payload: {},
    });
    mockApprovalService.requestRevision.mockResolvedValue({
      id: "approval-6",
      companyId: "company-1",
      type: "hire_agent",
      status: "revision_requested",
      payload: {},
    });

    const res = await request(await createApp())
      .post("/api/approvals/approval-6/request-revision")
      .send({ decidedByUserId: "forged-user", decisionNote: "Need changes" });

    expect(res.status).toBe(200);
    expect(mockApprovalService.requestRevision).toHaveBeenCalledWith(
      "approval-6",
      "user-1",
      "Need changes",
    );
  });

  it("wakes the original requester with semantic-only revision recovery context", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-revision",
      companyId: "company-1",
      type: "request_board_approval",
      status: "pending",
      payload: {},
      requestedByAgentId: "agent-1",
    });
    mockApprovalService.requestRevision.mockResolvedValue({
      id: "approval-revision",
      companyId: "company-1",
      type: "request_board_approval",
      status: "revision_requested",
      payload: {},
      requestedByAgentId: "agent-1",
      decisionNote: "Please revise the estimate.",
    });
    mockIssueApprovalService.listIssuesForApproval.mockResolvedValue([
      { id: "issue-1", identifier: "PAP-1", title: "Estimate", status: "in_progress" },
    ]);

    const res = await request(await createApp())
      .post("/api/approvals/approval-revision/request-revision")
      .send({ decisionNote: "Please revise the estimate." });

    expect(res.status).toBe(200);
    expect(mockHeartbeatService.wakeup).toHaveBeenCalledWith("agent-1", expect.objectContaining({
      reason: "approval_revision_requested",
      idempotencyKey: "approval-revision-requested:approval-revision",
      payload: expect.objectContaining({
        approvalId: "approval-revision",
        revisionDecision: "revision_requested",
        revisionNote: "Please revise the estimate.",
        issueIds: ["issue-1"],
        recoveryInstruction: expect.stringContaining("resubmit_approval only"),
      }),
    }));
    const wake = mockHeartbeatService.wakeup.mock.calls[0]?.[1];
    expect(JSON.stringify(wake)).not.toContain("/api/");
  });

  it("forbids a non-requester from resubmitting an approval", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-foreign-requester",
      companyId: "company-1",
      type: "request_board_approval",
      status: "revision_requested",
      payload: {},
      requestedByAgentId: "another-agent",
    });

    const res = await request(await createAgentApp())
      .post("/api/approvals/approval-foreign-requester/resubmit")
      .send({ payload: { revised: true } });

    expect(res.status).toBe(403);
    expect(res.body.error).toContain("Only requesting agent can resubmit");
    expect(mockApprovalService.resubmit).not.toHaveBeenCalled();
  });

  it("lets COS create a governed issue-linked Board approval request", async () => {
    const createdApproval = {
      id: "approval-1",
      companyId: "company-1",
      type: "request_board_approval",
      requestedByAgentId: "agent-1",
      requestedByUserId: null,
      status: "pending",
      payload: { title: "Approve hosting spend" },
      decisionNote: null,
      decidedByUserId: null,
      decidedAt: null,
      createdAt: new Date("2026-04-06T00:00:00.000Z"),
      updatedAt: new Date("2026-04-06T00:00:00.000Z"),
    };
    mockApprovalService.createOrReuseBoardApproval.mockResolvedValue({
      approval: createdApproval,
      created: true,
    });

    const res = await request(await createAgentApp())
      .post("/api/companies/company-1/approvals")
      .send({
        type: "request_board_approval",
        issueIds: ["00000000-0000-0000-0000-000000000001"],
        payload: { title: "Approve hosting spend" },
      });

    expect([200, 201], JSON.stringify(res.body)).toContain(res.status);
    expect(res.body).toMatchObject({
      companyId: "company-1",
      type: "request_board_approval",
      requestedByAgentId: "agent-1",
      requestedByUserId: null,
      status: "pending",
    });
    expect(mockSecretService.normalizeHireApprovalPayloadForPersistence).not.toHaveBeenCalled();
    expect(mockApprovalService.createOrReuseBoardApproval).toHaveBeenCalledWith(expect.objectContaining({
      companyId: "company-1",
      issueIds: ["00000000-0000-0000-0000-000000000001"],
      linkedByAgentId: "agent-1",
      openDeduplicationKey: expect.stringMatching(/^[0-9a-f]{64}$/),
      authorizationFingerprint: expect.stringMatching(/^[0-9a-f]{64}$/),
      reuseApprovedAuthorization: false,
    }));
    expect(mockIssueApprovalService.linkManyForApproval).not.toHaveBeenCalled();
    expect(mockLogActivity).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        companyId: "company-1",
        actorType: "agent",
        actorId: "agent-1",
        action: "approval.created",
      }),
    );
  });

  it("delegates the repeated TOT-3098 read-only topology request and creates zero approvals", async () => {
    const app = await createAgentApp();
    const body = {
      type: "request_board_approval",
      issueIds: ["00000000-0000-0000-0000-000000000001"],
      payload: {
        title: "Authorize bounded read-only staged-host topology collection",
        summary: "Collect effective unit topology, candidate, rollback, process, listener, and health identities. No host mutation is authorized.",
        recommendedAction: "Approve bounded read-only collection for exact remediation diagnosis.",
        risks: ["Host remains uncertified pending fresh independent validation."],
      },
    };

    const first = await request(app).post("/api/companies/company-1/approvals").send(body);
    const repeated = await request(app).post("/api/companies/company-1/approvals").send(body);

    expect(first.status, JSON.stringify(first.body)).toBe(200);
    expect(repeated.status, JSON.stringify(repeated.body)).toBe(200);
    expect(first.body).toMatchObject({ created: false, delegated: true, approval: null });
    expect(repeated.body).toMatchObject({ created: false, delegated: true, approval: null });
    expect(mockApprovalService.create).not.toHaveBeenCalled();
    expect(mockApprovalService.createOrReuseBoardApproval).not.toHaveBeenCalled();
    expect(mockIssueApprovalService.linkManyForApproval).not.toHaveBeenCalled();
  });

  it("does not let a Board session create a routine approval record", async () => {
    const res = await request(await createApp())
      .post("/api/companies/company-1/approvals")
      .send({
        type: "request_board_approval",
        issueIds: ["00000000-0000-0000-0000-000000000001"],
        payload: { title: "Collect read-only workspace topology evidence" },
      });

    expect(res.status, JSON.stringify(res.body)).toBe(200);
    expect(res.body).toMatchObject({ created: false, delegated: true, approval: null });
    expect(mockApprovalService.create).not.toHaveBeenCalled();
    expect(mockApprovalService.createOrReuseBoardApproval).not.toHaveBeenCalled();
  });

  it("reuses an equivalent pending deployment approval instead of creating another", async () => {
    const approval = {
      id: "approval-1",
      companyId: "company-1",
      type: "request_board_approval",
      requestedByAgentId: "agent-1",
      requestedByUserId: null,
      status: "pending",
      payload: { title: "Approve production deployment" },
      decisionNote: null,
      decidedByUserId: null,
      decidedAt: null,
      createdAt: new Date("2026-04-06T00:00:00.000Z"),
      updatedAt: new Date("2026-04-06T00:00:00.000Z"),
    };
    mockApprovalService.createOrReuseBoardApproval.mockResolvedValue({ approval, created: false });

    const res = await request(await createAgentApp())
      .post("/api/companies/company-1/approvals")
      .send({
        type: "request_board_approval",
        issueIds: ["00000000-0000-0000-0000-000000000001"],
        payload: { title: "Approve production deployment" },
      });

    expect(res.status, JSON.stringify(res.body)).toBe(200);
    expect(res.body).toMatchObject({ id: "approval-1", created: false, reused: true });
    expect(mockApprovalService.create).not.toHaveBeenCalled();
    expect(mockIssueApprovalService.linkManyForApproval).not.toHaveBeenCalled();
  });

  it("routes an unclassified request to COS instead of creating a Board approval", async () => {
    const res = await request(await createAgentApp())
      .post("/api/companies/company-1/approvals")
      .send({
        type: "request_board_approval",
        payload: { title: "Please decide what to do next" },
      });

    expect(res.status, JSON.stringify(res.body)).toBe(422);
    expect(res.body).toMatchObject({ code: "cos_review_required" });
    expect(mockApprovalService.create).not.toHaveBeenCalled();
    expect(mockApprovalService.createOrReuseBoardApproval).not.toHaveBeenCalled();
  });

  it("routes a hidden governed action to COS instead of delegating it", async () => {
    const res = await request(await createAgentApp())
      .post("/api/companies/company-1/approvals")
      .send({
        type: "request_board_approval",
        payload: {
          title: "Collect read-only evidence",
          summary: "After collection, deploy the Alpha shared service.",
        },
      });

    expect(res.status, JSON.stringify(res.body)).toBe(422);
    expect(res.body).toMatchObject({ code: "cos_review_required" });
    expect(mockApprovalService.create).not.toHaveBeenCalled();
    expect(mockApprovalService.createOrReuseBoardApproval).not.toHaveBeenCalled();
  });

  it("routes a manager's valid human gate through COS instead of creating it directly", async () => {
    const res = await request(await createAgentApp({ contextSnapshot: { agentRole: "manager" } }))
      .post("/api/companies/company-1/approvals")
      .send({
        type: "request_board_approval",
        payload: { title: "Approve production deployment" },
      });

    expect(res.status, JSON.stringify(res.body)).toBe(422);
    expect(res.body).toMatchObject({
      code: "cos_review_required",
      governance: { proposedReasonCode: "DEPLOYMENT" },
    });
    expect(mockApprovalService.create).not.toHaveBeenCalled();
    expect(mockApprovalService.createOrReuseBoardApproval).not.toHaveBeenCalled();
  });

  it.each(["ceo", "chief of staff", "chief-of-staff", "cos"])(
    "lets COS role %s cancel a manager's redundant pending approval",
    async (agentRole) => {
    const pending = {
      id: "approval-9",
      companyId: "company-1",
      type: "request_board_approval",
      status: "pending",
      payload: { title: "Read-only topology" },
      requestedByAgentId: "manager-1",
    };
    mockApprovalService.getById.mockResolvedValue(pending);
    const cancelled = {
      ...pending,
      status: "cancelled",
      cancellationReason: "Routine action delegated to manager/COS.",
      cancelledByAgentId: "agent-1",
      cancelledAt: new Date("2026-04-06T01:00:00.000Z"),
    };
    mockApprovalService.cancel.mockResolvedValue({
      approval: cancelled,
      applied: true,
    });
    mockIssueApprovalService.listIssuesForApproval.mockResolvedValue([{
      id: "issue-1",
      assigneeAgentId: "manager-1",
    }]);

    const res = await request(await createAgentApp({ contextSnapshot: { agentRole } }))
      .post("/api/approvals/approval-9/cancel")
      .send({ decisionNote: "Routine action delegated to manager/COS." });

    expect(res.status, JSON.stringify(res.body)).toBe(200);
    expect(res.body).toMatchObject({
      id: "approval-9",
      status: "cancelled",
      cancellationApplied: true,
    });
    expect(mockApprovalService.cancel).toHaveBeenCalledWith(
      "approval-9",
      "Routine action delegated to manager/COS.",
      { agentId: "agent-1", userId: null },
    );
    expect(mockLogActivity).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({
      actorType: "agent",
      action: "approval.cancelled",
      details: expect.objectContaining({ grantsAuthorization: false }),
    }));
    expect(mockHeartbeatService.wakeup).toHaveBeenCalledWith("manager-1", expect.objectContaining({
      reason: "approval_cancelled",
      idempotencyKey: "approval-review-path:approval-9:issue-1:cancelled",
      payload: expect.objectContaining({ grantsAuthorization: false }),
    }));
  });

  it("treats repeated requester cancellation as an audited-side-effect no-op", async () => {
    const cancelled = {
      id: "approval-9",
      companyId: "company-1",
      type: "request_board_approval",
      status: "cancelled",
      payload: {},
      requestedByAgentId: "agent-1",
      cancellationReason: "Stale request",
    };
    mockApprovalService.getById.mockResolvedValue(cancelled);
    mockApprovalService.cancel.mockResolvedValue({ approval: cancelled, applied: false });
    const res = await request(await createAgentApp({ contextSnapshot: { agentRole: "manager" } }))
      .post("/api/approvals/approval-9/cancel")
      .send({ decisionNote: "Stale request" });
    expect(res.status, JSON.stringify(res.body)).toBe(200);
    expect(res.body.cancellationApplied).toBe(false);
    expect(mockLogActivity).not.toHaveBeenCalled();
    expect(mockHeartbeatService.wakeup).not.toHaveBeenCalled();
  });

  it("prevents a non-requester manager from cancelling another manager's approval", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-10",
      companyId: "company-1",
      type: "request_board_approval",
      status: "pending",
      payload: {},
      requestedByAgentId: "manager-2",
    });

    const res = await request(await createAgentApp({ contextSnapshot: { agentRole: "manager" } }))
      .post("/api/approvals/approval-10/cancel")
      .send({ decisionNote: "Not mine" });

    expect(res.status, JSON.stringify(res.body)).toBe(403);
    expect(mockApprovalService.cancel).not.toHaveBeenCalled();
  });

  it("blocks status-only recovery runs from creating approvals", async () => {
    const res = await request(await createAgentApp({
      contextSnapshot: {
        modelProfile: "cheap",
        recoveryIntent: "status_only",
        allowDeliverableWork: false,
        allowDocumentUpdates: false,
        resumeRequiresNormalModel: true,
      },
    }))
      .post("/api/companies/company-1/approvals")
      .send({
        type: "request_board_approval",
        payload: { title: "Approve hosting spend" },
      });

    expect(res.status, JSON.stringify(res.body)).toBe(403);
    expect(res.body.error).toContain("Cheap status-only recovery runs cannot create or modify approvals");
    expect(mockApprovalService.create).not.toHaveBeenCalled();
    expect(mockIssueApprovalService.linkManyForApproval).not.toHaveBeenCalled();
  });

  it("blocks status-only recovery runs from resubmitting approvals", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-7",
      companyId: "company-1",
      type: "request_board_approval",
      status: "revision_requested",
      payload: {},
      requestedByAgentId: "agent-1",
    });

    const res = await request(await createAgentApp({
      contextSnapshot: {
        modelProfile: "cheap",
        recoveryIntent: "status_only",
        allowDeliverableWork: false,
        allowDocumentUpdates: false,
        resumeRequiresNormalModel: true,
      },
    }))
      .post("/api/approvals/approval-7/resubmit")
      .send({ payload: { title: "Retry" } });

    expect(res.status, JSON.stringify(res.body)).toBe(403);
    expect(res.body.error).toContain("Cheap status-only recovery runs cannot create or modify approvals");
    expect(mockApprovalService.resubmit).not.toHaveBeenCalled();
  });

  it("blocks status-only recovery runs from commenting on approvals", async () => {
    mockApprovalService.getById.mockResolvedValue({
      id: "approval-8",
      companyId: "company-1",
      type: "request_board_approval",
      status: "pending",
      payload: {},
      requestedByAgentId: "agent-1",
    });

    const res = await request(await createAgentApp({
      contextSnapshot: {
        modelProfile: "cheap",
        recoveryIntent: "status_only",
        allowDeliverableWork: false,
        allowDocumentUpdates: false,
        resumeRequiresNormalModel: true,
      },
    }))
      .post("/api/approvals/approval-8/comments")
      .send({ body: "please approve" });

    expect(res.status, JSON.stringify(res.body)).toBe(403);
    expect(res.body.error).toContain("Cheap status-only recovery runs cannot create or modify approvals");
    expect(mockApprovalService.addComment).not.toHaveBeenCalled();
  });
});
