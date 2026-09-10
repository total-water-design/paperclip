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

  it("fails closed when governed action text is hidden outside the action fields", () => {
    expect(classifyBoardApprovalRequest({
      title: "Collect read-only evidence",
      summary: "After collection, deploy the Alpha shared service.",
    })).toMatchObject({
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
    expect(same.authorizationFingerprint).toBe(first.authorizationFingerprint);
    expect(differentSha.authorizationFingerprint).not.toBe(first.authorizationFingerprint);
  });

  it("does not establish approved authorization identity from an idempotency key alone", () => {
    const identity = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["issue-1"],
      payload: { idempotencyKey: "deploy-once" },
    });
    expect(identity.exactIdentityEstablished).toBe(false);
  });

  it("does not treat an abbreviated candidate hash as immutable authorization identity", () => {
    const identity = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["issue-1"],
      payload: { action: "deploy", scope: "alpha", candidateSha: "0123456" },
    });
    expect(identity.exactIdentityEstablished).toBe(false);
  });

  it("ignores request deduplication keys once exact approved identity is established", () => {
    const payload = {
      action: "deploy",
      target: "alpha",
      candidateSha: "0123456789abcdef0123456789abcdef01234567",
    };
    const first = boardApprovalRequestIdentity({
      type: "request_board_approval", issueIds: ["issue-1"], payload: { ...payload, idempotencyKey: "request-1" },
    });
    const repeated = boardApprovalRequestIdentity({
      type: "request_board_approval", issueIds: ["issue-1"], payload: { ...payload, idempotencyKey: "request-2" },
    });
    expect(first.exactIdentityEstablished).toBe(true);
    expect(repeated.authorizationFingerprint).toBe(first.authorizationFingerprint);
  });

  it("normalizes linked issue ordering, action prefixes, case, and scope arrays", () => {
    const first = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["issue-b", "issue-a", "issue-a"],
      payload: {
        title: "Authorize the Production Deployment",
        scope: { resources: ["Service-B", "service-a"] },
      },
    });
    const same = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["issue-a", "issue-b"],
      payload: {
        title: "production deployment",
        scope: { resources: ["SERVICE-A", "service-b"] },
      },
    });
    expect(same.openDeduplicationKey).toBe(first.openDeduplicationKey);
  });

  it("uses the named operational records as immutable identity fixtures", () => {
    const duplicateA = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["TOT-3098"],
      payload: {
        title: "Authorize bounded read-only staged-host topology collection",
        summary: "fixture 544365d1-e653-4c55-a290-fca919ffbf1f",
      },
    });
    const duplicateB = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["TOT-3098"],
      payload: {
        title: "Authorize bounded read-only staged-host topology collection",
        summary: "fixture d93fefee-488a-4d93-a43a-7199d88d0ab9 with reworded support",
      },
    });
    const stale = boardApprovalRequestIdentity({
      type: "request_board_approval",
      issueIds: ["TOT-1912"],
      payload: {
        title: "Authorize bounded TOT-1912 smoke probes",
        summary: "fixture eb43b4e8-65c0-4cc8-b2c6-917ccf71c1fc",
      },
    });
    expect(duplicateB.openDeduplicationKey).toBe(duplicateA.openDeduplicationKey);
    expect(stale.openDeduplicationKey).not.toBe(duplicateA.openDeduplicationKey);
  });
});
