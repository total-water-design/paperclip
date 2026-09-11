import { jsonb, pgTable, text, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";

import { companies } from "./companies.js";

/**
 * Durable outcomes for mutations invoked through the native runner semantic
 * authority. The scope is a digest of the run, operation, and caller key.
 */
export const semanticActionReceipts = pgTable(
  "semantic_action_receipts",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    companyId: uuid("company_id").notNull().references(() => companies.id, { onDelete: "cascade" }),
    scope: text("scope").notNull(),
    operationId: text("operation_id").notNull(),
    inputDigest: text("input_digest").notNull(),
    outcome: jsonb("outcome").$type<Record<string, unknown> | null>(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => ({
    companyScopeUq: uniqueIndex("semantic_action_receipts_company_scope_uq").on(
      table.companyId,
      table.scope,
    ),
  }),
);
