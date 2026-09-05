import { execFileSync, spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

const directories: string[] = [];
const recovery = path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-health-recovery");
const installer = path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-service-install");
const testUid = process.getuid?.() ?? 0;
const testGid = process.getgid?.() ?? 0;

afterEach(() => {
  for (const directory of directories.splice(0)) fs.rmSync(directory, { recursive: true, force: true });
});

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-health-recovery-"));
  directories.push(root);
  const bin = path.join(root, "bin"), state = path.join(root, "state"), health = path.join(root, "health"), calls = path.join(root, "helper.calls");
  fs.mkdirSync(bin); fs.mkdirSync(state); fs.writeFileSync(health, "unhealthy");
  fs.writeFileSync(path.join(bin, "curl"), `#!/usr/bin/env bash\ncat <<JSON\n{"status":"$(cat "$HEALTH_FILE")"}\nJSON\n`, { mode: 0o755 });
  fs.writeFileSync(path.join(bin, "sudo"), `#!/usr/bin/env bash\nprintf '%s\\n' "$*" >>"$SYSTEMCTL_CALLS"\n[[ "\${SYSTEMCTL_FAIL:-0}" == 1 ]] && exit 1\n[[ -n "\${SYSTEMCTL_RESTART_SLEEP:-}" ]] && sleep "$SYSTEMCTL_RESTART_SLEEP"\nprintf ok >"$HEALTH_FILE"\nexit 0\n`, { mode: 0o755 });
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
      PAPERCLIP_RECOVERY_HELPER: "/usr/local/lib/paperclip/paperclip-recovery",
      ...extra,
    },
  });
}

function runCaptured(input: ReturnType<typeof fixture>, extra: NodeJS.ProcessEnv = {}) {
  return spawnSync("bash", [recovery], {
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
      PAPERCLIP_RECOVERY_HELPER: "/usr/local/lib/paperclip/paperclip-recovery",
      ...extra,
    },
  });
}

function installerFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-service-install-"));
  directories.push(root);
  const target = path.join(root, "target"), backup = path.join(root, "backup"), bin = path.join(root, "bin"), state = path.join(root, "systemctl-state"), calls = path.join(root, "systemctl.calls");
  fs.mkdirSync(bin); fs.mkdirSync(state); fs.mkdirSync(path.join(target, "etc/systemd/system"), { recursive: true }); fs.mkdirSync(path.join(target, "etc/paperclip"), { recursive: true });
  fs.writeFileSync(path.join(target, "etc/systemd/system/paperclip.service"), "prior primary unit\n", { mode: 0o600 });
  fs.writeFileSync(path.join(target, "etc/paperclip/paperclip.env"), "prior environment\n", { mode: 0o600 });
  for (const [unit, enabled, active] of [["paperclip.service", "disabled", "inactive"], ["paperclip-health-recovery.timer", "enabled", "active"]]) {
    fs.writeFileSync(path.join(state, `${unit}.enabled`), enabled); fs.writeFileSync(path.join(state, `${unit}.active`), active);
  }
  fs.writeFileSync(path.join(bin, "systemctl"), `#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >>"$SYSTEMCTL_CALLS"
case "$1" in
  daemon-reload) ;;
  is-enabled) cat "$SYSTEMCTL_STATE/$2.enabled" ;;
  is-active) cat "$SYSTEMCTL_STATE/$2.active" ;;
  enable) printf enabled >"$SYSTEMCTL_STATE/$2.enabled" ;;
  disable) printf disabled >"$SYSTEMCTL_STATE/$2.enabled" ;;
  start) printf active >"$SYSTEMCTL_STATE/$2.active" ;;
  stop) printf inactive >"$SYSTEMCTL_STATE/$2.active" ;;
  *) exit 64 ;;
esac
`, { mode: 0o755 });
  fs.writeFileSync(path.join(bin, "visudo"), "#!/usr/bin/env bash\n[[ \"$1\" == -c && \"$2\" == -f ]]\n", { mode: 0o755 });
  return { root, target, backup, bin, state, calls };
}

