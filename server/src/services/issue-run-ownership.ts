/**
 * The fail-closed first-claim gate for an in-progress issue. A wake-created
 * execution run may adopt an empty checkout lock only when it is the exact
 * executionRunId already stored on that issue.
 */
export function canAdoptExactExecutionRunOwnership(input: {
  status: string;
  assigneeAgentId: string | null;
  checkoutRunId: string | null;
  executionRunId: string | null;
  actorAgentId: string;
  actorRunId: string | null;
}) {
  return Boolean(
    input.actorRunId
    && input.status === "in_progress"
    && input.assigneeAgentId === input.actorAgentId
    && input.checkoutRunId == null
    && (input.executionRunId == null || input.executionRunId === input.actorRunId),
  );
}
