import express from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";
import { recoveryRoutes } from "./recovery.js";

function heartbeat() {
  return {
    getRecoveryRunInventory: vi.fn()
      .mockResolvedValueOnce({ activeRunIds: ["run-live"], queuedRunIds: [] })
      .mockResolvedValueOnce({ activeRunIds: [], queuedRunIds: ["run-retry"] }),
    reapOrphanedRuns: vi.fn().mockResolvedValue({ reaped: 1, runIds: ["run-stale"] }),
    promoteDueScheduledRetries: vi.fn().mockResolvedValue({ promoted: 1, runIds: ["run-retry"] }),
    resumeQueuedRuns: vi.fn().mockResolvedValue(undefined),
    reconcileStrandedAssignedIssues: vi.fn().mockResolvedValue({ assignmentDispatched: 1 }),
    sweepStaleIssueLocks: vi.fn().mockResolvedValue({
      cleared: 1,
      issueIds: ["issue-stale-lock"],
      terminalizedRunIds: ["run-stale"],
    }),
    getSafeWindowInventory: vi.fn().mockResolvedValue({
      company: { id: "company-a", status: "active" },
      runs: [],
      issues: [],
    }),
  };
}

function app(
  token: string | undefined,
  service = heartbeat(),
  remoteAddress?: string,
  inventoryToken?: string,
  inventoryCompanyId?: string,
) {
  const instance = express();
  instance.use(express.json());
  if (remoteAddress) {
    instance.use((req, _res, next) => {
      Object.defineProperty(req.socket, "remoteAddress", { value: remoteAddress });
      next();
    });
  }
  instance.use("/api", recoveryRoutes({
    recoveryToken: token,
    safeWindowInventoryToken: inventoryToken,
    safeWindowInventoryCompanyId: inventoryCompanyId,
    heartbeat: service,
  }));
  return { instance, service };
}

describe("fixed recovery reconciliation route", () => {
  it("returns a scoped read-only inventory without invoking recovery operations", async () => {
    const service = heartbeat();
    const { instance } = app("recovery-secret", service, undefined, "inventory-secret", "company-a");

    const response = await request(instance)
      .get("/api/recovery/safe-window-inventory")
      .set("x-paperclip-safe-window-inventory-token", "inventory-secret")
      .expect(200);

    expect(response.body).toMatchObject({
      contractVersion: "safe_window_inventory.v1",
      caller: { principal: "safe_window_inventory", companyId: "company-a" },
    });
    expect(service.getSafeWindowInventory).toHaveBeenCalledWith("company-a");
    expect(service.reapOrphanedRuns).not.toHaveBeenCalled();
    expect(service.promoteDueScheduledRetries).not.toHaveBeenCalled();
    expect(service.resumeQueuedRuns).not.toHaveBeenCalled();
    expect(service.reconcileStrandedAssignedIssues).not.toHaveBeenCalled();
    expect(service.sweepStaleIssueLocks).not.toHaveBeenCalled();
  });

  it("denies missing or unrelated safe-window principals", async () => {
    const service = heartbeat();
    const { instance } = app("recovery-secret", service, undefined, "inventory-secret", "company-a");
    await request(instance).get("/api/recovery/safe-window-inventory").expect(401);
    await request(instance)
      .get("/api/recovery/safe-window-inventory")
      .set("x-paperclip-safe-window-inventory-token", "unrelated-token")
      .expect(401);
    expect(service.getSafeWindowInventory).not.toHaveBeenCalled();
  });

  it("denies non-loopback safe-window callers", async () => {
    const service = heartbeat();
    const { instance } = app("recovery-secret", service, "203.0.113.8", "inventory-secret", "company-a");
    await request(instance)
      .get("/api/recovery/safe-window-inventory")
      .set("x-paperclip-safe-window-inventory-token", "inventory-secret")
      .expect(403);
    expect(service.getSafeWindowInventory).not.toHaveBeenCalled();
  });

  it("binds inventory reads to the configured company and ignores caller-selected scope", async () => {
    const service = heartbeat();
    const { instance } = app("recovery-secret", service, undefined, "inventory-secret", "company-a");
    await request(instance)
      .get("/api/recovery/safe-window-inventory?companyId=company-b")
      .set("x-paperclip-safe-window-inventory-token", "inventory-secret")
      .expect(200);
    expect(service.getSafeWindowInventory).toHaveBeenCalledWith("company-a");
  });

  it("rejects a missing recovery principal without running reconciliation", async () => {
    const { instance, service } = app(undefined);
    await request(instance).post("/api/recovery/reconcile").expect(503);
    expect(service.getRecoveryRunInventory).not.toHaveBeenCalled();
  });

  it("rejects an unauthenticated request without exposing a control operation", async () => {
    const { instance, service } = app("recovery-secret");
    await request(instance).post("/api/recovery/reconcile").expect(401);
    expect(service.reapOrphanedRuns).not.toHaveBeenCalled();
  });

  it("rejects a token-authenticated non-loopback request without running reconciliation", async () => {
    const { instance, service } = app("recovery-secret", heartbeat(), "203.0.113.8");
    await request(instance)
      .post("/api/recovery/reconcile")
      .set("x-paperclip-recovery-token", "recovery-secret")
      .expect(403);
    expect(service.getRecoveryRunInventory).not.toHaveBeenCalled();
  });

  it("uses only the canonical service inventory and reconciliation sequence", async () => {
    const { instance, service } = app("recovery-secret");

    const response = await request(instance)
      .post("/api/recovery/reconcile")
      .set("x-paperclip-recovery-token", "recovery-secret")
      .send({ ignored: "no request parameters are accepted" })
      .expect(200);

    expect(response.body).toEqual({
      inventory: {
        before: { activeRunIds: ["run-live"], queuedRunIds: [] },
        after: { activeRunIds: [], queuedRunIds: ["run-retry"] },
      },
      reconciled: {
        orphanedRunIds: ["run-stale"],
        promotedRetryRunIds: ["run-retry"],
        terminalizedStaleRunIds: ["run-stale"],
        clearedStaleIssueLockIds: ["issue-stale-lock"],
        stranded: { assignmentDispatched: 1 },
      },
    });
    expect(service.getRecoveryRunInventory).toHaveBeenCalledTimes(2);
    expect(service.reapOrphanedRuns).toHaveBeenCalledTimes(1);
    expect(service.resumeQueuedRuns).toHaveBeenCalledTimes(1);
  });
});
