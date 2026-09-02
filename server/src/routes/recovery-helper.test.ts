import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const helper = path.join(repoRoot, "deploy/recovery/paperclip-recovery");
const transition = path.join(repoRoot, "deploy/systemd/paperclip-service-transition");
const directories: string[] = [];
const token = "argv-secret-recovery-token-0123456789abcdef";

afterEach(() => {
  for (const directory of directories.splice(0)) fs.rmSync(directory, { recursive: true, force: true });
});

function argvCaptureFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-recovery-argv-"));
  directories.push(root);
  const bin = path.join(root, "bin");
  const tokenFile = path.join(root, "recovery.token");
  const calls = path.join(root, "curl.calls");
  const headers = path.join(root, "curl.headers");
  fs.mkdirSync(bin);
  fs.writeFileSync(tokenFile, `${token}\n`, { mode: 0o640 });
  fs.writeFileSync(path.join(bin, "curl"), `#!/usr/bin/env bash
set -euo pipefail
printf '%s\\0' "$@" >>"$CURL_CALLS"
printf '\\0' >>"$CURL_CALLS"
for argument in "$@"; do
  if [[ "$argument" == @* ]]; then
    header_file="\${argument#@}"
    printf '%s\\t%s\\n' "$(stat -c '%a' "$header_file")" "$(cat "$header_file")" >>"$CURL_HEADERS"
  fi
done
if [[ " $* " == *" /api/health "* ]]; then
  printf '{"status":"ok"}\\n'
else
  printf '{"reconciled":true}\\n'
fi
`, { mode: 0o755 });
  fs.writeFileSync(path.join(bin, "jq"), "#!/usr/bin/env bash\ncat\n", { mode: 0o755 });
  fs.writeFileSync(path.join(bin, "id"), "#!/bin/sh\nprintf '0\\n'\n", { mode: 0o755 });
  fs.writeFileSync(path.join(bin, "systemctl"), "#!/bin/sh\nexit 0\n", { mode: 0o755 });
  return { root, bin, tokenFile, calls, headers };
}

function capturedArgv(calls: string) {
  return fs.readFileSync(calls).toString("utf8").split("\0").filter(Boolean);
}

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

  it("keeps the recovery token out of curl argv while supplying a protected header file", () => {
    const input = argvCaptureFixture();
    const stagedHelper = path.join(input.root, "paperclip-recovery");
    const source = fs.readFileSync(helper, "utf8")
      .replaceAll("/usr/bin/id", path.join(input.bin, "id"))
      .replaceAll("/bin/systemctl", path.join(input.bin, "systemctl"))
      .replaceAll("/usr/bin/curl", path.join(input.bin, "curl"))
      .replaceAll("/etc/paperclip/recovery.token", input.tokenFile)
      .replaceAll("/run/paperclip-recovery-header.XXXXXX", path.join(input.root, "header.XXXXXX"));
    fs.writeFileSync(stagedHelper, source, { mode: 0o755 });

    const result = spawnSync("/bin/sh", [stagedHelper], {
      encoding: "utf8",
      env: { ...process.env, SUDO_USER: "paperclip", CURL_CALLS: input.calls, CURL_HEADERS: input.headers },
    });

    expect(result.status).toBe(0);
    expect(`${result.stdout}${result.stderr}`).not.toContain(token);
    expect(capturedArgv(input.calls)).not.toContain(token);
    expect(fs.readFileSync(input.calls, "utf8")).not.toContain(token);
    expect(fs.readFileSync(input.headers, "utf8")).toBe(`600\tx-paperclip-recovery-token: ${token}\n`);
    expect(fs.readdirSync(input.root)).not.toContainEqual(expect.stringMatching(/^header\./));
  });

  it("keeps the transition token out of curl argv while supplying a protected header file", () => {
    const input = argvCaptureFixture();
    const stagedTransition = path.join(input.root, "paperclip-service-transition");
    fs.writeFileSync(
      stagedTransition,
      fs.readFileSync(transition, "utf8").replaceAll("/etc/paperclip/recovery.token", input.tokenFile),
      { mode: 0o755 },
    );
    const evidence = path.join(input.root, "evidence");

    const result = spawnSync("bash", [stagedTransition, "reconcile"], {
      encoding: "utf8",
      env: {
        ...process.env,
        PATH: `${input.bin}:${process.env.PATH}`,
        TMPDIR: input.root,
        PAPERCLIP_TRANSITION_EVIDENCE_DIR: evidence,
        PAPERCLIP_RECOVERY_TOKEN_FILE: input.tokenFile,
        CURL_CALLS: input.calls,
        CURL_HEADERS: input.headers,
      },
    });

    expect(result.status).toBe(0);
    expect(`${result.stdout}${result.stderr}`).not.toContain(token);
    expect(capturedArgv(input.calls)).not.toContain(token);
    expect(fs.readFileSync(input.calls, "utf8")).not.toContain(token);
    expect(fs.readFileSync(input.headers, "utf8")).toBe(`600\tx-paperclip-recovery-token: ${token}\n`);
    expect(fs.readdirSync(input.root)).not.toContainEqual(expect.stringMatching(/^paperclip-recovery-header\./));
  });
});
