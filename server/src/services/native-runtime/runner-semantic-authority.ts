import { and, desc, eq, isNull } from "drizzle-orm";

import type { Db } from "@paperclipai/db";
import {
  agents,
  documentRevisions,
  documents,
  heartbeatRuns,
  issueComments,
  issueDocuments,
  issues,
  semanticActionReceipts,
} from "@paperclipai/db";
import {
  PaperclipSemanticDispatcher,
  type PaperclipJsonValue,
  type PaperclipSemanticActionBinding,
  type PaperclipSemanticActionId,
  type PaperclipSemanticAuthorizationRecord,
  type PaperclipSemanticIdempotencyStore,
  type PaperclipSemanticRunContext,
  type PaperclipSemanticStoredOutcome,
  type PaperclipSemanticToolCall,
  type PaperclipSemanticToolDefinition,
  type PaperclipSemanticToolResult,
} from "../../vendor/paperclip-runner/index.js";
import { approvalService } from "../approvals.js";
import { logActivity } from "../activity-log.js";
import { secretService } from "../secrets.js";

export interface PaperclipRunnerSemanticBinding {
  readonly companyId: string;
  readonly issueId: string;
  readonly runId: string;
  readonly agentId: string;
}

const READ_OPERATION_IDS = [
  "get_task_context",
  "get_task_history",
  "list_documents",
  "read_document",
  "list_document_revisions",
] as const satisfies readonly PaperclipSemanticActionId[];

const RESUBMIT_APPROVAL_CLAIM = "governance:approvals:resubmit";

type BoundContext = {
  readonly run: typeof heartbeatRuns.$inferSelect;
  readonly issue: typeof issues.$inferSelect;
  readonly agent: typeof agents.$inferSelect;
};

function boundedLimit(value: unknown): number {
  return typeof value === "number" && Number.isInteger(value)
    ? Math.max(1, Math.min(value, 200))
    : 50;
}

function requiredString(value: unknown): string {
  if (typeof value !== "string" || value.length === 0 || value.length > 240) {
    throw new Error("paperclip_runner_semantic_input_invalid");
  }
  return value;
}

