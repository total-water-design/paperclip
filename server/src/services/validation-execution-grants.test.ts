import { describe, expect, it } from "vitest";
import { TWDS_VALIDATION_GRANT, isValidationExecutionOnlyAction } from "./validation-execution-grants.js";

describe("TWDS validation execution grant boundary", () => {
  it("has one immutable validation tuple", () => {
    expect(TWDS_VALIDATION_GRANT).toEqual({
      approvalIssueId: "c2840abd-d4b5-46f1-bd73-ac8fbfd5078b",
      approvalCommentId: "99cf7940-1a77-4dd6-8e4a-bc6d9f24b24b",
      issueId: "ea9c1146-8ffa-4718-94d7-49c483d02969",
      candidateSha: "2298ccb3c33337e718ab37fb75d8d805fb020c14",
      contractSha: "96a6b59ca7a693756f419ce5adc1acde3a96ff8b",
      oracleSha: "73baefded458372ef679ca19a85803d50047ea9",
    });
  });

  it.each(["repository_mutation", "merge", "promotion", "deployment", "force_push", "protected_alpha_change", "scope_waiver", "tolerance_change", "observed_output_golden_creation"])("does not authorize %s", (action) => {
    expect(isValidationExecutionOnlyAction(action)).toBe(false);
  });

  it("authorizes only validation execution", () => {
    expect(isValidationExecutionOnlyAction("validation_execution")).toBe(true);
  });
});
