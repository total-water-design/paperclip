import { describe, expect, it } from "vitest";
import {
  TWDS_COMPANY_ID,
  TWDS_PROJECT_ID,
  shouldDefaultTwdsIssueProject,
} from "./twds-issue-defaults.js";

describe("TWDS issue defaults", () => {
  const engineer = {
    companyId: TWDS_COMPANY_ID,
    role: "engineer",
    name: "TWDS Pilot Implementation Engineer 2",
    title: "Implementation Engineer",
  };

  it("defaults an omitted project for a TWDS engineer or QA agent", () => {
    expect(shouldDefaultTwdsIssueProject({
      companyId: TWDS_COMPANY_ID,
      requestedProjectId: undefined,
      assignee: engineer,
    })).toBe(true);
    expect(TWDS_PROJECT_ID).toBe("b1472d84-5dd2-4082-8aa4-08186ae970ee");
  });

  it("preserves explicit project selection and excludes non-TWDS roles", () => {
    expect(shouldDefaultTwdsIssueProject({
      companyId: TWDS_COMPANY_ID,
      requestedProjectId: "00000000-0000-4000-8000-000000000001",
      assignee: engineer,
    })).toBe(false);
    expect(shouldDefaultTwdsIssueProject({
      companyId: TWDS_COMPANY_ID,
      requestedProjectId: undefined,
      assignee: { ...engineer, role: "designer", name: "TWDS UI/UX Reviewer" },
    })).toBe(false);
  });
});
