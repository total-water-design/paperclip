import { and, eq, or, sql } from "drizzle-orm";
import type { Db } from "@paperclipai/db";
import { validationExecutionGrants } from "@paperclipai/db";

export const TWDS_VALIDATION_GRANT = {
  approvalIssueId: "c2840abd-d4b5-46f1-bd73-ac8fbfd5078b", approvalCommentId: "99cf7940-1a77-4dd6-8e4a-bc6d9f24b24b",
  issueId: "ea9c1146-8ffa-4718-94d7-49c483d02969", candidateSha: "2298ccb3c33337e718ab37fb75d8d805fb020c14",
  contractSha: "96a6b59ca7a693756f419ce5adc1acde3a96ff8b", oracleSha: "73baefded458372ef679ca19a85803d50047ea9",
} as const;
export type ValidationTuple = Pick<typeof TWDS_VALIDATION_GRANT, "issueId" | "candidateSha" | "contractSha" | "oracleSha">;
export const isValidationExecutionOnlyAction = (action: string) => action === "validation_execution";

/** Called under the locked acceptance transaction. Every other confirmation is fail-closed. */
export async function createTwdsValidationGrant(tx: Db, input: { companyId: string; approvalIssueId: string; interaction: { id: string; kind: string; sourceCommentId: string | null; sourceRunId: string | null; effectiveResolverPolicy: string }; userId: string | null | undefined; now: Date }) {
  const i = input.interaction;
  if (input.approvalIssueId !== TWDS_VALIDATION_GRANT.approvalIssueId || i.kind !== "request_confirmation" || i.sourceCommentId !== TWDS_VALIDATION_GRANT.approvalCommentId || i.effectiveResolverPolicy !== "human_only" || !input.userId || !i.sourceRunId) return null;
  const [row] = await tx.insert(validationExecutionGrants).values({ companyId: input.companyId, approvalIssueId: input.approvalIssueId, approvalInteractionId: i.id, approvalCommentId: TWDS_VALIDATION_GRANT.approvalCommentId, approvalSourceRunId: i.sourceRunId, issueId: TWDS_VALIDATION_GRANT.issueId, candidateSha: TWDS_VALIDATION_GRANT.candidateSha, contractSha: TWDS_VALIDATION_GRANT.contractSha, oracleSha: TWDS_VALIDATION_GRANT.oracleSha, createdAt: input.now }).onConflictDoNothing().returning();
  return row ?? null;
}

export async function bindTwdsValidationGrantSuccessor(db: Db, input: { companyId: string; interactionId: string; sourceRunId: string; successorRunId: string }) {
  const [row] = await db.update(validationExecutionGrants).set({ successorRunId: input.successorRunId }).where(and(eq(validationExecutionGrants.companyId, input.companyId), eq(validationExecutionGrants.approvalInteractionId, input.interactionId), eq(validationExecutionGrants.approvalSourceRunId, input.sourceRunId), eq(validationExecutionGrants.status, "issued"), sql`${validationExecutionGrants.successorRunId} IS NULL`)).returning();
  return row ?? null;
}

export async function consumeTwdsValidationGrant(db: Db, input: { companyId: string; runId: string; action: string; tuple: ValidationTuple; now?: Date }) {
  if (!isValidationExecutionOnlyAction(input.action)) return { ok: false as const, code: "capability_denied" };
  return db.transaction(async (tx) => {
    const [grant] = await tx.select().from(validationExecutionGrants).where(and(eq(validationExecutionGrants.companyId, input.companyId), or(eq(validationExecutionGrants.approvalSourceRunId, input.runId), eq(validationExecutionGrants.successorRunId, input.runId)))).for("update");
    if (!grant) return { ok: false as const, code: "grant_not_found" };
    if (grant.status !== "issued") return { ok: false as const, code: "grant_unavailable" };
    const exact = grant.issueId === input.tuple.issueId && grant.candidateSha === input.tuple.candidateSha && grant.contractSha === input.tuple.contractSha && grant.oracleSha === input.tuple.oracleSha;
    const now = input.now ?? new Date();
    if (!exact) { await tx.update(validationExecutionGrants).set({ status: "invalidated", invalidatedAt: now, invalidationReason: "tuple_mismatch" }).where(eq(validationExecutionGrants.id, grant.id)); return { ok: false as const, code: "tuple_mismatch" }; }
    const [consumed] = await tx.update(validationExecutionGrants).set({ status: "consumed", consumerRunId: input.runId, consumedAt: now }).where(and(eq(validationExecutionGrants.id, grant.id), eq(validationExecutionGrants.status, "issued"))).returning({ id: validationExecutionGrants.id });
    return consumed ? { ok: true as const, grantId: consumed.id } : { ok: false as const, code: "grant_unavailable" };
  });
}

export async function invalidateTwdsValidationGrants(db: Db, input: { companyId: string; issueId: string; reason: "validation_completed" | "terminal_issue" | "expired"; now?: Date }) {
  return db.update(validationExecutionGrants).set({ status: "invalidated", invalidatedAt: input.now ?? new Date(), invalidationReason: input.reason }).where(and(eq(validationExecutionGrants.companyId, input.companyId), eq(validationExecutionGrants.issueId, input.issueId), eq(validationExecutionGrants.status, "issued"))).returning({ id: validationExecutionGrants.id });
}
