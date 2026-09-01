import { sql } from "drizzle-orm";
import { check, index, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";
import { agents } from "./agents.js";
import { companies } from "./companies.js";
import { companySecretBindings } from "./company_secret_bindings.js";
import { heartbeatRuns } from "./heartbeat_runs.js";
import { issues } from "./issues.js";

/** Auditable, revocable authority to expose one existing binding to one agent and issue/run. */
export const managedSecretCapabilityGrants = pgTable("managed_secret_capability_grants", {
  id: uuid("id").primaryKey().defaultRandom(),
  companyId: uuid("company_id").notNull().references(() => companies.id, { onDelete: "cascade" }),
  bindingId: uuid("binding_id").notNull().references(() => companySecretBindings.id, { onDelete: "cascade" }),
  agentId: uuid("agent_id").notNull().references(() => agents.id, { onDelete: "cascade" }),
  issueId: uuid("issue_id").references(() => issues.id, { onDelete: "cascade" }),
  runId: uuid("run_id").references(() => heartbeatRuns.id, { onDelete: "cascade" }),
  status: text("status").notNull().default("active"),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  createdByUserId: text("created_by_user_id"),
  revokedByUserId: text("revoked_by_user_id"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
  revocationReason: text("revocation_reason"),
}, (t) => ({
  scopeIdx: index("managed_secret_capability_grants_scope_idx").on(t.companyId, t.agentId, t.issueId, t.runId, t.status),
  bindingIdx: index("managed_secret_capability_grants_binding_idx").on(t.bindingId),
  scopeCheck: check("managed_secret_capability_grants_scope_check", sql`(${t.issueId} IS NOT NULL) <> (${t.runId} IS NOT NULL)`),
  statusCheck: check("managed_secret_capability_grants_status_check", sql`${t.status} IN ('active','revoked')`),
}));
