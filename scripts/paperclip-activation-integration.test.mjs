import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { chmodSync, copyFileSync, existsSync, mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { createCertification } from "./paperclip-artifact-identity.mjs";

const sourceRoot = path.resolve(import.meta.dirname, "..");
const waitFor = async (predicate) => {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error("timed out waiting for runtime record");
};
function installedFixture(root, label, sourceSha, executableBody) {
  const release = path.join(root, label); mkdirSync(release, { recursive: true });
  const executable = path.join(release, "paperclipai");
  writeFileSync(executable, executableBody); chmodSync(executable, 0o755);
  const identity = path.join(release, "paperclip-artifact-identity.json");
  writeFileSync(identity, `${JSON.stringify({
    format: "paperclip-artifact-certification/v1", source: { sha: sourceSha, clean: true },
    toolchain: { node: process.version, pnpm: "9.15.4" }, lockfile: { path: "pnpm-lock.yaml", sha256: "0".repeat(64) },
    build: { command: "fixture" }, generatedOutput: { sha256: "1".repeat(64), entries: [] },
  })}\n`);
  const archive = path.join(release, "paperclipai.tgz"); writeFileSync(archive, `archive-${label}\n`);
  const manifest = path.join(release, "paperclipai.certification.json");
  createCertification({ identityPath: identity, archivePath: archive, executablePath: executable, outputPath: manifest });
  return { executable, identity, archive, manifest };
}

test("documented staged verifier layout and real runtime lifecycle fail closed", async () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "paperclip-staged-"));
  const lib = path.join(root, "usr/lib/paperclip"); mkdirSync(lib, { recursive: true });
  for (const [source, target] of [
    ["deploy/systemd/paperclip-preflight", "paperclip-preflight"],
    ["scripts/paperclip-activation-preflight.sh", "paperclip-activation-preflight"],
    ["scripts/paperclip-artifact-identity.mjs", "paperclip-artifact-identity.mjs"],
    ["scripts/paperclip-runtime-wrapper.mjs", "paperclip-runtime-wrapper"],
  ]) { copyFileSync(path.join(sourceRoot, source), path.join(lib, target)); chmodSync(path.join(lib, target), 0o755); }

  const fakeBody = "#!/usr/bin/env bash\ntrap 'exit 0' TERM INT HUP\nwhile :; do sleep 0.1; done\n";
  const oldRelease = installedFixture(root, "old", "a".repeat(40), fakeBody);
  const newRelease = installedFixture(root, "new", "b".repeat(40), `${fakeBody}# changed\n`);
  const runtimeDir = path.join(root, "run/paperclip"); mkdirSync(runtimeDir, { recursive: true });
  const pidFile = path.join(runtimeDir, "paperclip.pid");
  const runtimeIdentity = path.join(runtimeDir, "paperclip-runtime-identity.json");
  const home = path.join(root, "var/lib/paperclip");
  const instance = path.join(home, "instances/default");
  const data = path.join(instance, "db"); const backup = path.join(instance, "backups"); const storage = path.join(instance, "storage");
  for (const directory of [home, instance, data, backup, storage]) mkdirSync(directory, { recursive: true });
  const key = path.join(instance, "master.key"); writeFileSync(key, "fixture\n", { mode: 0o600 });
  const config = path.join(instance, "config.json");
  writeFileSync(config, `${JSON.stringify({ server: { host: "127.0.0.1", port: 3100, deploymentMode: "local_trusted", exposure: "private" }, database: { mode: "embedded-postgres", embeddedPostgresDataDir: data, backup: { enabled: true, dir: backup } }, storage: { provider: "local_disk", localDisk: { baseDir: storage } }, secrets: { provider: "local_encrypted", localEncrypted: { keyFilePath: key } } })}\n`);
  const envFile = path.join(root, "paperclip.env"); writeFileSync(envFile, "fixture\n", { mode: 0o600 });
  const fixtureBin = path.join(root, "fixture-bin"); mkdirSync(fixtureBin);
  const statShim = path.join(fixtureBin, "stat");
  writeFileSync(statShim, "#!/usr/bin/env bash\nif [[ \"$1\" == -c && \"$2\" == %U ]]; then printf 'root\\n'; else exec /usr/bin/stat \"$@\"; fi\n"); chmodSync(statShim, 0o755);
  const envFor = (release) => ({ ...process.env, PAPERCLIP_NODE: process.execPath, PAPERCLIP_INSTANCE_ID: "default",
    PATH: `${fixtureBin}:${process.env.PATH}`,
    PAPERCLIP_HOME: home, PAPERCLIP_CONFIG: config, PAPERCLIP_DATA_DIR: data, PAPERCLIP_BACKUP_DIR: backup,
    PAPERCLIP_STORAGE_DIR: storage, PAPERCLIP_SECRETS_KEY_FILE: key, PAPERCLIP_ENV_FILE: envFile, PAPERCLIP_SERVICE_MANAGED: "1",
    PAPERCLIP_EXECUTABLE: release.executable, PAPERCLIP_ARTIFACT_IDENTITY: release.identity,
    PAPERCLIP_ARTIFACT_MANIFEST: release.manifest, PAPERCLIP_ARTIFACT_ARCHIVE: release.archive,
    PAPERCLIP_RUNTIME_PID_FILE: pidFile, PAPERCLIP_RUNTIME_IDENTITY: runtimeIdentity });
  const preflight = (release) => execFileSync(path.join(lib, "paperclip-activation-preflight"), { env: envFor(release), encoding: "utf8" });

  assert.doesNotThrow(() => execFileSync(path.join(lib, "paperclip-preflight"), { env: envFor(oldRelease), encoding: "utf8" }));
  assert.match(preflight(oldRelease), /activation preflight passed/);
  const oldWrapper = spawn(path.join(lib, "paperclip-runtime-wrapper"), { env: envFor(oldRelease), stdio: "ignore" });
  await waitFor(() => existsSync(pidFile) && existsSync(runtimeIdentity));
  assert.match(preflight(oldRelease), /activation preflight passed/);
  assert.throws(() => preflight(newRelease), /stale runtime identity/);
  oldWrapper.kill("SIGTERM"); await new Promise((resolve) => oldWrapper.once("exit", resolve));
  await waitFor(() => !existsSync(pidFile) && !existsSync(runtimeIdentity));

  const freshWrapper = spawn(path.join(lib, "paperclip-runtime-wrapper"), { env: envFor(newRelease), stdio: "ignore" });
  await waitFor(() => existsSync(pidFile) && JSON.parse(readFileSync(runtimeIdentity, "utf8")).sourceSha === "b".repeat(40));
  assert.match(preflight(newRelease), /activation preflight passed/);
  freshWrapper.kill("SIGTERM"); await new Promise((resolve) => freshWrapper.once("exit", resolve));
  await waitFor(() => !existsSync(pidFile) && !existsSync(runtimeIdentity));
});