function runInstaller(input: ReturnType<typeof installerFixture>, action: "install" | "rollback") {
  return execFileSync("bash", [installer, action], {
    encoding: "utf8",
    env: { ...process.env, PATH: `${input.bin}:${process.env.PATH}`, SYSTEMCTL_CALLS: input.calls, SYSTEMCTL_STATE: input.state, PAPERCLIP_INSTALL_ROOT: input.target, PAPERCLIP_ROLLBACK_ROOT: input.backup, PAPERCLIP_INSTALL_OWNER: testUid.toString(), PAPERCLIP_INSTALL_GROUP: testGid.toString() },
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
    expect(fs.readFileSync(input.calls, "utf8")).toContain("-n -- /usr/local/lib/paperclip/paperclip-recovery");
    expect(fs.readFileSync(path.join(input.state, "consecutive-failures"), "utf8").trim()).toBe("0");
  });

  it("treats a non-ok JSON health response as unhealthy even with curl success", () => {
    const input = fixture(); fs.writeFileSync(input.health, "degraded");
    const output = run(input);
    expect(output).toContain("consecutive_failures=1 threshold=3");
    expect(fs.existsSync(input.calls)).toBe(false);
  });

  it("treats actual curl failure and malformed JSON as unhealthy", () => {
    const curlFailure = fixture();
    fs.writeFileSync(path.join(curlFailure.bin, "curl"), "#!/usr/bin/env bash\necho curl-transport-error >&2\nexit 22\n", { mode: 0o755 });
    const failed = runCaptured(curlFailure);
    expect(failed.status).toBe(0);
    expect(failed.stdout).toContain("consecutive_failures=1 threshold=3");
    expect(failed.stderr).toBe("");

    const malformed = fixture();
    fs.writeFileSync(path.join(malformed.bin, "curl"), "#!/usr/bin/env bash\nprintf '{not-json'\n", { mode: 0o755 });
    const malformedResult = runCaptured(malformed);
    expect(malformedResult.status).toBe(0);
    expect(malformedResult.stdout).toContain("consecutive_failures=1 threshold=3");
    expect(malformedResult.stderr).toBe("");
  });

  it("never emits configured secret sentinels to stdout, stderr, or journal-bound output", () => {
    const input = fixture();
    const sentinels = ["sentinel-api-key-1049", "postgres://sentinel-db-url-1049", "sentinel-secret-value-1049"];
    const result = runCaptured(input, {
      PAPERCLIP_API_KEY: sentinels[0], DATABASE_URL: sentinels[1], PAPERCLIP_SECRET: sentinels[2],
      SYSTEMCTL_FAIL: "1", PAPERCLIP_HEALTH_FAILURE_THRESHOLD: "1",
    });
    expect(result.status).toBe(1);
    const journalBoundOutput = `${result.stdout}${result.stderr}`;
    for (const sentinel of sentinels) expect(journalBoundOutput).not.toContain(sentinel);
    expect(journalBoundOutput).toContain("recovery result=failed: fixed privileged helper failed");
  });

  it("reports a failed recovery and preserves the rate-limit timestamp", () => {
    const input = fixture(); fs.writeFileSync(path.join(input.state, "consecutive-failures"), "2\n");
    let failure: { stdout?: string } | undefined;
    try { run(input, { SYSTEMCTL_FAIL: "1" }); } catch (error) { failure = error as { stdout?: string }; }
    expect(failure?.stdout).toContain("recovery result=failed: fixed privileged helper failed");
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
    expect(fs.readFileSync(input.calls, "utf8").match(/paperclip-recovery/g)).toHaveLength(1);
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

  it("installs and rolls back every managed file and both unit states in an isolated root", () => {
    const input = installerFixture();
    runInstaller(input, "install");
    const unit = path.join(input.target, "etc/systemd/system/paperclip.service");
    const recoveryUnit = path.join(input.target, "etc/systemd/system/paperclip-health-recovery.service");
    const timer = path.join(input.target, "etc/systemd/system/paperclip-health-recovery.timer");
    const env = path.join(input.target, "etc/paperclip/paperclip.env");
    const activationPreflight = path.join(input.target, "usr/lib/paperclip/paperclip-activation-preflight");
    const artifactIdentityVerifier = path.join(input.target, "usr/lib/paperclip/paperclip-artifact-identity.mjs");
    const recoveryScript = path.join(input.target, "usr/lib/paperclip/paperclip-health-recovery");
    const fixedHelper = path.join(input.target, "usr/local/lib/paperclip/paperclip-recovery");
    const sudoers = path.join(input.target, "etc/sudoers.d/paperclip-recovery");
    const tokenProvisioner = path.join(input.target, "usr/lib/paperclip/paperclip-recovery-token-provision");
    for (const file of [unit, recoveryUnit, timer, env, activationPreflight, artifactIdentityVerifier, recoveryScript, fixedHelper, sudoers, tokenProvisioner]) expect(fs.existsSync(file)).toBe(true);
    expect(fs.statSync(unit).mode & 0o777).toBe(0o644);
    expect(fs.statSync(recoveryUnit).mode & 0o777).toBe(0o644);
    expect(fs.statSync(timer).mode & 0o777).toBe(0o644);
    expect(fs.statSync(env).mode & 0o777).toBe(0o640);
    expect(fs.statSync(recoveryScript).mode & 0o777).toBe(0o755);
    expect(fs.statSync(fixedHelper).mode & 0o777).toBe(0o750);
    expect(fs.statSync(sudoers).mode & 0o777).toBe(0o440);
    expect(fs.statSync(tokenProvisioner).mode & 0o777).toBe(0o750);
    expect(fs.statSync(artifactIdentityVerifier).mode & 0o777).toBe(0o644);
    expect(fs.statSync(recoveryScript).uid).toBe(testUid);
    expect(fs.statSync(recoveryScript).gid).toBe(testGid);

    const artifactRoot = path.join(input.root, "artifact");
    const artifactOutput = path.join(artifactRoot, "out");
    fs.mkdirSync(artifactOutput, { recursive: true });
    fs.writeFileSync(path.join(artifactRoot, "pnpm-lock.yaml"), "lockfileVersion: '9.0'\n");
    fs.writeFileSync(path.join(artifactRoot, ".gitignore"), "out/\n");
    fs.writeFileSync(path.join(artifactRoot, "source"), "source\n");
    execFileSync("git", ["init", "-q", artifactRoot]);
    execFileSync("git", ["-C", artifactRoot, "config", "user.email", "test@example.invalid"]);
    execFileSync("git", ["-C", artifactRoot, "config", "user.name", "Test"]);
    execFileSync("git", ["-C", artifactRoot, "add", "."]);
    execFileSync("git", ["-C", artifactRoot, "commit", "-qm", "fixture"]);
    const sourceSha = execFileSync("git", ["-C", artifactRoot, "rev-parse", "HEAD"], { encoding: "utf8" }).trim();
    const executable = path.join(artifactOutput, "index.js");
    const identity = path.join(artifactOutput, "paperclip-artifact-identity.json");
    const archive = path.join(input.root, "paperclip.tgz");
    const manifest = path.join(artifactRoot, "certification.json");
    fs.writeFileSync(executable, "installed executable\n");
    fs.writeFileSync(archive, "installed archive\n");
    execFileSync(process.execPath, [artifactIdentityVerifier, "identity", "--repo", artifactRoot, "--output-dir", artifactOutput, "--source-sha", sourceSha, "--build-command", "pnpm certified"]);
    execFileSync(process.execPath, [artifactIdentityVerifier, "certify", "--identity", identity, "--archive", archive, "--executable", executable, "--manifest", manifest]);
    expect(execFileSync(activationPreflight, {
      encoding: "utf8",
      env: { ...process.env, PAPERCLIP_NODE: process.execPath, PAPERCLIP_ARTIFACT_MANIFEST: manifest, PAPERCLIP_ARTIFACT_IDENTITY: identity, PAPERCLIP_ARTIFACT_ARCHIVE: archive, PAPERCLIP_EXECUTABLE: executable },
    })).toContain("artifact identity: activation preflight passed");

    runInstaller(input, "rollback");
    expect(fs.readFileSync(unit, "utf8")).toBe("prior primary unit\n");
    expect(fs.statSync(unit).mode & 0o777).toBe(0o600);
    expect(fs.readFileSync(env, "utf8")).toBe("prior environment\n");
    expect(fs.statSync(env).mode & 0o777).toBe(0o600);
    for (const file of [recoveryUnit, timer, activationPreflight, artifactIdentityVerifier, recoveryScript, fixedHelper, sudoers, tokenProvisioner]) expect(fs.existsSync(file)).toBe(false);
    expect(fs.readFileSync(path.join(input.state, "paperclip.service.enabled"), "utf8")).toBe("disabled");
    expect(fs.readFileSync(path.join(input.state, "paperclip.service.active"), "utf8")).toBe("inactive");
    expect(fs.readFileSync(path.join(input.state, "paperclip-health-recovery.timer.enabled"), "utf8")).toBe("enabled");
    expect(fs.readFileSync(path.join(input.state, "paperclip-health-recovery.timer.active"), "utf8")).toBe("active");
    expect(fs.readFileSync(input.calls, "utf8")).toContain("daemon-reload");
  });

  it("runs the recovery component as the Paperclip service identity", () => {
    const unit = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-health-recovery.service"), "utf8");
    expect(unit).toContain("User=paperclip");
    expect(unit).toContain("Group=paperclip");
    expect(unit).not.toContain("User=root");
  });

  it("binds the health path only to the exact no-argument helper through narrow sudoers", () => {
    const script = fs.readFileSync(recovery, "utf8");
    const sudoers = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/recovery/paperclip-recovery.sudoers"), "utf8");
    expect(script).toContain('sudo -n -- "$recovery_helper"');
    expect(script).not.toMatch(/systemctl\s+(restart|start|stop|kill)/);
    expect(sudoers.trim().split("\n").at(-1)).toBe('paperclip ALL=(root) NOPASSWD: /usr/local/lib/paperclip/paperclip-recovery ""');
    expect(sudoers).not.toContain("ALL=(ALL)");
  });

  it("ships fail-closed non-secret token provisioning and validation", () => {
    const provisioner = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-recovery-token-provision"), "utf8");
    const installer = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-service-install"), "utf8");
    expect(provisioner).toContain('[[ ! -t 0 ]]');
    expect(provisioner).toContain("token must be a non-whitespace value of at least 32 characters");
    expect(provisioner).toContain('chmod 0640 "$token_tmp" "$env_tmp"');
    expect(provisioner).not.toContain("set -x");
    expect(installer).toContain('visudo -c -f "$root/etc/sudoers.d/paperclip-recovery"');
    expect(installer).toContain("unsafe recovery helper mode");
    expect(installer).toContain("unsafe sudoers mode");
  });
});
