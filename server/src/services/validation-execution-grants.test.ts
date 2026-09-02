import { randomUUID } from "node:crypto";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { and, eq, sql } from "drizzle-orm";
import { agents, companies, createDb, heartbeatRuns, issueComments, issueThreadInteractions, issues, validationExecutionGrants } from "@paperclipai/db";
import { getEmbeddedPostgresTestSupport, startEmbeddedPostgresTestDatabase } from "../__tests__/helpers/embedded-postgres.js";
import { TWDS_VALIDATION_GRANT, bindTwdsValidationGrantSuccessor, consumeTwdsValidationGrant, createTwdsValidationGrant, invalidateTwdsValidationGrants, isValidationExecutionOnlyAction } from "./validation-execution-grants.js";
import { evaluateIssueThreadInteractionResolverAudience } from "./issue-thread-interaction-resolution.js";
import { heartbeatService } from "./heartbeat.js";
import { issueService } from "./issues.js";
import { registerServerAdapter, unregisterServerAdapter, type ServerAdapterModule } from "../adapters/index.js";

const support = await getEmbeddedPostgresTestSupport();
const describePostgres = support.supported ? describe : describe.skip;

describe("TWDS validation execution grant boundary", () => {
  it("has one immutable validation tuple", () => {
    expect(TWDS_VALIDATION_GRANT).toEqual({
      approvalIssueId: "c2840abd-d4b5-46f1-bd73-ac8fbfd5078b",
      approvalCommentId: "99cf7940-1a77-4dd6-8e4a-bc6d9f24b24b",
      issueId: "ea9c1146-8ffa-4718-94d7-49c483d02969",
      candidateSha: "2298ccb3c33337e718ab37fb75d8d805fb020c14",
      contractSha: "96a6b59ca7a693756f419ce5adc1acde3a96ff8b",
      oracleSha: "73baefded458372ef679ca19a85803d50047ea9",
    });
  });

  it.each(["repository_mutation", "merge", "promotion", "deployment", "force_push", "protected_alpha_change", "scope_waiver", "tolerance_change", "observed_output_golden_creation"])("does not authorize %s", (action) => {
    expect(isValidationExecutionOnlyAction(action)).toBe(false);
  });

  it("authorizes only validation execution", () => {
    expect(isValidationExecutionOnlyAction("validation_execution")).toBe(true);
  });
});

