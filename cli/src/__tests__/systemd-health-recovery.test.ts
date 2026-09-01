import { execFileSync, spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

const directories: string[] = [];
const recovery = path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-health-recovery");

afterEach(() => {
  for (const directory of directories.splice(0)) fs.rmSync(directory, { recursive: true, force: true });
});

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-health-recovery-"));
  directories.push(root);
  const bin = path.join(root, "bin"), state = path.join(root, "state"), health = path.join(root, "health"), calls = path.join(root, "systemctl.calls");
  fs.mkdirSync(bin); fs.mkdirSync(state); fs.writeFileSync(health, "unhealthy");
  fs.writeFileSync(path.join(bin, "curl"), `#!/usr/bin/env bash\ncat <<JSON\n{"status":"$(cat "$HEALTH_FILE")"}\nJSON\n`, { mode: 0o755 });
  fs.writeFileSync(path.join(bin, "systemctl"), `#!/usr/bin/env bash\nprintf '%s\\n' "$*" >>"$SYSTEMCTL_CALLS"\nif [[ "$1" == restart ]]; then\n  [[ "\${SYSTEMCTL_FAIL:-0}" == 1 ]] && exit 1\n  [[ -n "\${SYSTEMCTL_RESTART_SLEEP:-}" ]] && sleep "$SYSTEMCTL_RESTART_SLEEP"\n  printf ok >"$HEALTH_FILE"\nfi\nexit 0\n`, { mode: 0o755 });
  for (const command of ["initdb", "dropdb", "rm"]) fs.writeFileSync(path.join(bin, command), `#!/usr/bin/env bash\nprintf '%s\\n' "$0 $*" >>"$FORBIDDEN_CALLS"\nexit 97\n`, { mode: 0o755 });
  return { root, bin, state, health, calls, forbidden: path.join(root, "forbidden.calls") };
}

function run(input: ReturnType<typeof fixture>, extra: NodeJS.ProcessEnv = {}) {
  return execFileSync("bash", [recovery], {
    encoding: "utf8",
    env: {
      ...process.env,
      PATH: `${input.bin}:${process.env.PATH}`,
      HEALTH_FILE: input.health,
      SYSTEMCTL_CALLS: input.calls,
      FORBIDDEN_CALLS: input.forbidden,
      PAPERCLIP_RECOVERY_STATE_DIR: input.state,
      PAPERCLIP_HEALTH_FAILURE_THRESHOLD: "3",
      PAPERCLIP_HEALTH_TIMEOUT_SECONDS: "1",
      PAPERCLIP_RECOVERY_READINESS_TIMEOUT_SECONDS: "2",
      PAPERCLIP_RECOVERY_COOLDOWN_SECONDS: "60",
      ...extra,
    },
  });
}

describe("systemd database-unhealthy health recovery", () => {
  it("recovers only after the documented threshold and confirms full-service readiness", () => {
    const input = fixture();
    expect(run(input)).toContain("consecutive_failures=1 threshold=3");
    expect(run(input)).toContain("consecutive_failures=2 threshold=3");
    expect(fs.existsSync(input.calls)).toBe(false);
    const output = run(input);
    expect(output).toContain("recovery threshold reached");
    expect(output).toContain("embedded PostgreSQL and Paperclip ready; health status=ok");
    expect(output).toContain("recovery result=success");
    expect(fs.readFileSync(input.calls, "utf8")).toContain("restart paperclip.service");
    expect(fs.readFileSync(path.join(input.state, "consecutive-failures"), "utf8").trim()).toBe("0");
  });

  it("treats a non-ok JSON health response as unhealthy even with curl success", () => {
    const input = fixture(); fs.writeFileSync(input.health, "degraded");
    const output = run(input);
    expect(output).toContain("consecutive_failures=1 threshold=3");
    expect(fs.existsSync(input.calls)).toBe(false);
  });

  it("reports a failed recovery and preserves the rate-limit timestamp", () => {
    const input = fixture(); fs.writeFileSync(path.join(input.state, "consecutive-failures"), "2\n");
    let failure: { stdout?: string } | undefined;
    try { run(input, { SYSTEMCTL_FAIL: "1" }); } catch (error) { failure = error as { stdout?: string }; }
    expect(failure?.stdout).toContain("recovery result=failed: systemctl restart paperclip.service failed");
    expect(fs.existsSync(path.join(input.state, "last-recovery-epoch"))).toBe(true);
  });

  it("excludes concurrent invocations with a non-blocking lock", async () => {
    const input = fixture(); fs.writeFileSync(path.join(input.state, "consecutive-failures"), "2\n");
    const env = { ...process.env, PATH: `${input.bin}:${process.env.PATH}`, HEALTH_FILE: input.health, SYSTEMCTL_CALLS: input.calls, FORBIDDEN_CALLS: input.forbidden, PAPERCLIP_RECOVERY_STATE_DIR: input.state, PAPERCLIP_HEALTH_FAILURE_THRESHOLD: "3", PAPERCLIP_HEALTH_TIMEOUT_SECONDS: "1", PAPERCLIP_RECOVERY_READINESS_TIMEOUT_SECONDS: "3", PAPERCLIP_RECOVERY_COOLDOWN_SECONDS: "60", SYSTEMCTL_RESTART_SLEEP: "1" };
    const first = spawn("bash", [recovery], { env });
    await new Promise((resolve) => setTimeout(resolve, 100));
    const second = run(input, { SYSTEMCTL_RESTART_SLEEP: "1" });
    expect(second).toContain("recovery suppressed: another invocation is active");
    await new Promise<void>((resolve, reject) => first.on("exit", (code) => code === 0 ? resolve() : reject(new Error(`first exit ${code}`))));
    expect(fs.readFileSync(input.calls, "utf8").match(/restart paperclip\.service/g)).toHaveLength(1);
  });

  it("suppresses a thresholded retry during the documented cooldown", () => {
    const input = fixture(); fs.writeFileSync(path.join(input.state, "consecutive-failures"), "2\n");
    fs.writeFileSync(path.join(input.state, "last-recovery-epoch"), `${Math.floor(Date.now() / 1000)}\n`);
    expect(run(input)).toContain("recovery suppressed: threshold reached but cooldown_seconds=60 remains");
    expect(fs.existsSync(input.calls)).toBe(false);
  });

  it("does not invoke initialization or data-deletion commands", () => {
    const input = fixture(); fs.writeFileSync(path.join(input.state, "consecutive-failures"), "2\n");
    run(input);
    expect(fs.existsSync(input.forbidden)).toBe(false);
  });

  it("ships a persistent one-minute timer and rollback coverage for all new files", () => {
    const timer = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-health-recovery.timer"), "utf8");
    const installer = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-service-install"), "utf8");
    expect(timer).toContain("OnUnitActiveSec=1min"); expect(timer).toContain("Persistent=true");
    expect(installer).toContain("paperclip-health-recovery.service"); expect(installer).toContain("paperclip-health-recovery.timer");
    expect(installer).toContain("prior.health-recovery-timer.enabled"); expect(installer).toContain("prior.health-recovery-timer.active");
  });
});
