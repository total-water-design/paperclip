import { createHash } from "node:crypto";
import type { AgentConfigurationAttestation, ServerGitInfo } from "@paperclipai/shared";

type AttestableAgent = {
  id: string;
  companyId: string;
  adapterType: string;
  adapterConfig: Record<string, unknown> | null;
  runtimeConfig: Record<string, unknown> | null;
  status: string;
  pauseReason: string | null;
  pausedAt: Date | null;
  updatedAt: Date;
};

type ConfigurationRevision = {
  id: string;
  createdAt: Date;
} | null;

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function stringsOnly(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function buildAgentConfigurationAttestation(input: {
  agent: AttestableAgent;
  latestRevision: ConfigurationRevision;
  serverGit: ServerGitInfo;
}): AgentConfigurationAttestation {
  const adapterConfig = asRecord(input.agent.adapterConfig);
  const heartbeat = asRecord(asRecord(input.agent.runtimeConfig).heartbeat);
  const persistedConfiguration = {
    adapterType: input.agent.adapterType,
    engine: typeof adapterConfig.engine === "string" ? adapterConfig.engine : null,
    filesystemScope: typeof adapterConfig.filesystemScope === "string" ? adapterConfig.filesystemScope : null,
    filesystemSandboxCommand: typeof adapterConfig.filesystemSandboxCommand === "string"
      ? adapterConfig.filesystemSandboxCommand
      : null,
    networkScope: typeof adapterConfig.networkScope === "string" ? adapterConfig.networkScope : null,
    networkAllowlist: stringsOnly(adapterConfig.networkAllowlist),
    heartbeat: {
      enabled: typeof heartbeat.enabled === "boolean" ? heartbeat.enabled : null,
    },
  };
  const persistedRecord = {
    agentId: input.agent.id,
    companyId: input.agent.companyId,
    agentUpdatedAt: input.agent.updatedAt.toISOString(),
    configurationRevisionId: input.latestRevision?.id ?? null,
    configurationRevisionCreatedAt: input.latestRevision?.createdAt.toISOString() ?? null,
    configuration: persistedConfiguration,
    state: {
      status: input.agent.status,
      pauseReason: input.agent.pauseReason,
      pausedAt: input.agent.pausedAt?.toISOString() ?? null,
    },
  };

  return {
    schemaVersion: "agent-configuration-attestation/v1",
    agentId: input.agent.id,
    companyId: input.agent.companyId,
    configurationRevisionId: input.latestRevision?.id ?? null,
    configurationDigest: `sha256:${createHash("sha256").update(canonicalJson(persistedRecord)).digest("hex")}`,
    configuration: persistedConfiguration,
    state: persistedRecord.state,
    provenance: {
      source: "persisted_agent_record",
      agentUpdatedAt: persistedRecord.agentUpdatedAt,
      configurationRevisionCreatedAt: persistedRecord.configurationRevisionCreatedAt,
      candidateSha: input.serverGit.available ? input.serverGit.fullSha : null,
      candidateSourceAvailable: input.serverGit.available,
    },
  };
}
