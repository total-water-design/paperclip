import { timingSafeEqual } from "node:crypto";
import { Router, type Request } from "express";

/**
 * The recovery endpoint is deliberately outside the ordinary board/agent
 * permission model. It is for the fixed, host-local recovery helper only:
 * no caller-selected company, run, issue, command, or operation is accepted.
 */
function isLoopbackRequest(req: Request) {
  const address = req.socket.remoteAddress ?? "";
  return address === "127.0.0.1" || address === "::1" || address === "::ffff:127.0.0.1";
}

function tokenMatches(candidate: unknown, expected: string) {
  if (typeof candidate !== "string") return false;
  const actual = Buffer.from(candidate, "utf8");
  const wanted = Buffer.from(expected, "utf8");
  return actual.length === wanted.length && timingSafeEqual(actual, wanted);
}

/**
 * A distinct principal for IV&R safe-window snapshots.  It is intentionally
 * separate from the recovery principal: possessing this token authorizes a
 * read-only view for exactly one configured company, never reconciliation.
 */
function safeWindowInventoryIdentity(options: {
  safeWindowInventoryToken?: string;
  safeWindowInventoryCompanyId?: string;
}) {
  const token = options.safeWindowInventoryToken?.trim() ?? "";
  const companyId = options.safeWindowInventoryCompanyId?.trim() ?? "";
  return token && companyId ? { token, companyId } : null;
}

export function recoveryRoutes(options: {
  recoveryToken?: string;
  safeWindowInventoryToken?: string;
  safeWindowInventoryCompanyId?: string;
  heartbeat: {
    getRecoveryRunInventory: () => Promise<{ activeRunIds: string[]; queuedRunIds: string[] }>;
    reapOrphanedRuns: () => Promise<{ reaped: number; runIds: string[] }>;
    promoteDueScheduledRetries: () => Promise<{ promoted: number; runIds: string[] }>;
    resumeQueuedRuns: () => Promise<void>;
    reconcileStrandedAssignedIssues: () => Promise<Record<string, unknown>>;
    sweepStaleIssueLocks: () => Promise<{ cleared: number; issueIds: string[]; terminalizedRunIds: string[] }>;
    getSafeWindowInventory: (companyId: string) => Promise<unknown>;
  };
}) {
  const router = Router();
  const recoveryToken = options.recoveryToken?.trim() ?? "";
  // Resolve once at router construction. A successful request neither reads a
  // secret file nor resolves process environment or caller-selected scope.
  const inventoryIdentity = safeWindowInventoryIdentity(options);

  router.get("/recovery/safe-window-inventory", async (req, res) => {
    // This principal is deliberately independent of PAPERCLIP_RECOVERY_TOKEN.
    // No body, query, or company selector is accepted; the token is bound to
    // the configured company and so cannot be used for cross-company reads.
    if (!inventoryIdentity) {
      res.status(503).json({ error: "Safe-window inventory principal is not configured" });
      return;
    }
    if (!isLoopbackRequest(req)) {
      res.status(403).json({ error: "Safe-window inventory is loopback-only" });
      return;
    }
    if (!tokenMatches(req.get("x-paperclip-safe-window-inventory-token"), inventoryIdentity.token)) {
      res.status(401).json({ error: "Safe-window inventory authentication failed" });
      return;
    }

    // getSafeWindowInventory is a select-only snapshot method. Do not add
    // wake, enqueue, resume, reconciliation, secret, privilege, filesystem,
    // subprocess, or service-control work to this route.
    const inventory = await options.heartbeat.getSafeWindowInventory(inventoryIdentity.companyId);
    res.json({
      contractVersion: "safe_window_inventory.v1",
      caller: { principal: "safe_window_inventory", companyId: inventoryIdentity.companyId },
      inventory,
    });
  });

  router.post("/recovery/reconcile", async (req, res) => {
    // Fail closed if the recovery principal was not provisioned. In particular,
    // local_trusted must not turn this into an unauthenticated control route.
    if (!recoveryToken) {
      res.status(503).json({ error: "Recovery principal is not configured" });
      return;
    }
    if (!isLoopbackRequest(req)) {
      res.status(403).json({ error: "Recovery reconciliation is loopback-only" });
      return;
    }
    if (!tokenMatches(req.get("x-paperclip-recovery-token"), recoveryToken)) {
      res.status(401).json({ error: "Recovery authentication failed" });
      return;
    }

    // The inventory and all state changes stay inside the application service.
    // This route deliberately takes no input and never probes or edits Postgres
    // itself; the service owns authoritative status and stale-run handling.
    const before = await options.heartbeat.getRecoveryRunInventory();
    const reaped = await options.heartbeat.reapOrphanedRuns();
    const promoted = await options.heartbeat.promoteDueScheduledRetries();
    await options.heartbeat.resumeQueuedRuns();
    const stranded = await options.heartbeat.reconcileStrandedAssignedIssues();
    const staleLocks = await options.heartbeat.sweepStaleIssueLocks();
    const after = await options.heartbeat.getRecoveryRunInventory();

    res.json({
      inventory: { before, after },
      reconciled: {
        orphanedRunIds: reaped.runIds,
        promotedRetryRunIds: promoted.runIds,
        terminalizedStaleRunIds: staleLocks.terminalizedRunIds,
        clearedStaleIssueLockIds: staleLocks.issueIds,
        stranded,
      },
    });
  });

  return router;
}