describePostgres("TWDS validation execution grant lifecycle (Postgres)", () => {
  let db: ReturnType<typeof createDb>;
  let temp: Awaited<ReturnType<typeof startEmbeddedPostgresTestDatabase>>;
  let companyId: string;
  let sourceRunId: string;
  let successorRunId: string;

  beforeAll(async () => {
    temp = await startEmbeddedPostgresTestDatabase("paperclip-validation-grant-");
    db = createDb(temp.connectionString);
  }, 30_000);
  afterEach(async () => {
    await db.delete(validationExecutionGrants);
    await db.delete(issueThreadInteractions);
    await db.delete(issueComments);
    await db.delete(heartbeatRuns);
    await db.delete(issues);
    await db.delete(agents);
    await db.delete(companies);
  });
  afterAll(async () => { await db.$client.end(); await temp.cleanup(); });

  async function seedGrant(options: { createGrant?: boolean } = {}) {
    companyId = randomUUID(); const agentId = randomUUID(); sourceRunId = randomUUID(); successorRunId = randomUUID();
    const approvalInteractionId = randomUUID();
    await db.insert(companies).values({ id: companyId, name: "Validation Grant Test", issuePrefix: "VGT", requireBoardApprovalForNewAgents: false });
    await db.insert(agents).values({ id: agentId, companyId, name: "Runner", role: "engineer", status: "idle", adapterType: "codex_local", adapterConfig: {}, runtimeConfig: {}, permissions: {} });
    await db.insert(heartbeatRuns).values([{ id: sourceRunId, companyId, agentId }, { id: successorRunId, companyId, agentId }]);
    await db.insert(issues).values([{ id: TWDS_VALIDATION_GRANT.approvalIssueId, companyId, title: "Approval", status: "open" }, { id: TWDS_VALIDATION_GRANT.issueId, companyId, title: "Target", status: "open" }]);
    await db.insert(issueComments).values({ id: TWDS_VALIDATION_GRANT.approvalCommentId, companyId, issueId: TWDS_VALIDATION_GRANT.approvalIssueId, body: "Board approval" });
    await db.insert(issueThreadInteractions).values({ id: approvalInteractionId, companyId, issueId: TWDS_VALIDATION_GRANT.approvalIssueId, kind: "request_confirmation", status: "accepted", effectiveResolverPolicy: "human_only", requestedResolverPolicy: "human_only", resolverPolicyProvenance: "explicit", effectiveResolverPolicySource: "requested", continuationPolicy: "wake_assignee", sourceCommentId: TWDS_VALIDATION_GRANT.approvalCommentId, sourceRunId, payload: {} });
    if (options.createGrant !== false) {
      await db.insert(validationExecutionGrants).values({ companyId, approvalIssueId: TWDS_VALIDATION_GRANT.approvalIssueId, approvalInteractionId, approvalCommentId: TWDS_VALIDATION_GRANT.approvalCommentId, approvalSourceRunId: sourceRunId, issueId: TWDS_VALIDATION_GRANT.issueId, candidateSha: TWDS_VALIDATION_GRANT.candidateSha, contractSha: TWDS_VALIDATION_GRANT.contractSha, oracleSha: TWDS_VALIDATION_GRANT.oracleSha, expiresAt: new Date(Date.now() + 60_000) });
    }
    return approvalInteractionId;
  }

  it("consumes once, rejects concurrent replay, and records the consumer", async () => {
    await seedGrant();
    const results = await Promise.all([consumeTwdsValidationGrant(db, { companyId, runId: sourceRunId, action: "validation_execution", tuple: TWDS_VALIDATION_GRANT }), consumeTwdsValidationGrant(db, { companyId, runId: sourceRunId, action: "validation_execution", tuple: TWDS_VALIDATION_GRANT })]);
    expect(results.filter((r) => r.ok)).toHaveLength(1);
    expect(results.filter((r) => !r.ok)[0]).toMatchObject({ code: "grant_unavailable" });
    const [grant] = await db.select().from(validationExecutionGrants);
    expect(grant).toMatchObject({ status: "consumed", consumerRunId: sourceRunId });
  });

  it.each(["issueId", "candidateSha", "contractSha", "oracleSha"] as const)("invalidates on %s mismatch", async (field) => {
    await seedGrant();
    const mismatch = await consumeTwdsValidationGrant(db, { companyId, runId: sourceRunId, action: "validation_execution", tuple: { ...TWDS_VALIDATION_GRANT, [field]: "wrong" } });
    expect(mismatch).toMatchObject({ ok: false, code: "tuple_mismatch" });
    const [grant] = await db.select().from(validationExecutionGrants);
    expect(grant).toMatchObject({ status: "invalidated", invalidationReason: "tuple_mismatch" });
  });

  it("rejects unrelated runs and expires unused grants", async () => {
    await seedGrant();
    expect(await consumeTwdsValidationGrant(db, { companyId, runId: randomUUID(), action: "validation_execution", tuple: TWDS_VALIDATION_GRANT })).toMatchObject({ ok: false, code: "grant_not_found" });
    expect(await consumeTwdsValidationGrant(db, { companyId, runId: sourceRunId, action: "validation_execution", tuple: TWDS_VALIDATION_GRANT, now: new Date(Date.now() + 120_000) })).toMatchObject({ ok: false, code: "grant_expired" });
    const [grant] = await db.select().from(validationExecutionGrants);
    expect(grant).toMatchObject({ status: "invalidated", invalidationReason: "expired" });
  });

  it("binds only one immediate successor and invalidates outstanding grants on completion", async () => {
    const interactionId = await seedGrant();
    expect(await bindTwdsValidationGrantSuccessor(db, { companyId, interactionId, sourceRunId, successorRunId })).toMatchObject({ successorRunId });
    expect(await bindTwdsValidationGrantSuccessor(db, { companyId, interactionId, sourceRunId, successorRunId: randomUUID() })).toBeNull();
    expect(await invalidateTwdsValidationGrants(db, { companyId, issueId: TWDS_VALIDATION_GRANT.issueId, reason: "validation_completed" })).toHaveLength(1);
    const [grant] = await db.select().from(validationExecutionGrants).where(and(eq(validationExecutionGrants.companyId, companyId), eq(validationExecutionGrants.issueId, TWDS_VALIDATION_GRANT.issueId)));
    expect(grant).toMatchObject({ status: "invalidated", invalidationReason: "validation_completed", successorRunId });
  });

  it("allows the single immediate successor to consume and preserves immutable audit linkage", async () => {
    const interactionId = await seedGrant({ createGrant: false });
    const now = new Date();
    await expect(createTwdsValidationGrant(db, {
      companyId,
      approvalIssueId: TWDS_VALIDATION_GRANT.approvalIssueId,
      interaction: {
        id: interactionId,
        kind: "request_confirmation",
        sourceCommentId: TWDS_VALIDATION_GRANT.approvalCommentId,
        sourceRunId,
        effectiveResolverPolicy: "human_only",
      },
      userId: randomUUID(),
      now,
    })).resolves.toMatchObject({
      approvalInteractionId: interactionId,
      approvalSourceRunId: sourceRunId,
      approvalCommentId: TWDS_VALIDATION_GRANT.approvalCommentId,
      createdAt: now,
    });
    expect(await bindTwdsValidationGrantSuccessor(db, { companyId, interactionId, sourceRunId, successorRunId })).toMatchObject({ successorRunId });

    await expect(consumeTwdsValidationGrant(db, { companyId, runId: successorRunId, action: "validation_execution", tuple: TWDS_VALIDATION_GRANT })).resolves.toMatchObject({ ok: true });

    const [grant] = await db.select().from(validationExecutionGrants);
    expect(grant).toMatchObject({
      approvalIssueId: TWDS_VALIDATION_GRANT.approvalIssueId,
      approvalInteractionId: interactionId,
      approvalCommentId: TWDS_VALIDATION_GRANT.approvalCommentId,
      approvalSourceRunId: sourceRunId,
      successorRunId,
      consumerRunId: successorRunId,
      status: "consumed",
    });
  });

  it("invalidates a consumed grant on validation completion without erasing its audit linkage", async () => {
    const interactionId = await seedGrant();
    await expect(consumeTwdsValidationGrant(db, { companyId, runId: sourceRunId, action: "validation_execution", tuple: TWDS_VALIDATION_GRANT })).resolves.toMatchObject({ ok: true });

    await expect(invalidateTwdsValidationGrants(db, { companyId, issueId: TWDS_VALIDATION_GRANT.issueId, reason: "validation_completed" })).resolves.toHaveLength(1);

    const [grant] = await db.select().from(validationExecutionGrants);
    expect(grant).toMatchObject({
      status: "invalidated",
      invalidationReason: "validation_completed",
      approvalInteractionId: interactionId,
      approvalSourceRunId: sourceRunId,
      consumerRunId: sourceRunId,
    });
  });

  it("invalidates a consumed grant when its target issue becomes terminal", async () => {
    await seedGrant();
    await expect(consumeTwdsValidationGrant(db, { companyId, runId: sourceRunId, action: "validation_execution", tuple: TWDS_VALIDATION_GRANT })).resolves.toMatchObject({ ok: true });

    await expect(invalidateTwdsValidationGrants(db, { companyId, issueId: TWDS_VALIDATION_GRANT.issueId, reason: "terminal_issue" })).resolves.toHaveLength(1);

    const [grant] = await db.select().from(validationExecutionGrants);
    expect(grant).toMatchObject({ status: "invalidated", invalidationReason: "terminal_issue", consumerRunId: sourceRunId });
  });

  it("invalidates through the terminal issue-service transition", async () => {
    await seedGrant();

    await expect(issueService(db).update(TWDS_VALIDATION_GRANT.issueId, { status: "done" })).resolves.toMatchObject({
      id: TWDS_VALIDATION_GRANT.issueId,
      status: "done",
    });

    const [grant] = await db.select().from(validationExecutionGrants);
    expect(grant).toMatchObject({ status: "invalidated", invalidationReason: "terminal_issue" });
  });

  it("denies mutation capabilities without consuming the grant", async () => {
    await seedGrant();
    for (const action of ["merge", "deployment", "repository_mutation", "tolerance_change"]) {
      await expect(consumeTwdsValidationGrant(db, { companyId, runId: sourceRunId, action, tuple: TWDS_VALIDATION_GRANT })).resolves.toMatchObject({ ok: false, code: "capability_denied" });
    }
    const [grant] = await db.select().from(validationExecutionGrants);
    expect(grant).toMatchObject({ status: "issued", consumerRunId: null });
  });

  it("does not issue a grant when the confirmation is not human_only or has no authenticated user", async () => {
    const interactionId = await seedGrant({ createGrant: false });
    const base = {
      companyId,
      approvalIssueId: TWDS_VALIDATION_GRANT.approvalIssueId,
      interaction: {
        id: interactionId,
        kind: "request_confirmation",
        sourceCommentId: TWDS_VALIDATION_GRANT.approvalCommentId,
        sourceRunId,
        effectiveResolverPolicy: "human_only",
      },
      now: new Date(),
    } as const;
    await expect(createTwdsValidationGrant(db, { ...base, userId: null })).resolves.toBeNull();
    await expect(createTwdsValidationGrant(db, {
      ...base,
      userId: randomUUID(),
      interaction: { ...base.interaction, effectiveResolverPolicy: "anyone" },
    })).resolves.toBeNull();
    expect(await db.select().from(validationExecutionGrants)).toHaveLength(0);
  });
});