function jsonValue(value: unknown): PaperclipJsonValue {
  return JSON.parse(JSON.stringify(value)) as PaperclipJsonValue;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStatusOnlyCheapRecoveryContext(contextSnapshot: unknown): boolean {
  if (!isPlainObject(contextSnapshot)) return false;
  return contextSnapshot.modelProfile === "cheap" &&
    contextSnapshot.recoveryIntent === "status_only" &&
    contextSnapshot.allowDeliverableWork === false &&
    contextSnapshot.allowDocumentUpdates === false &&
    contextSnapshot.resumeRequiresNormalModel === true;
}

function activeAgentStatus(status: string): "active" | "inactive" {
  return ["paused", "terminated", "pending_approval", "error"].includes(status)
    ? "inactive"
    : "active";
}

/**
 * Run-scoped semantic authority for the hidden native coordinator.
 * This first server slice binds only same-task read operations. A catalog
 * entry remains undiscoverable until a later PR adds its guarded binding.
 */
export class PaperclipRunnerSemanticAuthority {
  readonly #db: Db;
  readonly #binding: PaperclipRunnerSemanticBinding;
  readonly #dispatcher: PaperclipSemanticDispatcher;

  constructor(db: Db, binding: PaperclipRunnerSemanticBinding) {
    this.#db = db;
    this.#binding = structuredClone(binding);
    this.#dispatcher = new PaperclipSemanticDispatcher({
      contextProvider: (runId) => this.#context(runId),
      bindings: [
        ...READ_OPERATION_IDS.map((operationId) => this.#readBinding(operationId)),
        this.#resubmitApprovalBinding(),
      ],
      idempotencyStore: this.#semanticIdempotencyStore(),
    });
  }

  listAlwaysAvailableTools(): Promise<
    readonly PaperclipSemanticToolDefinition[]
  > {
    return this.#dispatcher.listAlwaysAvailableTools(this.#binding.runId);
  }

  dispatch(
    call: Omit<PaperclipSemanticToolCall, "runId">,
  ): Promise<PaperclipSemanticToolResult> {
    return this.#dispatcher.dispatch({ ...call, runId: this.#binding.runId });
  }

  authorizationRecords(): readonly PaperclipSemanticAuthorizationRecord[] {
    return this.#dispatcher.authorizationRecords();
  }

  #readBinding(
    operationId: (typeof READ_OPERATION_IDS)[number],
  ): PaperclipSemanticActionBinding {
    return {
      operationId,
      execute: async (invocation) => {
        const context = await this.#loadBoundContext();
        this.#assertActiveContext(context, true);
        const input = invocation.input;
        switch (operationId) {
          case "get_task_context":
            return {
              value: jsonValue({
                company: { id: this.#binding.companyId },
                actor: {
                  id: context.agent.id,
                  name: context.agent.name,
                  role: context.agent.role,
                  title: context.agent.title,
                  capabilities: context.agent.capabilities,
                },
                activeTask: {
                  id: context.issue.id,
                  identifier: context.issue.identifier,
                  title: context.issue.title,
                  description: context.issue.description,
                  status: context.issue.status,
                  statusVersion: context.issue.statusVersion,
                  priority: context.issue.priority,
                  workMode: context.issue.workMode,
                  parentId: context.issue.parentId,
                  projectId: context.issue.projectId,
                  goalId: context.issue.goalId,
                },
                run: {
                  id: context.run.id,
                  status: context.run.status,
                  invocationSource: context.run.invocationSource,
                },
              }),
              references: [{ kind: "task", id: context.issue.id }],
            };
          case "get_task_history": {
            const rows = await this.#db
              .select({
                id: issueComments.id,
                body: issueComments.body,
                authorAgentId: issueComments.authorAgentId,
                authorUserId: issueComments.authorUserId,
                createdAt: issueComments.createdAt,
              })
              .from(issueComments)
              .where(
                and(
                  eq(issueComments.companyId, this.#binding.companyId),
                  eq(issueComments.issueId, this.#binding.issueId),
                  isNull(issueComments.deletedAt),
                ),
              )
              .orderBy(desc(issueComments.createdAt))
              .limit(boundedLimit(input.limit));
            return {
              value: jsonValue({ comments: rows.reverse() }),
              references: [{ kind: "task", id: context.issue.id }],
            };
          }
          case "list_documents": {
            const rows = await this.#db
              .select({
                key: issueDocuments.key,
                id: documents.id,
                title: documents.title,
                format: documents.format,
                latestRevisionId: documents.latestRevisionId,
                latestRevisionNumber: documents.latestRevisionNumber,
                lockedAt: documents.lockedAt,
                updatedAt: documents.updatedAt,
              })
              .from(issueDocuments)
              .innerJoin(documents, eq(documents.id, issueDocuments.documentId))
              .where(
                and(
                  eq(issueDocuments.companyId, this.#binding.companyId),
                  eq(issueDocuments.issueId, this.#binding.issueId),
                  eq(documents.companyId, this.#binding.companyId),
                ),
              );
            return {
              value: jsonValue({ documents: rows }),
              references: rows.map((row) => ({
                kind: "document_revision" as const,
                id: row.latestRevisionId ?? row.id,
              })),
            };
          }
          case "read_document": {
            const key = requiredString(input.key);
            const [row] = await this.#db
              .select({
                key: issueDocuments.key,
                id: documents.id,
                title: documents.title,
                format: documents.format,
                body: documents.latestBody,
                latestRevisionId: documents.latestRevisionId,
                latestRevisionNumber: documents.latestRevisionNumber,
                lockedAt: documents.lockedAt,
                updatedAt: documents.updatedAt,
              })
              .from(issueDocuments)
              .innerJoin(documents, eq(documents.id, issueDocuments.documentId))
              .where(
                and(
                  eq(issueDocuments.companyId, this.#binding.companyId),
                  eq(issueDocuments.issueId, this.#binding.issueId),
                  eq(issueDocuments.key, key),
                  eq(documents.companyId, this.#binding.companyId),
                ),
              )
              .limit(1);
            if (!row) throw new Error("paperclip_runner_document_not_found");
            return {
              value: jsonValue({ document: row }),
              references: [
                {
                  kind: "document_revision",
                  id: row.latestRevisionId ?? row.id,
                },
              ],
            };
          }
          case "list_document_revisions": {
            const key = requiredString(input.key);
            const rows = await this.#db
              .select({
                id: documentRevisions.id,
                revisionNumber: documentRevisions.revisionNumber,
                title: documentRevisions.title,
                format: documentRevisions.format,
                body: documentRevisions.body,
                changeSummary: documentRevisions.changeSummary,
                createdByAgentId: documentRevisions.createdByAgentId,
                createdByUserId: documentRevisions.createdByUserId,
                createdAt: documentRevisions.createdAt,
              })
              .from(issueDocuments)
              .innerJoin(
                documentRevisions,
                eq(documentRevisions.documentId, issueDocuments.documentId),
              )
              .where(
                and(
                  eq(issueDocuments.companyId, this.#binding.companyId),
                  eq(issueDocuments.issueId, this.#binding.issueId),
                  eq(issueDocuments.key, key),
                  eq(documentRevisions.companyId, this.#binding.companyId),
                ),
              )
              .orderBy(desc(documentRevisions.revisionNumber))
              .limit(boundedLimit(input.limit));
            return {
              value: jsonValue({ revisions: rows }),
              references: rows.map((row) => ({
                kind: "document_revision" as const,
                id: row.id,
              })),
            };
          }
        }
      },
    };
  }

  #resubmitApprovalBinding(): PaperclipSemanticActionBinding {
    return {
      operationId: "resubmit_approval",
      execute: async (invocation) => {
        const context = await this.#loadBoundContext();
        this.#assertActiveContext(context, true);
        if (isStatusOnlyCheapRecoveryContext(context.run.contextSnapshot)) {
          throw new Error("status_only_recovery_cannot_resubmit_approval");
        }

        const approvalId = requiredString(invocation.input.approvalId);
        const approvalSvc = approvalService(this.#db);
        const existing = await approvalSvc.getById(approvalId);
        if (!existing || existing.companyId !== this.#binding.companyId) {
          throw new Error("approval_not_found_in_run_company");
        }
        if (existing.requestedByAgentId !== this.#binding.agentId) {
          throw new Error(
            "Only the requester may resubmit; approvers may approve or reject.",
          );
        }

        const payload = invocation.input.payload;
        if (payload !== undefined && !isPlainObject(payload)) {
          throw new Error("paperclip_runner_semantic_input_invalid");
        }
        const normalizedPayload = payload === undefined
          ? undefined
          : existing.type === "hire_agent"
            ? await secretService(this.#db).normalizeHireApprovalPayloadForPersistence(
              existing.companyId,
              payload,
              { strictMode: process.env.PAPERCLIP_SECRETS_STRICT_MODE === "true" },
            )
            : payload;
        const approval = await approvalSvc.resubmit(approvalId, normalizedPayload);
        await logActivity(this.#db, {
          companyId: approval.companyId,
          actorType: "agent",
          actorId: this.#binding.agentId,
          agentId: this.#binding.agentId,
          action: "approval.resubmitted",
          entityType: "approval",
          entityId: approval.id,
          details: { type: approval.type, source: "runner_semantic" },
        });
        return {
          value: jsonValue({
            commandId: invocation.callId,
            disposition: "applied",
            stateRevision: 0,
            entityRefs: [approval.id, invocation.taskId],
            scheduledWakeIds: [],
          }),
          references: [
            { kind: "approval", id: approval.id },
            { kind: "task", id: invocation.taskId },
          ],
        };
      },
    };
  }

  #semanticIdempotencyStore(): PaperclipSemanticIdempotencyStore {
    const companyId = this.#binding.companyId;
    return {
      claim: async ({ scope, operationId, inputDigest }) => {
        const [inserted] = await this.#db
          .insert(semanticActionReceipts)
          .values({ companyId, scope, operationId, inputDigest, outcome: null })
          .onConflictDoNothing({
            target: [semanticActionReceipts.companyId, semanticActionReceipts.scope],
          })
          .returning();
        if (inserted) return { kind: "claimed", token: scope } as const;

        const existing = await this.#db
          .select()
          .from(semanticActionReceipts)
          .where(
            and(
              eq(semanticActionReceipts.companyId, companyId),
              eq(semanticActionReceipts.scope, scope),
            ),
          )
          .then((rows) => rows[0] ?? null);
        if (!existing || existing.operationId !== operationId || existing.inputDigest !== inputDigest) {
          return { kind: "conflict" } as const;
        }
        if (existing.outcome === null) return { kind: "in_progress" } as const;
        return {
          kind: "duplicate",
          outcome: existing.outcome as unknown as PaperclipSemanticStoredOutcome,
        } as const;
      },
      complete: async (token, outcome) => {
        await this.#persistSemanticOutcome(token, outcome);
      },
      recover: async (token, outcome) => {
        await this.#persistSemanticOutcome(token, outcome);
      },
      release: async (token) => {
        await this.#db
          .delete(semanticActionReceipts)
          .where(
            and(
              eq(semanticActionReceipts.companyId, companyId),
              eq(semanticActionReceipts.scope, token),
              isNull(semanticActionReceipts.outcome),
            ),
          );
      },
    };
  }

  async #persistSemanticOutcome(
    token: string,
    outcome: PaperclipSemanticStoredOutcome,
  ): Promise<void> {
    await this.#db
      .update(semanticActionReceipts)
      .set({ outcome: jsonValue(outcome) as Record<string, unknown>, updatedAt: new Date() })
      .where(
        and(
          eq(semanticActionReceipts.companyId, this.#binding.companyId),
          eq(semanticActionReceipts.scope, token),
        ),
      );
  }

  async #context(requestedRunId: string): Promise<PaperclipSemanticRunContext> {
    if (requestedRunId !== this.#binding.runId) {
      throw new Error("paperclip_runner_semantic_run_mismatch");
    }
    const context = await this.#loadBoundContext();
    this.#assertActiveContext(context, false);
    return {
      runId: context.run.id,
      companyId: context.run.companyId,
      actor: {
        id: context.agent.id,
        companyId: context.agent.companyId,
        status: activeAgentStatus(context.agent.status),
        role: context.agent.role,
        claims: [RESUBMIT_APPROVAL_CLAIM],
      },
      activeTask: {
        id: context.issue.id,
        companyId: context.issue.companyId,
        assigneeActorId: context.issue.assigneeAgentId,
        executionRunId: context.issue.executionRunId,
        status: context.issue.status,
        workMode: context.issue
          .workMode as PaperclipSemanticRunContext["activeTask"]["workMode"],
      },
      delegatedClaims: [RESUBMIT_APPROVAL_CLAIM],
    };
  }

  async #loadBoundContext(): Promise<BoundContext> {
    const [row] = await this.#db
      .select({ run: heartbeatRuns, issue: issues, agent: agents })
      .from(heartbeatRuns)
      .innerJoin(
        issues,
        and(
          eq(issues.id, heartbeatRuns.nativeIssueId),
          eq(issues.companyId, heartbeatRuns.companyId),
        ),
      )
      .innerJoin(
        agents,
        and(
          eq(agents.id, heartbeatRuns.agentId),
          eq(agents.companyId, heartbeatRuns.companyId),
        ),
      )
      .where(
        and(
          eq(heartbeatRuns.id, this.#binding.runId),
          eq(heartbeatRuns.companyId, this.#binding.companyId),
          eq(heartbeatRuns.agentId, this.#binding.agentId),
          eq(heartbeatRuns.nativeIssueId, this.#binding.issueId),
          eq(heartbeatRuns.runtimeMode, "native"),
        ),
      )
      .limit(1);
    if (!row) throw new Error("paperclip_runner_semantic_binding_not_found");
    return row;
  }

  #assertActiveContext(context: BoundContext, requireOwnership: boolean): void {
    if (
      !["queued", "running"].includes(context.run.status) ||
      activeAgentStatus(context.agent.status) !== "active" ||
      (requireOwnership &&
        (context.issue.assigneeAgentId !== this.#binding.agentId ||
          context.issue.executionRunId !== this.#binding.runId))
    ) {
      throw new Error("paperclip_runner_semantic_binding_inactive");
    }
  }
}
