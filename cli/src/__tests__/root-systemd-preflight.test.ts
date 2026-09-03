import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

const directories: string[] = [];
const preflight = path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-preflight");
afterEach(() => { for (const directory of directories.splice(0)) fs.rmSync(directory, { recursive: true, force: true }); });

function fixture(overrides: Record<string, unknown> = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-root-unit-")); directories.push(root);
  const instance = path.join(root, "instances", "default"), envFile = path.join(root, "paperclip.env"), bin = path.join(root, "bin"), statShim = path.join(bin, "stat");
  const data = path.join(instance, "db"), backups = path.join(instance, "data", "backups"), storage = path.join(instance, "data", "storage"), secrets = path.join(instance, "secrets"), key = path.join(secrets, "master.key"), config = path.join(instance, "config.json"), executable = path.join(root, "paperclipai");
  for (const directory of [root, path.join(root, "instances"), instance, data, backups, storage, secrets]) fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  fs.writeFileSync(key, "key", { mode: 0o600 }); fs.writeFileSync(envFile, "# root-managed in production\n", { mode: 0o600 }); fs.writeFileSync(executable, "#!/bin/sh\nexit 0\n", { mode: 0o700 }); fs.mkdirSync(bin); fs.writeFileSync(statShim, `#!/bin/sh\nif [ "$1" = "-c" ] && [ "$2" = "%U" ] && [ "$3" = "${envFile}" ]; then echo root; else exec /usr/bin/stat "$@"; fi\n`, { mode: 0o700 });
  const document = { server: { host: "127.0.0.1", port: 3100, deploymentMode: "local_trusted", exposure: "private", bind: "loopback" }, database: { mode: "embedded-postgres", embeddedPostgresDataDir: data, backup: { enabled: true, dir: backups } }, storage: { provider: "local_disk", localDisk: { baseDir: storage } }, secrets: { provider: "local_encrypted", localEncrypted: { keyFilePath: key } }, ...overrides };
  fs.writeFileSync(config, JSON.stringify(document), { mode: 0o600 });
  return { root, data, backups, storage, key, config, executable, envFile, bin };
}
function run(input: ReturnType<typeof fixture>, extra: NodeJS.ProcessEnv = {}) { return execFileSync("bash", [preflight], { env: { ...process.env, PATH: `${input.bin}:${process.env.PATH}`, PAPERCLIP_HOME: input.root, PAPERCLIP_CONFIG: input.config, PAPERCLIP_INSTANCE_ID: "default", PAPERCLIP_EXECUTABLE: input.executable, PAPERCLIP_NODE: process.execPath, PAPERCLIP_DATA_DIR: input.data, PAPERCLIP_BACKUP_DIR: input.backups, PAPERCLIP_STORAGE_DIR: input.storage, PAPERCLIP_SECRETS_KEY_FILE: input.key, PAPERCLIP_ENV_FILE: input.envFile, PAPERCLIP_SERVICE_MANAGED: "1", ...extra }, encoding: "utf8" }); }

describe("root systemd preflight", () => {
  it("accepts the explicit private loopback deployment layout", () => { expect(run(fixture())).toBe(""); });
  it.each([["public exposure", { server: { host: "127.0.0.1", port: 3100, deploymentMode: "local_trusted", exposure: "public" } }], ["public binding", { server: { host: "0.0.0.0", port: 3100, deploymentMode: "local_trusted", exposure: "private" } }], ["weakened mode", { server: { host: "127.0.0.1", port: 3100, deploymentMode: "authenticated", exposure: "private" } }]])("rejects %s", (_name, config) => { const input = fixture(config); expect(() => run(input)).toThrow(/loopback-only local_trusted private/); });
  it("rejects missing executable and unsafe secret permissions", () => { const input = fixture(); fs.unlinkSync(input.executable); expect(() => run(input)).toThrow(/not an executable/); const second = fixture(); fs.chmodSync(second.key, 0o644); expect(() => run(second)).toThrow(/secret key must not be readable/); });
  it("requires the unit to execute both fail-closed preflights and the parameterized executable", () => { const unit = fs.readFileSync(path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip.service"), "utf8"); expect(unit).toContain("ExecStartPre=/usr/lib/paperclip/paperclip-preflight"); expect(unit).toContain("ExecStartPre=/usr/lib/paperclip/paperclip-activation-preflight"); expect(unit).toContain("Environment=PAPERCLIP_ENV_FILE=/etc/paperclip/paperclip.env"); expect(unit).toContain('"$PAPERCLIP_EXECUTABLE" run --instance "$PAPERCLIP_INSTANCE_ID"'); expect(unit).not.toContain("/usr/local/bin/paperclipai"); });
});
