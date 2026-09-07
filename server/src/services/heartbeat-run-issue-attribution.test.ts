import { describe, expect, it, vi } from "vitest";
import { bindHeartbeatRunToCheckedOutIssue } from "./heartbeat-run-issue-attribution.js";

describe("bindHeartbeatRunToCheckedOutIssue", () => {
  it("binds only the exact company, agent, and timer-started run tuple", async () => {
    const then = vi.fn((resolve: (rows: Array<{ id: string }>) => unknown) => resolve([{ id: "run-1" }]));
    const returning = vi.fn(() => ({ then }));
    const where = vi.fn(() => ({ returning }));
    const set = vi.fn(() => ({ where }));
    const update = vi.fn(() => ({ set }));

    const result = await bindHeartbeatRunToCheckedOutIssue({ update } as any, {
      companyId: "company-1",
      agentId: "cos-agent",
      runId: "run-1",
      issueId: "source-issue",
    });

    expect(result).toEqual({ id: "run-1" });
    expect(update).toHaveBeenCalledTimes(1);
    expect(set).toHaveBeenCalledWith(expect.objectContaining({ contextSnapshot: expect.anything() }));
    expect(where).toHaveBeenCalledTimes(1);
  });

  it("fails closed when no matching live run can be attributed", async () => {
    const db = {
      update: () => ({
        set: () => ({
          where: () => ({
            returning: () => ({ then: (resolve: (rows: unknown[]) => unknown) => resolve([]) }),
          }),
        }),
      }),
    };

    await expect(bindHeartbeatRunToCheckedOutIssue(db as any, {
      companyId: "company-1",
      agentId: "cos-agent",
      runId: "unknown-run",
      issueId: "source-issue",
    })).resolves.toBeNull();
  });
});
