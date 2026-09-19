import { beforeEach, describe, expect, it, vi } from "vitest";

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock("./client", () => ({
  api: mockApi,
}));

import { heartbeatsApi } from "./heartbeats";

describe("heartbeatsApi.list", () => {
  beforeEach(() => {
    mockApi.get.mockReset();
    mockApi.get.mockResolvedValue([]);
  });

  it("requests summary rows for hot-path history consumers", async () => {
    await heartbeatsApi.list("company-1", undefined, 200, { summary: true });

    expect(mockApi.get).toHaveBeenCalledWith("/companies/company-1/heartbeat-runs?limit=200&summary=true");
  });

  it("keeps full row requests as the default for run-history screens", async () => {
    await heartbeatsApi.list("company-1", "agent-1", 25);

    expect(mockApi.get).toHaveBeenCalledWith("/companies/company-1/heartbeat-runs?agentId=agent-1&limit=25");
  });

  it("sends an explicit offset for subsequent pages", async () => {
    await heartbeatsApi.list("company-1", "agent-1", 25, { offset: 25 });

    expect(mockApi.get).toHaveBeenCalledWith("/companies/company-1/heartbeat-runs?agentId=agent-1&limit=25&offset=25");
  });

  it("uses bounded aggregate endpoints for stats and latest failures", async () => {
    await heartbeatsApi.stats("company-1", "agent-1");
    await heartbeatsApi.latestFailed("company-1");

    expect(mockApi.get).toHaveBeenNthCalledWith(1, "/companies/company-1/heartbeat-runs/stats?agentId=agent-1");
    expect(mockApi.get).toHaveBeenNthCalledWith(2, "/companies/company-1/heartbeat-runs/latest-failed");
  });
});

describe("heartbeatsApi.liveRunsForCompany", () => {
  beforeEach(() => {
    mockApi.get.mockReset();
    mockApi.get.mockResolvedValue([]);
  });

  it("keeps the legacy numeric minCount signature", async () => {
    await heartbeatsApi.liveRunsForCompany("company-1", 4);

    expect(mockApi.get).toHaveBeenCalledWith("/companies/company-1/live-runs?minCount=4");
  });

  it("passes minCount and limit options to the company live-runs endpoint", async () => {
    await heartbeatsApi.liveRunsForCompany("company-1", { minCount: 50, limit: 50 });

    expect(mockApi.get).toHaveBeenCalledWith("/companies/company-1/live-runs?minCount=50&limit=50");
  });
});
