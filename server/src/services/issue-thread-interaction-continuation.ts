/**
 * Preserve the exact source-run compare-and-swap value from an accepted
 * interaction until heartbeat can atomically bind it to the execution run.
 */
export function acceptedInteractionSourceRunRebind(input: {
  id: string;
  status: string;
  sourceRunId?: string | null;
}) {
  if (input.status !== "accepted" || !input.sourceRunId) return undefined;
  return {
    interactionId: input.id,
    expectedSourceRunId: input.sourceRunId,
  };
}
