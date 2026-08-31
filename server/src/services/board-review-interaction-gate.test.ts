import { describe, expect, it } from "vitest";
import { boardReviewInteractionGateViolation } from "./board-review-interaction-gate.js";

const validIssue = {
  status: "in_review",
  assigneeAgentId: null,
  assigneeUserId: "board-user",
  reviewPolicy: null,
};

describe("Board review interaction gate", () => {
  it("allows ordinary interactions outside the human-only policy", () => {
    expect(boardReviewInteractionGateViolation({
      issue: { ...validIssue, status: "in_progress", assigneeUserId: null },
      kind: "ask_user_questions",
      resolverPolicy: "anyone",
    })).toBeNull();
  });

  it.each([
    [{ ...validIssue, status: "blocked" }, "human_only interactions require issue status in_review"],
    [{ ...validIssue, assigneeUserId: null }, "human_only interactions require an exclusively Board-assigned issue"],
    [{ ...validIssue, assigneeAgentId: "agent-id" }, "human_only interactions require an exclusively Board-assigned issue"],
  ])("rejects an invalid human-only issue state", (issue, message) => {
    expect(boardReviewInteractionGateViolation({
      issue,
      kind: "request_confirmation",
      resolverPolicy: "human_only",
    })).toBe(message);
  });

  it("enforces the gate inherited from issue review policy", () => {
    expect(boardReviewInteractionGateViolation({
      issue: { ...validIssue, status: "todo", reviewPolicy: "human_only" },
      kind: "request_confirmation",
    })).toContain("in_review");
  });

  it("accepts compatibility board_only only for a valid Board review", () => {
    expect(boardReviewInteractionGateViolation({
      issue: validIssue,
      kind: "request_item_verdicts",
      resolverPolicy: "board_only",
    })).toBeNull();
  });

  it("rejects an unknown action class", () => {
    expect(boardReviewInteractionGateViolation({
      issue: validIssue,
      kind: "arbitrary_action",
      resolverPolicy: "human_only",
    })).toContain("approved Board action class");
  });
});
