import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

const directories: string[] = [];
const preflight = path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-preflight");
afterEach(() => { for (const directory of directories.splice(0)) fs.rmSync(directory, { recursive: true, force: true }); });

function fixture(overrides: Record<string, unknown> = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-root-unit-")); directories.push(root);
  const home = path.join(root, "home"), state = path.join(home, ".paperclip"), instance = path.join(state, "instances", "default"), envFile = path.join(root, "paperclip.env"), bin = path.join(root, "bin"), statShim = path.join(bin, "stat");
  const data = path.join(instance, "db"), backups = path.join(instance, "data", "backups"), storage = path.join(instance, "data", "storage"), secrets = path.join(instance, "secrets"), key = path.join(secrets, "master.key"), config = path.join(instance, "config.json"), executable = path.join(home, ".local", "bin", "paperclipai"), workspaces = path.join(home, "workspaces");
  for (const directory of [root, home, state, path.join(state, "instances"), instance, data, backups, storage, secrets, path.dirname(executable), workspaces]) fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  fs.writeFileSync(key, "key", { mode: 0o600 }); fs.writeFileSync(envFile, "# root-managed in production\n", { mode: 0o600 }); fs.writeFileSync(executable, "#!/bin/sh\nexit 0\n", { mode: 0o700 }); fs.mkdirSync(bin); fs.writeFileSync(statShim, `#!/bin/sh\nif [ "$1" = "-c" ] && [ "$2" = "%U" ] && [ "$3" = "${envFile}" ]; then echo root; else exec /usr/bin/stat "$@"; fi\n`, { mode: 0o700 });
  const document = { server: { host: "127.0.0.1", port: 3100, deploymentMode: "local_trusted", exposure: "private", bind: "loopback" }, database: { mode: "embedded-postgres", embeddedPostgresDataDir: data, embeddedPostgresPort: 54329, backup: { enabled: true, dir: backups } }, storage: { provider: "local_disk", localDisk: { baseDir: storage } }, secrets: { provider: "local_encrypted", localEncrypted: { keyFilePath: key } }, ...overrides };
  fs.writeFileSync(config, JSON.stringify(document), { mode: 0o600 });
  return { root, home, state, data, backups, storage, key, config, executable, envFile, bin, workspaces };
}
function run(input: ReturnType<typeof fixture>, extra: NodeJS.ProcessEnv = {}) { return execFileSync("bash", [preflight], { env: { ...process.env, PATH: `${input.bin}:${process.env.PATH}`, PAPERCLIP_SYSTEM_HOME: input.home, PAPERCLIP_HOME: input.state, PAPERCLIP_CONFIG: input.config, PAPERCLIP_INSTANCE_ID: "default", PAPERCLIP_EXECUTABLE: input.executable, PAPERCLIP_NODE: "/usr/bin/node", PAPERCLIP_DATA_DIR: input.data, PAPERCLIP_BACKUP_DIR: input.backups, PAPERCLIP_STORAGE_DIR: input.storage, PAPERCLIP_SECRETS_KEY_FILE: input.key, PAPERCLIP_ENV_FILE: input.envFile, PAPERCLIP_WORKSPACES_DIR: input.workspaces, PAPERCLIP_SERVICE_MANAGED: "1", PAPERCLIP_RECOVERY_TOKEN: "fixture-recovery-token-0123456789abcdef", ...extra }, encoding: "utf8" }); }

