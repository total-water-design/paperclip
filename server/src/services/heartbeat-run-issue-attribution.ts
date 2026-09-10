import { and, eq, sql } from "drizzle-orm";
import type { Db } from "@paperclipai/db";
import { heartbeatRuns } from "@paperclipai/db";

/**
 * Bind an already-running heartbeat to the issue it successfully checked out.
 *
 * Timer-started portfolio runs may begin without an issue in their context
 * snapshot. Checkout establishes the source issue for run-scoped cross-issue
 * accounting, but only for the exact company/agent/run tuple authenticated by
 * the request. Returning null is fail-closed: callers must not report checkout
 * success when the supplied run cannot be bound.
 */
export async function bindHeartbeatRunToCheckedOutIssue(
  db: Db,
  input: { companyId: string; agentId: string; runId: string; issueId: string },
) {
  return db
    .update(heartbeatRuns)
    .set({
      contextSnapshot: sql`jsonb_set(
        jsonb_set(coalesce(${heartbeatRuns.contextSnapshot}, '{}'::jsonb), '{issueId}', to_jsonb(${input.issueId}::text), true),
        '{taskId}',
        to_jsonb(${input.issueId}::text),
        true
      )`,
    })
    .where(and(
      eq(heartbeatRuns.id, input.runId),
      eq(heartbeatRuns.companyId, input.companyId),
      eq(heartbeatRuns.agentId, input.agentId),
    ))
    .returning({ id: heartbeatRuns.id })
    .then((rows) => rows[0] ?? null);
}
