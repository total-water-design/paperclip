/**
 * Company-local defaulting for the Total Water Design Suite (TWDS) pilot.
 *
 * This deliberately lives behind both the company id and a TWDS engineer/QA
 * identity check.  It must never turn an ordinary Paperclip assignment into a
 * TWDS worktree task just because an agent happens to have an engineering
 * role.
 */
export const TWDS_COMPANY_ID = "b3d4c323-12f9-4291-82cb-816623d0de84";
export const TWDS_PROJECT_ID = "b1472d84-5dd2-4082-8aa4-08186ae970ee";

export type TwdsAssignmentAgent = {
  companyId: string;
  role: string;
  name: string;
  title?: string | null;
};

export function shouldDefaultTwdsIssueProject(input: {
  companyId: string;
  requestedProjectId: string | null | undefined;
  assignee: TwdsAssignmentAgent | null | undefined;
}): boolean {
  if (input.requestedProjectId !== undefined) return false;
  if (input.companyId !== TWDS_COMPANY_ID || !input.assignee) return false;
  if (input.assignee.companyId !== TWDS_COMPANY_ID) return false;
  if (input.assignee.role !== "engineer" && input.assignee.role !== "qa") return false;
  return /\bTWDS\b/i.test(`${input.assignee.name} ${input.assignee.title ?? ""}`);
}
