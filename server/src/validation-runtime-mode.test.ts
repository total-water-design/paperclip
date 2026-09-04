import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { isValidationRuntimeRequest, resolveValidationRuntimePolicy, VALIDATION_RUNTIME_MODE } from "./validation-runtime-mode.js";

describe("bounded DAF validation runtime", () => {
  it("is inert unless explicitly selected", () => {
    expect(resolveValidationRuntimePolicy({ host: "0.0.0.0" })).toMatchObject({ enabled: false, applyMigrations: true });
  });

  it("fails closed outside an explicit non-production loopback invocation with an existing database", () => {
    expect(() => resolveValidationRuntimePolicy({ mode: VALIDATION_RUNTIME_MODE, nodeEnv: "production", host: "127.0.0.1", databaseUrl: "postgres://db" })).toThrow("unavailable");
    expect(() => resolveValidationRuntimePolicy({ mode: VALIDATION_RUNTIME_MODE, host: "0.0.0.0", databaseUrl: "postgres://db" })).toThrow("loopback");
    expect(() => resolveValidationRuntimePolicy({ mode: VALIDATION_RUNTIME_MODE, host: "127.0.0.1" })).toThrow("external DATABASE_URL");
  });

  it("disables every startup mutation owner named by the validation contract", () => {
    expect(resolveValidationRuntimePolicy({ mode: VALIDATION_RUNTIME_MODE, nodeEnv: "test", host: "127.0.0.1", databaseUrl: "postgres://db" })).toEqual({
      enabled: true, serveUi: false, applyMigrations: false, runBackups: false,
      runHeartbeatScheduler: false, runStartupReconciliation: false, runBackgroundJobs: false,
    });
  });

  it("exposes only health, attestation, and bounded adapter tests", () => {
    expect(isValidationRuntimeRequest("GET", "/api/health")).toBe(true);
    expect(isValidationRuntimeRequest("GET", "/api/agents/a/configuration-attestation")).toBe(true);
    expect(isValidationRuntimeRequest("POST", "/api/companies/c/adapters/codex_local/test-environment")).toBe(true);
    expect(isValidationRuntimeRequest("PATCH", "/api/agents/a")).toBe(false);
    expect(isValidationRuntimeRequest("POST", "/api/issues/i/checkout")).toBe(false);
    expect(isValidationRuntimeRequest("GET", "/")).toBe(false);
  });

  it("guards the concrete startup mutation and reconciliation call sites", () => {
    const source = readFileSync(new URL("./index.ts", import.meta.url), "utf8");
    for (const call of [
      "workspaceOperationService(db as any)",
      "reconcilePersistedRuntimeServicesOnStartup(db as any)",
      "reconcileCodexLocalManagedHomesOnStartup(db)",
      "reconcileBuiltInAgentsOnStartup(db as any)",
      "bootstrapExecutionPolicyFromEnv(db as any)",
      "applyManagedEnvironments(db as any, managedConfig",
    ]) {
      expect(source).toContain(`if (validationRuntime.runStartupReconciliation)`);
      expect(source.indexOf("if (validationRuntime.runStartupReconciliation", source.lastIndexOf("\n", source.indexOf(call)) - 200)).toBeGreaterThanOrEqual(0);
    }
    expect(source).toContain("validationRuntime.runBackups && config.databaseBackupEnabled");
    expect(source).toContain("validationRuntime.runHeartbeatScheduler && config.heartbeatSchedulerEnabled");
    expect(source).toContain("validationRuntime.applyMigrations");
  });
});
