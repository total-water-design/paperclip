import { randomUUID } from "node:crypto";
import { and, eq } from "drizzle-orm";
import { issueComments, issueExecutionDecisions, issues, type Db } from "@paperclipai/db";
import { conflict, notFound, unprocessable } from "../errors.js";
import { logActivity } from "./activity-log.js";
import { issueService } from "./issues.js";
import { normalizeIssueExecutionPolicy, parseIssueExecutionState } from "./issue-execution-policy.js";

export type LostReviewDecisionReconciliationInput = {
  issueId: string;
  companyId: string;
  candidate: string;
  stageId: string;
  approvingUserId: string;
  evidenceCommentId: string;
  actorUserId: string;
  runId?: string | null;
};

const APPROVAL_WORD = /\b(?:approve|approved|approval)\b/i;

export function lostReviewDecisionReconciliationService(db: Db) {
  return {
    reconcileApproved: async (input: LostReviewDecisionReconciliationInput) => db.transaction(async (tx) => {
      const txDb = tx as unknown as Db;
      if (input.actorUserId !== input.approvingUserId) {
        throw conflict("Approving identity does not match authenticated Board actor");
      }
      const locked = await tx.select().from(issues).where(and(
        eq(issues.id, input.issueId), eq(issues.companyId, input.companyId),
      )).for("update").then((rows) => rows[0] ?? null);
      if (!locked) throw notFound("Issue not found");

      const policy = normalizeIssueExecutionPolicy(locked.executionPolicy);
      const stage = policy?.stages.find((item) => item.id === input.stageId);
      if (!stage || stage.type !== "review") throw conflict("Review stage does not match", { stageId: input.stageId });
      if (!stage.participants.some((p) => p.type === "user" && p.userId === input.approvingUserId)) {
        throw conflict("Approving identity is not a participant in the review stage");
      }

      const evidence = await tx.select().from(issueComments).where(and(
        eq(issueComments.id, input.evidenceCommentId),
        eq(issueComments.issueId, locked.id),
        eq(issueComments.companyId, locked.companyId),
      )).then((rows) => rows[0] ?? null);
      if (!evidence || evidence.deletedAt || evidence.authorType !== "user" ||
          evidence.authorUserId !== input.approvingUserId ||
          !evidence.body.includes(input.candidate) || !APPROVAL_WORD.test(evidence.body)) {
        throw unprocessable("Preserved Board approval evidence does not match");
      }

      const existing = await tx.select().from(issueExecutionDecisions).where(and(
        eq(issueExecutionDecisions.issueId, locked.id),
        eq(issueExecutionDecisions.stageId, input.stageId),
      )).then((rows) => rows[0] ?? null);
      if (existing) {
        if (existing.outcome !== "approved" || existing.actorUserId !== input.approvingUserId) {
          throw conflict("Existing typed decision conflicts with reconciliation request");
        }
        return { issue: locked, decision: existing, reconciled: false as const };
      }

      const state = parseIssueExecutionState(locked.executionState);
      if (state?.lastDecisionId || state?.lastDecisionOutcome) {
        throw conflict("Issue already has an authoritative decision state");
      }
      const decisionId = randomUUID();
      const completedStageIds = [...new Set([...(state?.completedStageIds ?? []), input.stageId])];
      const executionState = {
        status: "completed" as const, currentStageId: null, currentStageIndex: null,
        currentStageType: null, currentParticipant: null,
        returnAssignee: state?.returnAssignee ?? null, reviewRequest: state?.reviewRequest ?? null,
        completedStageIds, lastDecisionId: decisionId, lastDecisionOutcome: "approved" as const,
        monitor: state?.monitor ?? null, changesRequestedCount: state?.changesRequestedCount ?? 0,
      };
      const svc = issueService(txDb);
      const updated = await svc.update(locked.id, {
        status: "done", executionState, actorUserId: input.actorUserId,
      }, tx);
      if (!updated) throw notFound("Issue not found");
      const body = `Recovered preserved Board approval from comment ${evidence.id} for candidate ${input.candidate}`;
      const [decision] = await tx.insert(issueExecutionDecisions).values({
        id: decisionId, companyId: locked.companyId, issueId: locked.id,
        stageId: input.stageId, stageType: "review", actorAgentId: null,
        actorUserId: input.approvingUserId, outcome: "approved", body,
        createdByRunId: input.runId ?? null,
      }).returning();
      await logActivity(txDb, {
        companyId: locked.companyId, actorType: "user", actorId: input.actorUserId,
        runId: input.runId ?? null, action: "issue.lost_review_decision_reconciled",
        entityType: "issue", entityId: locked.id, issueId: locked.id,
        details: { candidate: input.candidate, stageId: input.stageId, decisionId,
          approvingUserId: input.approvingUserId, evidenceCommentId: evidence.id,
          _previous: { status: locked.status, executionState: locked.executionState } },
      });
      return { issue: updated, decision: decision!, reconciled: true as const };
    }),
  };
}
