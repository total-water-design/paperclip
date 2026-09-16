import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flipCurrentAtomic, initializeInstallStore, payloadPathFor, readInstallManifest, resolveInstallStorePaths, writeInstallManifestAtomic, type InstallManifest, type InstallRecord } from "../install-store.js";
import type { CommandRunner } from "../commands/install.js";
import { compareVersions, detectInstallMode, resolveUpdateRequest, restoreRetainedRecord, rollbackManagedInstall, updateCommand } from "../commands/update.js";

let root: string;
let previousHome: string | undefined;
let previousPaperclipHome: string | undefined;

function record(payloadPath: string, version: string, channel: "latest" | "canary" | "pinned" = "latest"): InstallRecord {
  return { source: "npm", version, channel, payloadPath, installedAt: `2026-07-22T00:00:0${version}.000Z` };
}
function createPayload(payloadPath: string, version: string): string {
  const entrypoint = path.join(payloadPath, "node_modules", "paperclipai", "dist", "index.js");
  fs.mkdirSync(path.dirname(entrypoint), { recursive: true });
  fs.writeFileSync(entrypoint, version);
  return entrypoint;
}
function issueAuthorization(paths: ReturnType<typeof resolveInstallStorePaths>, request: object): void { const root = path.join(paths.cliRoot, "controller-authorizations"); fs.mkdirSync(root, { recursive: true, mode: 0o700 }); fs.writeFileSync(path.join(root, "single-use.json"), JSON.stringify(request), { mode: 0o600 }); }
beforeEach(() => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-update-"));
  previousHome = process.env.HOME;
  previousPaperclipHome = process.env.PAPERCLIP_HOME;
  process.env.HOME = path.join(root, "home");
  process.env.PAPERCLIP_HOME = path.join(root, "paperclip");
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  if (previousHome === undefined) delete process.env.HOME; else process.env.HOME = previousHome;
  if (previousPaperclipHome === undefined) delete process.env.PAPERCLIP_HOME; else process.env.PAPERCLIP_HOME = previousPaperclipHome;
  fs.rmSync(root, { recursive: true, force: true });
  process.exitCode = undefined;
});