describe("root systemd preflight", () => {
  it("accepts an isolated production-layout fixture with embedded PostgreSQL on port 54329", () => { expect(run(fixture())).toBe(""); });
  it("rejects embedded PostgreSQL on any other port", () => {
    const input = fixture();
    const config = JSON.parse(fs.readFileSync(input.config, "utf8"));
    config.database.embeddedPostgresPort = 54330;
    fs.writeFileSync(input.config, JSON.stringify(config), { mode: 0o600 });
    expect(() => run(input)).toThrow(/127\.0\.0\.1:54329/);
  });
  it.each([["public exposure", { server: { host: "127.0.0.1", port: 3100, deploymentMode: "local_trusted", exposure: "public" } }], ["public binding", { server: { host: "0.0.0.0", port: 3100, deploymentMode: "local_trusted", exposure: "private" } }], ["weakened mode", { server: { host: "127.0.0.1", port: 3100, deploymentMode: "authenticated", exposure: "private" } }]])("rejects %s", (_name, config) => { const input = fixture(config); expect(() => run(input)).toThrow(/loopback-only local_trusted private/); });
  it("rejects missing executable and unsafe secret permissions", () => { const input = fixture(); fs.unlinkSync(input.executable); expect(() => run(input)).toThrow(/not an executable/); const second = fixture(); fs.chmodSync(second.key, 0o644); expect(() => run(second)).toThrow(/secret key must not be readable/); });
  it("requires the unit to execute the fail-closed fixed production layout", () => { const unit = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip.service"), "utf8"); expect(unit).toContain("ExecStartPre=/usr/lib/paperclip/paperclip-preflight"); expect(unit).toContain("Environment=PAPERCLIP_SYSTEM_HOME=/home/paperclip"); expect(unit).toContain("WorkingDirectory=/home/paperclip"); expect(unit).toContain("exec /home/paperclip/.local/bin/paperclipai run"); expect(unit).toContain("User=paperclip"); expect(unit).toContain("NoNewPrivileges=true"); expect(unit).toContain("ProtectSystem=strict"); expect(unit).toContain("/home/paperclip/workspaces"); expect(unit).not.toContain("/usr/local/bin/paperclipai"); });
  it("fails closed when the dedicated recovery token is missing or weak", () => { const input = fixture(); expect(() => run(input, { PAPERCLIP_RECOVERY_TOKEN: "" })).toThrow(/missing PAPERCLIP_RECOVERY_TOKEN/); expect(() => run(input, { PAPERCLIP_RECOVERY_TOKEN: "short" })).toThrow(/at least 32 characters/); });
  it("runs the executable shell shim through its Node-backed CLI with the service arguments", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-root-exec-")); directories.push(root);
    const shim = path.join(root, "paperclipai"), cli = path.join(root, "managed-cli.js"), argumentLog = path.join(root, "arguments.json");
    fs.writeFileSync(cli, "require('node:fs').writeFileSync(process.env.PAPERCLIP_ARGUMENT_LOG, JSON.stringify(process.argv.slice(2)))");
    fs.writeFileSync(shim, `#!/bin/sh\nexec /usr/bin/node "$PAPERCLIP_MANAGED_CLI" "$@"\n`, { mode: 0o755 });
    const unit = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip.service"), "utf8");
    const execStart = unit.match(/^ExecStart=(.+)$/m)?.[1];
    expect(execStart).toBeDefined();
    const fixtureExecStart = execStart!.replace("/home/paperclip/.local/bin/paperclipai", shim);
    expect(fixtureExecStart).not.toBe(execStart);
    const result = spawnSync("/bin/sh", ["-c", fixtureExecStart], { encoding: "utf8", env: { ...process.env, PAPERCLIP_INSTANCE_ID: "shim-fixture", PAPERCLIP_MANAGED_CLI: cli, PAPERCLIP_ARGUMENT_LOG: argumentLog } });
    expect(result.status).toBe(0);
    expect(result.stderr).toBe("");
    expect(JSON.parse(fs.readFileSync(argumentLog, "utf8"))).toEqual(["run", "--instance", "shim-fixture"]);
  });
  it("ships an exact production /home/paperclip environment contract", () => {
    const env = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip.env"), "utf8");
    expect(env).toContain("PAPERCLIP_HOME=/home/paperclip/.paperclip");
    expect(env).toContain("PAPERCLIP_CONFIG=/home/paperclip/.paperclip/instances/default/config.json");
    expect(env).toContain("PAPERCLIP_EXECUTABLE=/home/paperclip/.local/bin/paperclipai");
    expect(env).toContain("PAPERCLIP_WORKSPACES_DIR=/home/paperclip/workspaces");
    expect(env).not.toContain("/tmp/");
  });
  it("keeps destructive recovery explicitly gated and uses canonical authenticated reconciliation", () => {
    const transition = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-service-transition"), "utf8");
    expect(transition).toContain('PAPERCLIP_ALLOW_SIGKILL_TEST:-}" == "APPROVED"');
    expect(transition).toContain("/api/recovery/reconcile");
    expect(transition).toContain("x-paperclip-recovery-token");
    expect(transition).not.toContain("PAPERCLIP_API_KEY");
    expect(transition).not.toContain("/heartbeat-runs");
    expect(transition).toContain("kill -TERM \"$manual_pid\"");
  });
  it("records absent files and restores prior enabled and active state", () => {
    const installer = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-service-install"), "utf8");
    expect(installer).toContain("printf 'absent\\t%s\\n'");
    expect(installer).toContain('mv "$target" "$backup/replaced/$rel"');
    expect(installer).toContain('grep -qx enabled "$backup/prior.enabled"');
    expect(installer).toContain('grep -qx active "$backup/prior.active"');
  });
});