describe("unrelated human_only resolver enforcement", () => {
  it("continues to deny an agent for a separate human_only confirmation", () => {
    expect(evaluateIssueThreadInteractionResolverAudience({
      actor: { type: "agent", agentId: randomUUID(), companyId: randomUUID(), runId: randomUUID() },
      interaction: {
        id: randomUUID(),
        companyId: randomUUID(),
        issueId: randomUUID(),
        kind: "request_confirmation",
        effectiveResolverPolicy: "human_only",
        createdByAgentId: null,
        createdByUserId: randomUUID(),
        sourceRunId: null,
      },
      additionalRestriction: "anyone",
    })).toMatchObject({ allowed: false, code: "interaction_human_only" });
  });
});

describePostgres("TWDS validation grant heartbeat boundary (Postgres)", () => {
  const adapterType = "twds_validation_grant_test";
  const execute = vi.fn<ServerAdapterModule["execute"]>();
  let db: ReturnType<typeof createDb>;
  let temp: Awaited<ReturnType<typeof startEmbeddedPostgresTestDatabase>>;

  beforeAll(async () => {
    temp = await startEmbeddedPostgresTestDatabase("paperclip-validation-grant-heartbeat-");
    db = createDb(temp.connectionString);
    registerServerAdapter({
      type: adapterType,
      execute,
      testEnvironment: async () => ({ adapterType, status: "pass", checks: [], testedAt: new Date().toISOString() }),
    });
  }, 30_000);
  afterEach(async () => {
    await db.execute(sql.raw('TRUNCATE TABLE "companies" RESTART IDENTITY CASCADE'));
    vi.clearAllMocks();
  });
  afterAll(async () => { unregisterServerAdapter(adapterType); await db.$client.end(); await temp.cleanup(); });

  async function seedQueuedValidationRun({ grant }: { grant: boolean }) {
    const companyId = randomUUID();
    const agentId = randomUUID();
    const runId = randomUUID();
    const interactionId = randomUUID();
    await db.insert(companies).values({ id: companyId, name: "Heartbeat boundary", issuePrefix: "VGH", requireBoardApprovalForNewAgents: false, defaultResponsibleUserId: "reviewer" });
    await db.insert(agents).values({ id: agentId, companyId, name: "Validation runner", role: "engineer", status: "idle", adapterType, adapterConfig: {}, runtimeConfig: {}, permissions: {} });
    await db.insert(issues).values([
      { id: TWDS_VALIDATION_GRANT.approvalIssueId, companyId, title: "Approval", status: "open" },
      { id: TWDS_VALIDATION_GRANT.issueId, companyId, title: "Validation", status: "in_progress", assigneeAgentId: agentId },
    ]);
    await db.insert(issueComments).values({ id: TWDS_VALIDATION_GRANT.approvalCommentId, companyId, issueId: TWDS_VALIDATION_GRANT.approvalIssueId, body: "Approved" });
    await db.insert(heartbeatRuns).values({ id: runId, companyId, agentId, status: "queued", responsibleUserId: "reviewer", contextSnapshot: { issueId: TWDS_VALIDATION_GRANT.issueId } });
    if (grant) {
      await db.insert(issueThreadInteractions).values({ id: interactionId, companyId, issueId: TWDS_VALIDATION_GRANT.approvalIssueId, kind: "request_confirmation", status: "accepted", effectiveResolverPolicy: "human_only", requestedResolverPolicy: "human_only", resolverPolicyProvenance: "explicit", effectiveResolverPolicySource: "requested", continuationPolicy: "wake_assignee", sourceCommentId: TWDS_VALIDATION_GRANT.approvalCommentId, sourceRunId: runId, payload: {} });
      await db.insert(validationExecutionGrants).values({ companyId, approvalIssueId: TWDS_VALIDATION_GRANT.approvalIssueId, approvalInteractionId: interactionId, approvalCommentId: TWDS_VALIDATION_GRANT.approvalCommentId, approvalSourceRunId: runId, issueId: TWDS_VALIDATION_GRANT.issueId, candidateSha: TWDS_VALIDATION_GRANT.candidateSha, contractSha: TWDS_VALIDATION_GRANT.contractSha, oracleSha: TWDS_VALIDATION_GRANT.oracleSha, expiresAt: new Date(Date.now() + 60_000) });
    }
    return { companyId, runId };
  }

  it("blocks adapter dispatch without a grant at the concrete pre-adapter boundary", async () => {
    const { runId } = await seedQueuedValidationRun({ grant: false });
    const heartbeat = heartbeatService(db);
    await heartbeat.resumeQueuedRuns();
    await heartbeat.drainActiveRunExecutions();
    expect(execute).not.toHaveBeenCalled();
    expect(await heartbeat.getRun(runId)).toMatchObject({ status: "failed" });
  });

  it("consumes before dispatch and invalidates immutable audit linkage after completion", async () => {
    execute.mockResolvedValue({ exitCode: 0, signal: null, timedOut: false, resultJson: {} });
    const { companyId, runId } = await seedQueuedValidationRun({ grant: true });
    const heartbeat = heartbeatService(db);
    await heartbeat.resumeQueuedRuns();
    await heartbeat.drainActiveRunExecutions();
    expect(execute).toHaveBeenCalledOnce();
    expect(await heartbeat.getRun(runId)).toMatchObject({ status: "succeeded" });
    const [grant] = await db.select().from(validationExecutionGrants).where(eq(validationExecutionGrants.companyId, companyId));
    expect(grant).toMatchObject({ status: "invalidated", invalidationReason: "validation_completed", approvalSourceRunId: runId, consumerRunId: runId });
  });
});
