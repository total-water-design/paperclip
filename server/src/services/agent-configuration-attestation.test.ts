import { describe, expect, it } from "vitest";
import { buildAgentConfigurationAttestation } from "./agent-configuration-attestation.js";

const agent = {
  id: "11111111-1111-4111-8111-111111111111",
  companyId: "22222222-2222-4222-8222-222222222222",
  adapterType: "codex_local",
  adapterConfig: {
    engine: "cli",
    filesystemScope: "workspace",
    filesystemSandboxCommand: "twds-bwrap",
    networkScope: "allowlist",
    networkAllowlist: ["api.openai.com", "github.com", "api.github.com", "objects.githubusercontent.com"],
    env: { OPENAI_API_KEY: "must-not-leak" },
    unrelated: "must-not-leak",
  },
  runtimeConfig: { heartbeat: { enabled: false, interval: 123 }, unrelated: "must-not-leak" },
  status: "paused",
  pauseReason: "manual",
  pausedAt: new Date("2026-09-04T12:00:00.000Z"),
  updatedAt: new Date("2026-09-04T12:01:00.000Z"),
};

const serverGit = {
  available: true as const,
  fullSha: "3b3f27d9a2099b0e40bd0cb8ebf67d4fe685e558",
  shortSha: "3b3f27d",
  branchName: "task/candidate",
  subject: "candidate",
  committedAt: "2026-09-04T00:00:00.000Z",
  localChanges: { available: true as const, hasLocalChanges: false, stagedFileCount: 0, unstagedFileCount: 0, untrackedFileCount: 0 },
};

describe("agent configuration attestation", () => {
  it("returns only the frozen attestation allowlist with stable persisted provenance", () => {
    const result = buildAgentConfigurationAttestation({
      agent,
      latestRevision: { id: "33333333-3333-4333-8333-333333333333", createdAt: new Date("2026-09-04T12:00:30.000Z") },
      serverGit,
    });

    expect(result).toMatchObject({
      schemaVersion: "agent-configuration-attestation/v1",
      agentId: agent.id,
      companyId: agent.companyId,
      configurationRevisionId: "33333333-3333-4333-8333-333333333333",
      configuration: {
        adapterType: "codex_local",
        engine: "cli",
        filesystemScope: "workspace",
        filesystemSandboxCommand: "twds-bwrap",
        networkScope: "allowlist",
        networkAllowlist: ["api.openai.com", "github.com", "api.github.com", "objects.githubusercontent.com"],
        heartbeat: { enabled: false },
      },
      state: { status: "paused", pauseReason: "manual", pausedAt: "2026-09-04T12:00:00.000Z" },
      provenance: { source: "persisted_agent_record", candidateSha: serverGit.fullSha },
    });
    expect(result.configurationDigest).toMatch(/^sha256:[0-9a-f]{64}$/);
    expect(JSON.stringify(result)).not.toContain("must-not-leak");
  });

  it("changes the digest when an attested persisted value changes", () => {
    const first = buildAgentConfigurationAttestation({ agent, latestRevision: null, serverGit });
    const second = buildAgentConfigurationAttestation({
      agent: { ...agent, runtimeConfig: { heartbeat: { enabled: true } } },
      latestRevision: null,
      serverGit,
    });
    expect(second.configurationDigest).not.toBe(first.configurationDigest);
  });
});
