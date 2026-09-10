import { describe, expect, it } from "vitest";
import {
  addApprovalCommentSchema,
  cancelApprovalSchema,
  requestApprovalRevisionSchema,
  resolveApprovalSchema,
} from "./approval.js";

describe("approval validators", () => {
  it("passes real line breaks through unchanged", () => {
    expect(addApprovalCommentSchema.parse({ body: "Looks good\n\nApproved." }).body)
      .toBe("Looks good\n\nApproved.");
    expect(resolveApprovalSchema.parse({ decisionNote: "Decision\n\nApproved." }).decisionNote)
      .toBe("Decision\n\nApproved.");
  });

  it("requires a cancellation reason while accepting the legacy decisionNote field", () => {
    expect(cancelApprovalSchema.parse({ reason: "Duplicate request" }).reason).toBe("Duplicate request");
    expect(cancelApprovalSchema.parse({ decisionNote: "Stale request" }).decisionNote).toBe("Stale request");
    expect(() => cancelApprovalSchema.parse({})).toThrow("Cancellation reason is required");
    expect(() => cancelApprovalSchema.parse({ reason: "   " })).toThrow("Cancellation reason is required");
  });

  it("accepts null and omitted optional decision notes", () => {
    expect(resolveApprovalSchema.parse({ decisionNote: null }).decisionNote).toBeNull();
    expect(resolveApprovalSchema.parse({}).decisionNote).toBeUndefined();
    expect(requestApprovalRevisionSchema.parse({ decisionNote: null }).decisionNote).toBeNull();
    expect(requestApprovalRevisionSchema.parse({}).decisionNote).toBeUndefined();
  });

  it("normalizes escaped line breaks in approval comments and decision notes", () => {
    expect(addApprovalCommentSchema.parse({ body: "Looks good\\n\\nApproved." }).body)
      .toBe("Looks good\n\nApproved.");
    expect(resolveApprovalSchema.parse({ decisionNote: "Decision\\n\\nApproved." }).decisionNote)
      .toBe("Decision\n\nApproved.");
    expect(requestApprovalRevisionSchema.parse({ decisionNote: "Decision\\r\\nRevise." }).decisionNote)
      .toBe("Decision\nRevise.");
  });
});
