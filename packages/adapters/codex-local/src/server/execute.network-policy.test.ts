import { describe, expect, it } from "vitest";

import { resolveCodexLocalProcessNetworkAllowlist } from "./execute.js";

describe("Codex local commissioned network policy", () => {
  it("uses the exact commissioned FQDN instead of the adapter default", () => {
    expect(resolveCodexLocalProcessNetworkAllowlist(
      { networkAllowlist: ["unrelated.example"] },
      {
        paperclipExecutionPolicy: {
          networkEgress: {
            allowFqdns: ["totalwaterdesign.com"],
            allowCidrs: [],
          },
        },
      },
    )).toEqual(["totalwaterdesign.com"]);
  });

  it("preserves an explicitly commissioned empty FQDN list", () => {
    expect(resolveCodexLocalProcessNetworkAllowlist(
      { networkAllowlist: ["unrelated.example"] },
      { paperclipExecutionPolicy: { networkEgress: { allowFqdns: [] } } },
    )).toEqual([]);
  });

  it("does not inherit an adapter hostname for a CIDR-only commission", () => {
    expect(resolveCodexLocalProcessNetworkAllowlist(
      { networkAllowlist: ["unrelated.example"] },
      { paperclipExecutionPolicy: { networkEgress: { allowCidrs: ["192.0.2.0/24"] } } },
    )).toEqual([]);
  });

  it("falls back to adapter configuration when no issue policy was commissioned", () => {
    expect(resolveCodexLocalProcessNetworkAllowlist(
      { networkAllowlist: ["api.openai.com"] },
      {},
    )).toEqual(["api.openai.com"]);
  });
});
