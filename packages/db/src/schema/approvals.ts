import { sql } from "drizzle-orm";
import { pgTable, uuid, text, timestamp, jsonb, index, uniqueIndex } from "drizzle-orm/pg-core";
import { companies } from "./companies.js";
import { agents } from "./agents.js";

export const approvals = pgTable(
  "approvals",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    companyId: uuid("company_id").notNull().references(() => companies.id),
    type: text("type").notNull(),
    requestedByAgentId: uuid("requested_by_agent_id").references(() => agents.id),
    requestedByUserId: text("requested_by_user_id"),
    status: text("status").notNull().default("pending"),
    payload: jsonb("payload").$type<Record<string, unknown>>().notNull(),
    openDeduplicationKey: text("open_deduplication_key"),
    decisionNote: text("decision_note"),
    decidedByUserId: text("decided_by_user_id"),
    decidedAt: timestamp("decided_at", { withTimezone: true }),
    cancellationReason: text("cancellation_reason"),
    cancelledByAgentId: uuid("cancelled_by_agent_id").references(() => agents.id),
    cancelledByUserId: text("cancelled_by_user_id"),
    cancelledAt: timestamp("cancelled_at", { withTimezone: true }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => ({
    companyStatusTypeIdx: index("approvals_company_status_type_idx").on(
      table.companyId,
      table.status,
      table.type,
    ),
    companyOpenDeduplicationIdx: uniqueIndex("approvals_company_open_deduplication_uq")
      .on(table.companyId, table.openDeduplicationKey)
      .where(sql`${table.type} = 'request_board_approval' and ${table.status} in ('pending', 'revision_requested') and ${table.openDeduplicationKey} is not null`),
  }),
);
