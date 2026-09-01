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
  };
}

function app(
  token: string | undefined,
  service = heartbeat(),
  remoteAddress?: string,
) {
  const instance = express();
  instance.use(express.json());
  if (remoteAddress) {
    instance.use((req, _res, next) => {
      Object.defineProperty(req.socket, "remoteAddress", { value: remoteAddress });
      next();
    });
  }
  instance.use("/api", recoveryRoutes({ recoveryToken: token, heartbeat: service }));
  return { instance, service };
}

describe("fixed recovery reconciliation route", () => {
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
