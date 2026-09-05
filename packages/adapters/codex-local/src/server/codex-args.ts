import { asBoolean, asString, asStringArray } from "@paperclipai/adapter-utils/server-utils";
import {
  CODEX_LOCAL_FAST_MODE_SUPPORTED_MODELS,
  isCodexLocalFastModeSupported,
  normalizeCodexModel,
} from "../index.js";

const SKIP_GIT_REPO_CHECK_FLAG = "--skip-git-repo-check";

export type BuildCodexExecArgsResult = {
  args: string[];
  model: string;
  fastModeRequested: boolean;
  fastModeApplied: boolean;
  fastModeIgnoredReason: string | null;
};

function readExtraArgs(config: unknown): string[] {
  const fromExtraArgs = asStringArray(asRecord(config).extraArgs);
  if (fromExtraArgs.length > 0) return fromExtraArgs;
  return asStringArray(asRecord(config).args);
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function formatFastModeSupportedModels(): string {
  return `${CODEX_LOCAL_FAST_MODE_SUPPORTED_MODELS.join(", ")} or manually configured model IDs`;
}

function tomlString(value: string): string {
  return JSON.stringify(value);
}

export function buildManagedNetworkProxyConfig(domains: string[]): string {
  const domainEntries = domains
    .map((host) => `${tomlString(host)}="allow"`)
    .join(",");
  return `features.network_proxy={enabled=true,enable_socks5=false,allow_upstream_proxy=true,domains={${domainEntries}}}`;
}

export function buildCodexExecArgs(
  config: unknown,
  options: {
    resumeSessionId?: string | null;
    skipGitRepoCheck?: boolean;
    taskNetworkAllowlist?: string[] | null;
  } = {},
): BuildCodexExecArgsResult {
  const record = asRecord(config);
  const model = normalizeCodexModel(asString(record.model, ""));
  const modelReasoningEffort = asString(
    record.modelReasoningEffort,
    asString(record.reasoningEffort, ""),
  ).trim();
  const search = asBoolean(record.search, false);
  const fastModeRequested = asBoolean(record.fastMode, false);
  const fastModeApplied = fastModeRequested && isCodexLocalFastModeSupported(model);
  const bypass = asBoolean(
    record.dangerouslyBypassApprovalsAndSandbox,
    asBoolean(record.dangerouslyBypassSandbox, false),
  );
  const extraArgs = readExtraArgs(record);
  const confinementOverride = extraArgs.some((arg) =>
    arg === "--dangerously-bypass-approvals-and-sandbox"
    || arg === "--sandbox"
    || arg === "-s"
    || arg.startsWith("--sandbox=")
    || arg === "-c"
    || arg.startsWith("-c")
    || arg === "--config"
    || arg.startsWith("--config=")
    || arg === "--enable"
    || arg.startsWith("--enable=")
    || arg === "--disable"
    || arg.startsWith("--disable="));
  if (options.taskNetworkAllowlist && (bypass || confinementOverride)) {
    throw new Error("Codex sandbox or network-policy overrides cannot be combined with commissioned network confinement.");
  }

  const args = ["exec", "--json"];
  // Codex rejects a repeated `--skip-git-repo-check` ("cannot be used multiple
  // times"). The adapter injects this flag for sandbox execution, so when an
  // operator's extraArgs already carry it the injection would abort the run
  // with exit code 2. Skip the injection in that case and let the operator's
  // copy stand.
  if (options.skipGitRepoCheck && !extraArgs.includes(SKIP_GIT_REPO_CHECK_FLAG)) {
    args.push(SKIP_GIT_REPO_CHECK_FLAG);
  }
  if (search) args.unshift("--search");
  if (bypass) args.push("--dangerously-bypass-approvals-and-sandbox");
  if (model) args.push("--model", model);
  if (modelReasoningEffort) {
    args.push("-c", `model_reasoning_effort=${JSON.stringify(modelReasoningEffort)}`);
  }
  if (fastModeApplied) {
    args.push("-c", 'service_tier="fast"', "-c", "features.fast_mode=true");
  }
  if (options.taskNetworkAllowlist) {
    args.push(
      "--sandbox", "workspace-write",
      "-c", "sandbox_workspace_write.network_access=true",
      "-c", buildManagedNetworkProxyConfig(options.taskNetworkAllowlist),
    );
  }
  if (extraArgs.length > 0) args.push(...extraArgs);
  if (options.resumeSessionId) args.push("resume", options.resumeSessionId, "-");
  else args.push("-");

  return {
    args,
    model,
    fastModeRequested,
    fastModeApplied,
    fastModeIgnoredReason:
      fastModeRequested && !fastModeApplied
        ? `Configured fast mode is currently only supported on ${formatFastModeSupportedModels()}; Paperclip will ignore it for model ${model || "(default)"}.`
        : null,
  };
}
