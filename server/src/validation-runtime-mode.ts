import { isLoopbackHost } from "./url-utils.js";

export const VALIDATION_RUNTIME_MODE = "daf-adapter-validation";

export type ValidationRuntimePolicy = {
  enabled: boolean;
  serveUi: boolean;
  applyMigrations: boolean;
  runBackups: boolean;
  runHeartbeatScheduler: boolean;
  runStartupReconciliation: boolean;
  runBackgroundJobs: boolean;
};

const ordinaryPolicy: ValidationRuntimePolicy = {
  enabled: false, serveUi: true, applyMigrations: true, runBackups: true,
  runHeartbeatScheduler: true, runStartupReconciliation: true, runBackgroundJobs: true,
};

export function resolveValidationRuntimePolicy(input: { mode?: string; nodeEnv?: string; host: string; databaseUrl?: string | null }): ValidationRuntimePolicy {
  if (!input.mode) return ordinaryPolicy;
  if (input.mode !== VALIDATION_RUNTIME_MODE) throw new Error(`Unsupported PAPERCLIP_RUNTIME_MODE: ${input.mode}`);
  if (input.nodeEnv === "production") throw new Error(`${VALIDATION_RUNTIME_MODE} is unavailable in NODE_ENV=production`);
  if (!isLoopbackHost(input.host)) throw new Error(`${VALIDATION_RUNTIME_MODE} requires a loopback bind host`);
  if (!input.databaseUrl) throw new Error(`${VALIDATION_RUNTIME_MODE} requires an existing external DATABASE_URL`);
  return {
    enabled: true, serveUi: false, applyMigrations: false, runBackups: false,
    runHeartbeatScheduler: false, runStartupReconciliation: false, runBackgroundJobs: false,
  };
}

export function isValidationRuntimeRequest(method: string, path: string): boolean {
  if (method === "GET" && /^\/api\/health\/?$/.test(path)) return true;
  if (method === "GET" && /^\/api\/agents\/[^/]+\/configuration-attestation\/?$/.test(path)) return true;
  return method === "POST" && /^\/api\/companies\/[^/]+\/adapters\/[^/]+\/test-environment\/?$/.test(path);
}
