import { describe, expect, it } from "vitest";

import { resolveCodexLocalProcessNetworkAllowlist } from "./execute.js";

describe("Codex local commissioned network policy", () => {
  it("uses only the exact commissioned FQDN for task tools", () => {
    expect(resolveCodexLocalProcessNetworkAllowlist(
      { networkAllowlist: ["unrelated.example"] },
      { paperclipExecutionPolicy: { networkEgress: {
        allowFqdns: ["totalwaterdesign.com"], allowCidrs: [],
      } } },
    )).toEqual(["totalwaterdesign.com"]);
  });

  it("preserves an explicitly commissioned empty FQDN list", () => {
    expect(resolveCodexLocalProcessNetworkAllowlist(
      { networkAllowlist: ["unrelated.example"] },
      { paperclipExecutionPolicy: { networkEgress: { allowFqdns: [] } } },
    )).toEqual([]);
  });

  it("falls back to adapter configuration without a commissioned policy", () => {
    expect(resolveCodexLocalProcessNetworkAllowlist(
      { networkAllowlist: ["legacy.example"] }, {},
    )).toEqual(["legacy.example"]);
  });
});
