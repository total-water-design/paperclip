import { sql } from "drizzle-orm";
import { check, index, pgTable, text, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { companies } from "./companies.js";
import { heartbeatRuns } from "./heartbeat_runs.js";
import { issueComments } from "./issue_comments.js";
import { issueThreadInteractions } from "./issue_thread_interactions.js";
import { issues } from "./issues.js";

/** A deliberately non-general, single-use authority for TWDS validation only. */
export const validationExecutionGrants = pgTable("validation_execution_grants", {
  id: uuid("id").primaryKey().defaultRandom(),
  companyId: uuid("company_id").notNull().references(() => companies.id, { onDelete: "cascade" }),
  approvalIssueId: uuid("approval_issue_id").notNull().references(() => issues.id),
  approvalInteractionId: uuid("approval_interaction_id").notNull().references(() => issueThreadInteractions.id),
  approvalCommentId: uuid("approval_comment_id").notNull().references(() => issueComments.id),
  approvalSourceRunId: uuid("approval_source_run_id").references(() => heartbeatRuns.id, { onDelete: "set null" }),
  successorRunId: uuid("successor_run_id").references(() => heartbeatRuns.id, { onDelete: "set null" }),
  consumerRunId: uuid("consumer_run_id").references(() => heartbeatRuns.id, { onDelete: "set null" }),
  issueId: uuid("issue_id").notNull().references(() => issues.id),
  candidateSha: text("candidate_sha").notNull(), contractSha: text("contract_sha").notNull(), oracleSha: text("oracle_sha").notNull(),
  capability: text("capability").notNull().default("validation_execution"), status: text("status").notNull().default("issued"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(), expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(), consumedAt: timestamp("consumed_at", { withTimezone: true }),
  invalidatedAt: timestamp("invalidated_at", { withTimezone: true }), invalidationReason: text("invalidation_reason"),
}, (t) => ({
  approvalUq: uniqueIndex("validation_execution_grants_approval_interaction_uq").on(t.approvalInteractionId),
  successorUq: uniqueIndex("validation_execution_grants_successor_run_uq").on(t.successorRunId).where(sql`${t.successorRunId} IS NOT NULL`),
  consumerUq: uniqueIndex("validation_execution_grants_consumer_run_uq").on(t.consumerRunId).where(sql`${t.consumerRunId} IS NOT NULL`),
  issuedIdx: index("validation_execution_grants_issued_issue_idx").on(t.companyId, t.issueId, t.status),
  capabilityCheck: check("validation_execution_grants_capability_check", sql`${t.capability} = 'validation_execution'`),
  statusCheck: check("validation_execution_grants_status_check", sql`${t.status} IN ('issued','consumed','invalidated')`),
}));
