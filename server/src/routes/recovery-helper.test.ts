import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const helper = path.join(repoRoot, "deploy/recovery/paperclip-recovery");

describe("fixed recovery helper", () => {
  it("rejects an argument before it can reach a privileged operation", () => {
    const result = spawnSync("/bin/sh", [helper, "paperclip-other.service"], { encoding: "utf8" });
    expect(result.status).toBe(64);
    expect(result.stderr).toContain("accepts no arguments");
  });

  it("rejects direct invocation by an unprivileged identity", () => {
    const result = spawnSync("/bin/sh", [helper], {
      encoding: "utf8",
      env: { PATH: process.env.PATH ?? "" },
    });
    expect(result.status).toBe(77);
    expect(result.stderr).toContain("paperclip OS identity");
  });
});