describe("update command", () => {
  it("appends an authorized immutable retained record without changing current", () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const active = payloadPathFor(paths, "npm", "active"); const executable = createPayload(active, "1.0.0"); flipCurrentAtomic(active, paths);
    const sha = "72b50614011b457093cd5e3be189a4ca7a9aab75"; const retained = payloadPathFor(paths, "git", sha.slice(0, 12)); createPayload(retained, "1.0.0");
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(active, "1.0.0"), previous: [] }, paths); const currentBefore = fs.readlinkSync(paths.currentPath);
    const request = { operation: "restore-retained-record/v1", sha, payloadPath: retained, source: "git", repo: "paperclipai/paperclip", ref: sha }; issueAuthorization(paths, request); const result = restoreRetainedRecord(JSON.stringify({ ...request, authorization: { controllerAuthorizationId: "single-use" } }), paths);
    expect(fs.readlinkSync(paths.currentPath)).toBe(currentBefore); expect(result.manifest.previous).toHaveLength(1); expect(readInstallManifest(paths)?.previous[0]?.sha).toBe(sha); expect(fs.existsSync(result.backupPath)).toBe(true);
  });
  it("refuses duplicate and malformed retained-record requests without mutation", () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths); const active = payloadPathFor(paths, "npm", "active"); createPayload(active, "1.0.0"); flipCurrentAtomic(active, paths);
    const sha = "72b50614011b457093cd5e3be189a4ca7a9aab75"; const retained = payloadPathFor(paths, "git", sha.slice(0, 12)); createPayload(retained, "1.0.0");
    const manifest: InstallManifest = { schemaVersion: 1, ...record(active, "1.0.0"), previous: [{ source: "git", version: "1.0.0", channel: "pinned", repo: "paperclipai/paperclip", ref: sha, sha, payloadPath: retained, installedAt: "2026-01-01T00:00:00Z" }] }; writeInstallManifestAtomic(manifest, paths); const before = fs.readFileSync(paths.manifestPath, "utf8");
    const request = { operation: "restore-retained-record/v1", sha, payloadPath: retained, source: "git", repo: "paperclipai/paperclip", ref: sha }; issueAuthorization(paths, request); expect(() => restoreRetainedRecord(JSON.stringify({ ...request, authorization: { controllerAuthorizationId: "single-use" } }), paths)).toThrow("already exists");
    expect(() => restoreRetainedRecord("{}", paths)).toThrow("invalid controller request"); expect(fs.readFileSync(paths.manifestPath, "utf8")).toBe(before);
  });
  it("orders SemVer prerelease identifiers numerically", () => {
    expect(compareVersions("1.0.0-canary.10", "1.0.0-canary.2")).toBeGreaterThan(0);
    expect(compareVersions("1.0.0-1", "1.0.0-alpha")).toBeLessThan(0);
    expect(compareVersions("1.0.0-alpha", "1.0.0-alpha.1")).toBeLessThan(0);
  });

  it("detects managed, global npm, npx, and source modes", () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const payload = payloadPathFor(paths, "npm", "1.0.0"); const entrypoint = createPayload(payload, "1.0.0");
    flipCurrentAtomic(payload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(payload, "1.0.0"), previous: [] }, paths);
    expect(detectInstallMode(entrypoint, paths)).toBe("managed");
    expect(detectInstallMode(path.join(root, "lib", "node_modules", "paperclipai", "dist", "index.js"), paths)).toBe("global-npm");
    expect(detectInstallMode(path.join(root, ".npm", "_npx", "abc", "node_modules", "paperclipai", "dist", "index.js"), paths)).toBe("npx");
    const source = path.join(root, "source"); fs.mkdirSync(path.join(source, ".git"), { recursive: true });
    expect(detectInstallMode(path.join(source, "cli", "src", "index.ts"), paths)).toBe("source");
  });

  it("resolves channels and keeps pinned installs pinned by default", () => {
    const manifest = { channel: "pinned", version: "1.2.3" } as InstallManifest;
    expect(resolveUpdateRequest(manifest, {})).toEqual({ spec: "1.2.3", channel: "pinned", explicit: false });
    expect(resolveUpdateRequest(manifest, { latest: true })).toEqual({ spec: "latest", channel: "latest", explicit: true });
    expect(() => resolveUpdateRequest(manifest, { latest: true, canary: true })).toThrow("only one");
  });

  it("re-resolves a moving git branch and activates the new SHA payload", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const oldSha = "1".repeat(40); const newSha = "2".repeat(40);
    const oldPayload = payloadPathFor(paths, "git", oldSha.slice(0, 12));
    const executable = createPayload(oldPayload, "0.3.1");
    fs.writeFileSync(path.join(oldPayload, "node_modules", "paperclipai", "package.json"), JSON.stringify({ version: "0.3.1" }));
    const newPayload = payloadPathFor(paths, "git", newSha.slice(0, 12));
    createPayload(newPayload, "0.3.1");
    fs.writeFileSync(path.join(newPayload, "node_modules", "paperclipai", "package.json"), JSON.stringify({ version: "0.3.1" }));
    flipCurrentAtomic(oldPayload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, source: "git", version: "0.3.1", channel: "pinned", repo: "paperclipai/paperclip", ref: "master", sha: oldSha, payloadPath: oldPayload, installedAt: "2026-07-22T00:00:00.000Z", previous: [] }, paths);
    const backup = vi.fn(async () => undefined);
    const confirm = vi.fn(async () => true);
    const restartActiveService = vi.fn(async () => true);
    const runCommand = vi.fn(async (file: string) => file === "curl" ? { stdout: JSON.stringify({ sha: newSha }), stderr: "" } : { stdout: "0.3.1\n", stderr: "" });
    await updateCommand({}, { paths, executablePath: executable, runCommand, backup, confirm, restartActiveService, hasInstanceData: () => true, now: () => new Date("2026-07-22T12:00:00Z") });
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining(`commit ${newSha.slice(0, 12)}`));
    expect(backup).toHaveBeenCalledOnce();
    expect(restartActiveService).toHaveBeenCalledWith("0.3.1");
    expect(readInstallManifest(paths)?.sha).toBe(newSha);
    expect(fs.realpathSync(paths.currentPath)).toBe(fs.realpathSync(newPayload));
  });

  it("reports SHA git installs as pinned without resolving again", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const sha = "3".repeat(40); const payload = payloadPathFor(paths, "git", sha.slice(0, 12)); const executable = createPayload(payload, "0.3.1");
    flipCurrentAtomic(payload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, source: "git", version: "0.3.1", channel: "pinned", repo: "paperclipai/paperclip", ref: sha.slice(0, 12), sha, payloadPath: payload, installedAt: "2026-07-22T00:00:00.000Z", previous: [] }, paths);
    const runCommand = vi.fn(async () => ({ stdout: "", stderr: "" }));
    await updateCommand({}, { paths, executablePath: executable, runCommand });
    expect(runCommand).not.toHaveBeenCalled();
  });

  it("requires explicit confirmation before downgrading", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const payload = payloadPathFor(paths, "npm", "2.0.0"); const entrypoint = createPayload(payload, "2.0.0"); flipCurrentAtomic(payload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(payload, "2.0.0"), previous: [] }, paths);
    const runCommand = vi.fn(async () => ({ stdout: '"1.0.0"\n', stderr: "" }));
    await expect(updateCommand({ version: "1.0.0", dryRun: true }, { paths, executablePath: entrypoint, runCommand, confirm: async () => false })).rejects.toThrow("Downgrade cancelled");
  });

  it("requires explicit confirmation before a global npm downgrade", async () => {
    const paths = resolveInstallStorePaths();
    const executable = path.join(root, "lib", "node_modules", "paperclipai", "dist", "index.js");
    const runCommand = vi.fn(async () => ({ stdout: '"0.2.0"\n', stderr: "" }));
    await expect(updateCommand({ version: "0.2.0" }, { paths, executablePath: executable, runCommand, confirm: async () => false })).rejects.toThrow("Downgrade cancelled");
    expect(runCommand).toHaveBeenCalledTimes(1);
  });

  it("isolates global npm updates from hostile registry configuration", async () => {
    const paths = resolveInstallStorePaths();
    const executable = path.join(root, "lib", "node_modules", "paperclipai", "dist", "index.js");
    vi.stubEnv("NPM_CONFIG_REGISTRY", "http://attacker-registry.invalid");
    fs.mkdirSync(process.env.HOME!, { recursive: true });
    fs.writeFileSync(path.join(process.env.HOME!, ".npmrc"), "registry=http://attacker-registry.invalid\n");
    const runCommand = vi.fn<CommandRunner>(async (_file, args, commandOptions) => {
      if (args[0] === "view") return { stdout: '"2.0.0"\n', stderr: "" };
      expect(args).toContain("--registry=https://registry.npmjs.org");
      expect(args).toContain("--@paperclipai:registry=https://registry.npmjs.org");
      expect(commandOptions?.env?.NPM_CONFIG_REGISTRY).toBe("https://registry.npmjs.org");
      expect(commandOptions?.env?.npm_config_registry).toBe("https://registry.npmjs.org");
      expect(commandOptions?.env?.NPM_CONFIG_USERCONFIG).toBe(commandOptions?.env?.npm_config_userconfig);
      expect(fs.readFileSync(commandOptions!.env!.NPM_CONFIG_USERCONFIG!, "utf8")).toContain("registry=https://registry.npmjs.org");
      return { stdout: "", stderr: "" };
    });
    await updateCommand({}, { paths, executablePath: executable, runCommand });
    expect(runCommand).toHaveBeenCalledTimes(2);
  });

  it("backs up, installs side-by-side, flips, and rolls back instantly", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const oldPayload = payloadPathFor(paths, "npm", "1.0.0"); const executable = createPayload(oldPayload, "1.0.0"); flipCurrentAtomic(oldPayload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(oldPayload, "1.0.0"), previous: [] }, paths);
    const backup = vi.fn(async () => undefined);
    const restartActiveService = vi.fn(async () => true);
    const runCommand = vi.fn(async (file: string, args: string[]) => {
      if (args[0] === "view") return { stdout: '"2.0.0"\n', stderr: "" };
      if (file === "npm" && args[0] === "install") { const prefix = args[args.indexOf("--prefix") + 1]; createPayload(prefix, "2.0.0"); return { stdout: "", stderr: "" }; }
      return { stdout: "2.0.0\n", stderr: "" };
    });
    await updateCommand({}, { paths, executablePath: executable, runCommand, backup, restartActiveService, hasInstanceData: () => true, now: () => new Date("2026-07-22T12:00:00Z") });
    expect(backup).toHaveBeenCalledOnce();
    expect(restartActiveService).toHaveBeenCalledWith("2.0.0");
    expect(readInstallManifest(paths)?.version).toBe("2.0.0");
    expect(fs.realpathSync(paths.currentPath)).toBe(fs.realpathSync(payloadPathFor(paths, "npm", "2.0.0")));
    const rolledBack = rollbackManagedInstall(paths);
    expect(rolledBack.version).toBe("1.0.0");
    expect(fs.realpathSync(paths.currentPath)).toBe(fs.realpathSync(oldPayload));
  });

  it("discards only an unsafe retained git record without changing current or restarting", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const activePayload = payloadPathFor(paths, "npm", "2026.831.1");
    const executable = createPayload(activePayload, "2026.831.1");
    const validSha = "72b50614011b457093cd5e3be189a4ca7a9aab75";
    const invalidSha = "4fac7834b048d0942c0aa868a74b62ad0f0330fc";
    const validPayload = payloadPathFor(paths, "git", validSha.slice(0, 12));
    const invalidPayload = payloadPathFor(paths, "git", invalidSha.slice(0, 12));
    createPayload(validPayload, "0.3.1");
    fs.mkdirSync(invalidPayload, { recursive: true });
    fs.writeFileSync(path.join(invalidPayload, "package.json"), "{}");
    flipCurrentAtomic(activePayload, paths);
    const manifest: InstallManifest = {
      schemaVersion: 1,
      ...record(activePayload, "2026.831.1"),
      previous: [
        { source: "git", version: "0.3.1", channel: "pinned", repo: "paperclipai/paperclip", ref: validSha, sha: validSha, payloadPath: validPayload, installedAt: "2026-07-22T00:00:00.000Z" },
        { source: "git", version: "0.3.1", channel: "pinned", repo: "paperclipai/paperclip", ref: invalidSha, sha: invalidSha, payloadPath: invalidPayload, installedAt: "2026-07-22T00:00:01.000Z" },
      ],
    };
    writeInstallManifestAtomic(manifest, paths);
    const restartActiveService = vi.fn(async () => true);
    const backup = vi.fn(async () => undefined);
    const activationEnv = path.join(root, "activation", "default.env");
    fs.mkdirSync(path.dirname(activationEnv), { recursive: true });
    fs.writeFileSync(activationEnv, "AUTHORIZED_ALPHA=alpha\nAUTHORIZED_BETA=beta\n");
    const activationBefore = fs.readFileSync(activationEnv, "utf8");

    await updateCommand({ discardUnsafePrevious: invalidSha }, { paths, executablePath: executable, restartActiveService, backup });

    expect(fs.realpathSync(paths.currentPath)).toBe(fs.realpathSync(activePayload));
    expect(readInstallManifest(paths)).toEqual({ ...manifest, previous: [manifest.previous[0]!] });
    expect(restartActiveService).not.toHaveBeenCalled();
    expect(backup).not.toHaveBeenCalled();
    expect(fs.readFileSync(activationEnv, "utf8")).toBe(activationBefore);
    expect(fs.existsSync(invalidPayload)).toBe(true);
  });

  it("refuses to discard a bootable retained payload and refuses rollback to an unsafe one", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const activePayload = payloadPathFor(paths, "npm", "2026.831.1");
    const executable = createPayload(activePayload, "2026.831.1");
    const sha = "4".repeat(40); const unsafePayload = payloadPathFor(paths, "git", sha.slice(0, 12));
    const bootableSha = "7".repeat(40); const bootablePayload = payloadPathFor(paths, "git", bootableSha.slice(0, 12));
    fs.mkdirSync(unsafePayload, { recursive: true }); createPayload(bootablePayload, "0.3.1"); flipCurrentAtomic(activePayload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(activePayload, "2026.831.1"), previous: [
      { source: "git", version: "0.3.1", channel: "pinned", repo: "paperclipai/paperclip", ref: sha, sha, payloadPath: unsafePayload, installedAt: "2026-07-22T00:00:00.000Z" },
      { source: "git", version: "0.3.1", channel: "pinned", repo: "paperclipai/paperclip", ref: bootableSha, sha: bootableSha, payloadPath: bootablePayload, installedAt: "2026-07-22T00:00:01.000Z" },
    ] }, paths);

    await expect(updateCommand({ discardUnsafePrevious: bootableSha }, { paths, executablePath: executable })).rejects.toThrow("Refusing to discard bootable");
    expect(() => rollbackManagedInstall(paths)).toThrow("not bootable");
    expect(fs.realpathSync(paths.currentPath)).toBe(fs.realpathSync(activePayload));
  });

  it("refuses a missing selector or a repair that would retain an unbootable payload", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const activePayload = payloadPathFor(paths, "npm", "2026.831.1");
    const executable = createPayload(activePayload, "2026.831.1");
    const invalidSha = "4fac7834b048d0942c0aa868a74b62ad0f0330fc";
    const retainedSha = "72b50614011b457093cd5e3be189a4ca7a9aab75";
    const invalidPayload = payloadPathFor(paths, "git", invalidSha.slice(0, 12));
    const retainedPayload = payloadPathFor(paths, "git", retainedSha.slice(0, 12));
    fs.mkdirSync(invalidPayload, { recursive: true });
    fs.mkdirSync(retainedPayload, { recursive: true });
    flipCurrentAtomic(activePayload, paths);
    const manifest: InstallManifest = { schemaVersion: 1, ...record(activePayload, "2026.831.1"), previous: [
      { source: "git", version: "0.3.1", channel: "pinned", repo: "paperclipai/paperclip", ref: invalidSha, sha: invalidSha, payloadPath: invalidPayload, installedAt: "2026-07-22T00:00:00.000Z" },
      { source: "git", version: "0.3.1", channel: "pinned", repo: "paperclipai/paperclip", ref: retainedSha, sha: retainedSha, payloadPath: retainedPayload, installedAt: "2026-07-22T00:00:01.000Z" },
    ] };
    writeInstallManifestAtomic(manifest, paths);

    await expect(updateCommand({ discardUnsafePrevious: "f".repeat(40) }, { paths, executablePath: executable })).rejects.toThrow("No retained git payload");
    await expect(updateCommand({ discardUnsafePrevious: invalidSha }, { paths, executablePath: executable })).rejects.toThrow("retained payload is not bootable");
    expect(readInstallManifest(paths)).toEqual(manifest);
    expect(fs.realpathSync(paths.currentPath)).toBe(fs.realpathSync(activePayload));
  });

  it("explains how to recover when the pre-update database is unreachable", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const oldPayload = payloadPathFor(paths, "npm", "1.0.0"); const executable = createPayload(oldPayload, "1.0.0"); flipCurrentAtomic(oldPayload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(oldPayload, "1.0.0"), previous: [] }, paths);
    const backupError = Object.assign(new Error("connect ECONNREFUSED 127.0.0.1:54329"), { code: "ECONNREFUSED" });
    const backup = vi.fn(async () => { throw backupError; });
    const runCommand = vi.fn(async () => ({ stdout: '"2.0.0"\n', stderr: "" }));

    await expect(updateCommand({}, { paths, executablePath: executable, runCommand, backup, hasInstanceData: () => true })).rejects.toThrow(
      "Start the service with `paperclipai service start` and retry, or skip the backup with `paperclipai update --no-backup`.",
    );
    expect(backup).toHaveBeenCalledOnce();
    expect(readInstallManifest(paths)?.version).toBe("1.0.0");
  });

  it("skips the pre-update backup when there is no onboarded instance data", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const oldPayload = payloadPathFor(paths, "npm", "1.0.0"); const executable = createPayload(oldPayload, "1.0.0"); flipCurrentAtomic(oldPayload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(oldPayload, "1.0.0"), previous: [] }, paths);
    const backup = vi.fn(async () => undefined);
    const log = vi.spyOn(console, "log").mockImplementation(() => undefined);
    const runCommand = vi.fn(async (file: string, args: string[]) => {
      if (args[0] === "view") return { stdout: '"2.0.0"\n', stderr: "" };
      if (file === "npm" && args[0] === "install") { createPayload(args[args.indexOf("--prefix") + 1], "2.0.0"); return { stdout: "", stderr: "" }; }
      return { stdout: "2.0.0\n", stderr: "" };
    });

    await updateCommand({}, { paths, executablePath: executable, runCommand, backup, restartActiveService: async () => false, hasInstanceData: () => false });

    expect(backup).not.toHaveBeenCalled();
    expect(log).toHaveBeenCalledWith(expect.stringContaining("has not been onboarded and has no data to back up"));
    expect(readInstallManifest(paths)?.version).toBe("2.0.0");
  });

  it("does not inherit a managed pin for global npm updates", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const managedPayload = payloadPathFor(paths, "npm", "1.2.3"); createPayload(managedPayload, "1.2.3");
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(managedPayload, "1.2.3"), channel: "pinned", previous: [] }, paths);
    const executable = path.join(root, "lib", "node_modules", "paperclipai", "dist", "index.js");
    const runCommand = vi.fn(async (_file: string, args: string[]) => args[0] === "view" ? { stdout: '"2.0.0"\n', stderr: "" } : { stdout: "", stderr: "" });
    await updateCommand({ dryRun: true }, { paths, executablePath: executable, runCommand });
    expect(runCommand).toHaveBeenCalledWith("npm", expect.arrayContaining(["view", "paperclipai@latest"]), expect.anything());
  });

  it("rolls back the active payload when restart validation fails", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const oldPayload = payloadPathFor(paths, "npm", "1.0.0"); const executable = createPayload(oldPayload, "1.0.0"); flipCurrentAtomic(oldPayload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(oldPayload, "1.0.0"), previous: [] }, paths);
    const runCommand = vi.fn(async (file: string, args: string[]) => {
      if (args[0] === "view") return { stdout: '"2.0.0"\n', stderr: "" };
      if (file === "npm" && args[0] === "install") { createPayload(args[args.indexOf("--prefix") + 1], "2.0.0"); return { stdout: "", stderr: "" }; }
      return { stdout: "2.0.0\n", stderr: "" };
    });
    const restartActiveService = vi.fn(async (version: string) => { if (version === "2.0.0") throw new Error("health timeout"); return true; });
    await expect(updateCommand({}, { paths, executablePath: executable, runCommand, backup: async () => undefined, restartActiveService })).rejects.toThrow("rolled back to 1.0.0");
    expect(readInstallManifest(paths)?.version).toBe("1.0.0");
    expect(fs.realpathSync(paths.currentPath)).toBe(fs.realpathSync(oldPayload));
    expect(restartActiveService).toHaveBeenLastCalledWith("1.0.0");
  });

  it("surfaces a failure to restart the rolled-back payload", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const oldPayload = payloadPathFor(paths, "npm", "1.0.0"); const executable = createPayload(oldPayload, "1.0.0"); flipCurrentAtomic(oldPayload, paths);
    writeInstallManifestAtomic({ schemaVersion: 1, ...record(oldPayload, "1.0.0"), previous: [] }, paths);
    const runCommand = vi.fn(async (file: string, args: string[]) => {
      if (args[0] === "view") return { stdout: '"2.0.0"\n', stderr: "" };
      if (file === "npm" && args[0] === "install") { createPayload(args[args.indexOf("--prefix") + 1], "2.0.0"); return { stdout: "", stderr: "" }; }
      return { stdout: "2.0.0\n", stderr: "" };
    });
    const restartActiveService = vi.fn(async (version: string) => {
      throw new Error(version === "2.0.0" ? "health timeout" : "rollback restart failed");
    });

    await expect(updateCommand({}, {
      paths,
      executablePath: executable,
      runCommand,
      backup: async () => undefined,
      restartActiveService,
    })).rejects.toThrow("rolled-back service also failed to restart");
    expect(readInstallManifest(paths)?.version).toBe("1.0.0");
    expect(fs.realpathSync(paths.currentPath)).toBe(fs.realpathSync(oldPayload));
    expect(restartActiveService).toHaveBeenNthCalledWith(1, "2.0.0");
    expect(restartActiveService).toHaveBeenNthCalledWith(2, "1.0.0");
  });

});
