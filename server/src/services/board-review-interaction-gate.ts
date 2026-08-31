import { and, inArray, sql } from "drizzle-orm";
import type { Db } from "@paperclipai/db";
import { issueThreadInteractions, issues } from "@paperclipai/db";
import { unprocessable } from "../errors.js";

const BOARD_ACTION_INTERACTION_KINDS = new Set([
  "suggest_tasks",
  "ask_user_questions",
  "request_confirmation",
  "request_checkbox_confirmation",
  "request_item_verdicts",
]);

export type BoardReviewGateIssue = Pick<
  typeof issues.$inferSelect,
  "status" | "assigneeAgentId" | "assigneeUserId" | "reviewPolicy"
>;

export function isHumanOnlyResolverPolicy(value: unknown) {
  return value === "human_only" || value === "board_only";
}

export function boardReviewInteractionGateViolation(input: {
  issue: BoardReviewGateIssue;
  kind: string;
  resolverPolicy?: unknown;
}): string | null {
  const humanOnly = input.issue.reviewPolicy === "human_only"
    || isHumanOnlyResolverPolicy(input.resolverPolicy);
  if (!humanOnly) return null;
  if (input.issue.status !== "in_review") return "human_only interactions require issue status in_review";
  if (!input.issue.assigneeUserId || input.issue.assigneeAgentId) {
    return "human_only interactions require an exclusively Board-assigned issue";
  }
  if (!BOARD_ACTION_INTERACTION_KINDS.has(input.kind)) {
    return "human_only interactions require an approved Board action class";
  }
  return null;
}

export function assertBoardReviewInteractionGate(input: {
  issue: BoardReviewGateIssue;
  kind: string;
  resolverPolicy?: unknown;
}) {
  const violation = boardReviewInteractionGateViolation(input);
  if (violation) throw unprocessable(violation, { code: "board_review_interaction_gate" });
}

/**
 * Startup/periodic backstop for rows written before the synchronous gate, or
 * by an older server during a rolling restart. It preserves interaction and
 * issue history: invalid pending cards are terminalized in place and only the
 * stale Board assignment fields are cleared.
 */
export async function reconcileBoardReviewInteractionGate(db: Db) {
  const cancelled = await db.execute(sql`
    update ${issueThreadInteractions} as interaction
       set status = 'withdrawn',
           result = jsonb_build_object(
             'reason', 'Cancelled by Board-review gate reconciler: issue is not In Review and exclusively Board-assigned'
           ),
           resolved_at = now(),
           updated_at = now()
      from ${issues} as issue
     where interaction.issue_id = issue.id
       and interaction.status = 'pending'
       and interaction.effective_resolver_policy = 'human_only'
       and (
         issue.status <> 'in_review'
         or issue.assignee_user_id is null
         or issue.assignee_agent_id is not null
         or interaction.kind not in (
           'suggest_tasks', 'ask_user_questions', 'request_confirmation',
           'request_checkbox_confirmation', 'request_item_verdicts'
         )
       )
    returning interaction.id
  `);

  const unassigned = await db
    .update(issues)
    .set({ assigneeUserId: null, updatedAt: new Date() })
    .where(and(
      inArray(issues.status, ["blocked", "done", "cancelled"]),
      sql`${issues.assigneeUserId} is not null`,
    ))
    .returning({ id: issues.id });

  const cancelledRows = Array.isArray(cancelled)
    ? cancelled
    : ((cancelled as { rows?: unknown[] }).rows ?? []);

  return {
    cancelledInteractionIds: cancelledRows.map((row) => String((row as { id: unknown }).id)),
    removedBoardAssignmentIssueIds: unassigned.map((row) => row.id),
  };
}
