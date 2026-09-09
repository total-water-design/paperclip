import { describe, expect, it } from "vitest";
import {
  boardApprovalRequestIdentity,
  classifyBoardApprovalRequest,
} from "../services/approval-governance.js";

describe("Board approval governance", () => {
  it.each([
    "Collect read-only host-state evidence",
    "Run bounded smoke-test diagnostics",
    "Inspect CI checks and workspace topology",
  ])("delegates routine action: %s", (title) => {
    expect(classifyBoardApprovalRequest({ title })).toMatchObject({
      outcome: "delegated",
      reasonCode: "ROUTINE_DELEGATED_ACTION",
    });
  });

  it.each([
    ["Approve production deployment", "DEPLOYMENT"],
    ["Authorize merge into protected alpha branch", "PROTECTED_REFERENCE_MUTATION"],
    ["Approve destructive production data migration", "IRREVERSIBLE_ACTION"],
    ["Grant new root privilege", "MATERIAL_SECURITY_OR_ACCESS_POLICY"],
    ["Approve unbudgeted spend", "EXTERNALLY_CONSEQUENTIAL_ACTION"],
  ])("keeps governed action at the Board: %s", (title, reasonCode) => {
    expect(classifyBoardApprovalRequest({ title })).toMatchObject({
      outcome: "board_gate",
      reasonCode,
    });
  });

  it("requires COS classification for an unknown request", () => {
    expect(classifyBoardApprovalRequest({ title: "Please decide" })).toMatchObject({
      outcome: "route_to_cos",
      reasonCode: "COS_REVIEW_REQUIRED",
    });
  });

  it("binds reusable authorization to issue scope and exact candidate identity", () => {
    const first = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["issue-1"],
      payload: {
        title: "Approve production deployment",
        action: "deploy",
        scope: "alpha",
        candidateSha: "0123456789abcdef0123456789abcdef01234567",
      },
    });
    const same = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["issue-1"],
      payload: {
        title: "Approve production deployment",
        action: "deploy",
        scope: "alpha",
        candidateSha: "0123456789abcdef0123456789abcdef01234567",
      },
    });
    const differentSha = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["issue-1"],
      payload: {
        title: "Approve production deployment",
        action: "deploy",
        scope: "alpha",
        candidateSha: "abcdef0123456789abcdef0123456789abcdef01",
      },
    });

    expect(first.exactIdentityEstablished).toBe(true);
    expect(same.fingerprint).toBe(first.fingerprint);
    expect(differentSha.fingerprint).not.toBe(first.fingerprint);
  });
});
