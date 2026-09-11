import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type CommandRunner,
  installCommand,
  installGitPayload,
  stageGitCommand,
  GITHUB_SOURCE_TOKEN_ENV,
  resolveGitHubRef,
  resolveGitInstallRequest,
  resolveGitInstallWorkspacePackages,
  resolveNpmInstallRequest,
  runCommandWithDiagnostics,
} from "../commands/install.js";
import { uninstallCommand } from "../commands/uninstall.js";
import { resolvePaperclipInstanceId } from "../config/home.js";
import {
  INSTALL_MANIFEST_VERSION,
  flipCurrentAtomic,
  initializeInstallStore,
  payloadPathFor,
  readInstallManifest,
  resolveInstallStorePaths,
  withInstallStoreLock,
  writeInstallManifestAtomic,
} from "../install-store.js";
import { resolveCliVersion } from "../version.js";
import { systemdServiceName } from "../services/service-manager.js";

const ORIGINAL_ENV = { ...process.env };

describe("managed install commands", () => {
  let root: string;

  beforeEach(() => {
    root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-install-command-"));
    process.env = {
      ...ORIGINAL_ENV,
      HOME: path.join(root, "home"),
      PAPERCLIP_HOME: path.join(root, "home", ".paperclip"),
      PATH: "/usr/bin:/bin",
      SHELL: "/bin/bash",
    };
    fs.mkdirSync(process.env.HOME!, { recursive: true });
    vi.spyOn(console, "log").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    process.env = { ...ORIGINAL_ENV };
    fs.rmSync(root, { recursive: true, force: true });
  });

  it("selects stable, canary, and exact-version npm sources", () => {
    expect(resolveNpmInstallRequest({})).toEqual({ spec: "latest", channel: "latest" });
    expect(resolveNpmInstallRequest({ canary: true })).toEqual({ spec: "canary", channel: "canary" });
    expect(resolveNpmInstallRequest({ version: "2026.720.0" })).toEqual({
      spec: "2026.720.0",
      channel: "pinned",
    });
    expect(() => resolveNpmInstallRequest({ canary: true, version: "1.2.3" })).toThrow();
    expect(() => resolveNpmInstallRequest({ version: "latest" })).toThrow();
  });

  it("resolves branch, tag, full SHA, and short SHA refs through GitHub", async () => {
    const sha = "a".repeat(40);
    const runCommand = vi.fn(async (_file: string, _args: string[]) => ({ stdout: JSON.stringify({ sha }), stderr: "" }));
    for (const ref of ["master", "v1.2.3", sha, sha.slice(0, 12)]) {
      await expect(resolveGitHubRef("paperclipai/paperclip", ref, runCommand)).resolves.toBe(sha);
    }
    expect(runCommand.mock.calls.map((call) => call[1].at(-1))).toEqual([
      "https://api.github.com/repos/paperclipai/paperclip/commits/master",
      "https://api.github.com/repos/paperclipai/paperclip/commits/v1.2.3",
      `https://api.github.com/repos/paperclipai/paperclip/commits/${sha}`,
      `https://api.github.com/repos/paperclipai/paperclip/commits/${sha.slice(0, 12)}`,
    ]);
  });

  it("supports fork overrides and classifies SHA refs as pinned", () => {
    expect(resolveGitInstallRequest({ ref: "feature/test", repo: "HenkDz/paperclip" })).toEqual({ repo: "HenkDz/paperclip", ref: "feature/test", pinned: false });
    expect(resolveGitInstallRequest({ ref: "abcdef1" })).toEqual({ repo: "paperclipai/paperclip", ref: "abcdef1", pinned: true });
    expect(() => resolveGitInstallRequest({ repo: "HenkDz/paperclip" })).toThrow("requires --ref");
  });

  it("requires explicit non-interactive consent before resolving git refs", async () => {
    const runCommand = vi.fn();

    await expect(installCommand({ ref: "master", repo: "HenkDz/paperclip" }, { runCommand }))
      .rejects.toThrow("Re-run with --yes");

    expect(runCommand).not.toHaveBeenCalled();
  });

  it("reuses a SHA-keyed git payload without downloading or rebuilding", async () => {
    const sha = "b".repeat(40);
    const paths = resolveInstallStorePaths();
    const payloadPath = payloadPathFor(paths, "git", sha.slice(0, 12));
    const packageRoot = path.join(payloadPath, "node_modules", "paperclipai");
    fs.mkdirSync(path.join(packageRoot, "dist"), { recursive: true });
    fs.writeFileSync(path.join(packageRoot, "package.json"), JSON.stringify({ version: "0.3.1" }));
    fs.writeFileSync(path.join(packageRoot, "dist", "index.js"), "#!/usr/bin/env node\n");
    const runCommand = vi.fn(async (_file: string, _args: string[]) => ({ stdout: "0.3.1\n", stderr: "" }));
    await expect(installGitPayload("paperclipai/paperclip", sha, runCommand, paths)).resolves.toEqual({ payloadPath, reused: true, version: "0.3.1" });
    expect(runCommand).toHaveBeenCalledOnce();
    expect(runCommand.mock.calls[0]?.[0]).toBe(process.execPath);
  });

  const createGitCheckoutRunCommand = (sha: string) =>
    vi.fn(async (file: string, args: string[], _options?: Parameters<CommandRunner>[2]) => {
      if (file === "curl" && !args.includes("--output")) return { stdout: JSON.stringify({ sha }), stderr: "" };
      if (file === "curl") { fs.writeFileSync(args[args.indexOf("--output") + 1], "archive"); return { stdout: "", stderr: "" }; }
      if (file === "tar") {
        const checkout = args[args.indexOf("-C") + 1];
        const packages = [
          { dir: "packages/shared", name: "@paperclipai/shared", packageJson: { name: "@paperclipai/shared", version: "0.3.1" } },
          { dir: "packages/db", name: "@paperclipai/db", packageJson: { name: "@paperclipai/db", version: "0.3.1", dependencies: { "@paperclipai/shared": "workspace:*" }, bundleDependencies: ["embedded-postgres"] } },
          { dir: "server", name: "@paperclipai/server", packageJson: { name: "@paperclipai/server", version: "0.3.1", dependencies: { "@paperclipai/db": "workspace:*" } } },
        ];
        fs.mkdirSync(path.join(checkout, "cli"), { recursive: true });
        fs.writeFileSync(path.join(checkout, "cli", "package.json"), JSON.stringify({ version: "0.3.1" }));
        fs.mkdirSync(path.join(checkout, "scripts"), { recursive: true });
        fs.writeFileSync(path.join(checkout, "scripts", "release-package-manifest.json"), JSON.stringify(packages.map(({ dir, name }) => ({ dir, name }))));
        for (const workspacePackage of packages) {
          fs.mkdirSync(path.join(checkout, workspacePackage.dir), { recursive: true });
          fs.writeFileSync(path.join(checkout, workspacePackage.dir, "package.json"), JSON.stringify(workspacePackage.packageJson));
        }
        return { stdout: "", stderr: "" };
      }
      if (file === "corepack") {
        if (args.includes("pack")) {
          const destination = args[args.indexOf("--pack-destination") + 1];
          const packageDir = args[args.indexOf("--dir") + 1];
          const packageName = packageDir === "server" ? "paperclipai-server" : "paperclipai-shared";
          fs.writeFileSync(path.join(destination, `${packageName}-0.3.1.tgz`), "package");
        }
        return { stdout: "", stderr: "" };
      }
      if (file === "bash") return { stdout: "", stderr: "" };
      if (file === "npm" && args[0] === "pack") {
        const packageName = args[1]?.includes("workspace-package-") ? "paperclipai-db" : "paperclipai";
        fs.writeFileSync(path.join(args[args.indexOf("--pack-destination") + 1], `${packageName}-0.3.1.tgz`), "package");
        return { stdout: "", stderr: "" };
      }
      if (file === "npm" && args[0] === "install") { const prefix = args[args.indexOf("--prefix") + 1]; const packageRoot = path.join(prefix, "node_modules", "paperclipai"); fs.mkdirSync(path.join(packageRoot, "dist"), { recursive: true }); fs.writeFileSync(path.join(packageRoot, "package.json"), JSON.stringify({ version: "0.3.1" })); fs.writeFileSync(path.join(packageRoot, "dist", "index.js"), "#!/usr/bin/env node\n"); for (const filePath of [path.join(prefix, "node_modules", "@paperclipai", "adapter-utils", "dist", "sandbox-callback-bridge.js"), path.join(prefix, "node_modules", "@paperclipai", "server", "dist", "routes", "issues.js")]) { fs.mkdirSync(path.dirname(filePath), { recursive: true }); fs.writeFileSync(filePath, "export {};\n"); } return { stdout: "", stderr: "" }; }
      if (file === process.execPath && args[0]?.endsWith("prepare-bundled-package.mjs")) {
        fs.mkdirSync(args[2], { recursive: true });
        fs.writeFileSync(path.join(args[2], "package.json"), JSON.stringify({ name: "@paperclipai/db", version: "0.3.1" }));
        return { stdout: "", stderr: "" };
      }
      if (file === process.execPath) return { stdout: "0.3.1\n", stderr: "" };
      throw new Error(`Unexpected command: ${file} ${args.join(" ")}`);
    });

  it("installs a GitHub branch through codeload and reuses the resolved SHA", async () => {
    const sha = "c".repeat(40);
    const runCommand = createGitCheckoutRunCommand(sha);
    await installCommand({ ref: "master", repo: "HenkDz/paperclip", yes: true }, { runCommand });
    await installCommand({ ref: "master", repo: "HenkDz/paperclip", yes: true }, { runCommand });
    const manifest = readInstallManifest(resolveInstallStorePaths());
    expect(manifest).toMatchObject({ source: "git", repo: "HenkDz/paperclip", ref: "master", sha });
    expect(manifest?.payloadPath).toContain(path.join("git", sha.slice(0, 12)));
    expect(runCommand.mock.calls.filter(([command, args]) => command === "curl" && args.includes("--output"))).toHaveLength(1);
    expect(runCommand.mock.calls.filter(([command, args]) => command === "corepack" && args[1] === "install")).toHaveLength(1);
    expect(runCommand.mock.calls.filter(([command, args]) => command === "corepack" && args.includes("pack"))).toHaveLength(2);
    expect(runCommand.mock.calls.filter(([command, args]) => command === process.execPath && args[0]?.endsWith("prepare-bundled-package.mjs"))).toHaveLength(1);
    expect(runCommand.mock.calls.filter(([command, args]) => command === "npm" && args[0] === "pack")).toHaveLength(2);
    const installCall = runCommand.mock.calls.find(([command, args]) => command === "npm" && args[0] === "install");
    expect(installCall?.[1].filter((arg) => arg.endsWith(".tgz"))).toHaveLength(4);
  });

  it("stages an exact Git SHA without changing current or the active manifest", async () => {
    const sha = "e".repeat(40);
    const runCommand = createGitCheckoutRunCommand(sha);
    const paths = resolveInstallStorePaths();
    await stageGitCommand({ ref: sha, repo: "HenkDz/paperclip", yes: true, json: true }, { runCommand, now: () => new Date("2026-09-11T00:00:00Z") });
    expect(fs.existsSync(paths.currentPath)).toBe(false);
    expect(readInstallManifest(paths)).toBeNull();
    const staged = JSON.parse(fs.readFileSync(path.join(paths.stagedRoot, `${sha}.json`), "utf8"));
    expect(staged).toMatchObject({ sha, payloadPath: payloadPathFor(paths, "git", sha.slice(0, 12)) });
    expect(staged.entrypointSha256).toMatch(/^[0-9a-f]{64}$/);
    expect(staged.adapterBridgeSha256).toMatch(/^[0-9a-f]{64}$/);
    expect(staged.serverRouteSha256).toMatch(/^[0-9a-f]{64}$/);
  });

  it("stages a protected exact SHA through the explicitly projected source token without emitting it", async () => {
    const sha = "f".repeat(40);
    const token = "github_pat_clean_room_fixture_123";
    process.env[GITHUB_SOURCE_TOKEN_ENV] = token;
    const sourceConfigs: string[] = [];
    const delegate = createGitCheckoutRunCommand(sha);
    const runCommand: CommandRunner = async (file, args, options) => {
      const configIndex = args.indexOf("--config");
      if (file === "curl" && configIndex >= 0) {
        const config = fs.readFileSync(args[configIndex + 1]!, "utf8");
        sourceConfigs.push(config);
        expect(args).not.toContain(token);
        expect(args.join(" ")).not.toContain("Authorization:");
      }
      return delegate(file, args, options);
    };

    await stageGitCommand({ ref: sha, repo: "total-water-design/total-water-design-suite", yes: true, json: true }, { runCommand, now: () => new Date("2026-09-11T00:00:00Z") });

    const paths = resolveInstallStorePaths();
    const identity = JSON.parse(fs.readFileSync(path.join(paths.stagedRoot, `${sha}.json`), "utf8"));
    expect(sourceConfigs).toHaveLength(2);
    expect(sourceConfigs).toEqual([`header = "Authorization: Bearer ${token}"\n`, `header = "Authorization: Bearer ${token}"\n`]);
    expect(JSON.stringify(identity)).not.toContain(token);
    expect(console.log).toHaveBeenLastCalledWith(expect.not.stringContaining(token));
    expect(identity).toMatchObject({ sha, payloadPath: payloadPathFor(paths, "git", sha.slice(0, 12)) });
    for (const field of ["manifestSha256", "entrypointSha256", "adapterBridgeSha256", "serverRouteSha256"]) {
      expect(identity[field]).toMatch(/^[0-9a-f]{64}$/);
    }
  });

  it("fails a protected source fetch before staging and leaves the active payload untouched", async () => {
    const activeSha = "1".repeat(40);
    const requestedSha = "2".repeat(40);
    const paths = resolveInstallStorePaths();
    const activePayload = payloadPathFor(paths, "git", activeSha.slice(0, 12));
    fs.mkdirSync(activePayload, { recursive: true });
    fs.symlinkSync(activePayload, paths.currentPath);
    const activeManifest = {
      schemaVersion: INSTALL_MANIFEST_VERSION as typeof INSTALL_MANIFEST_VERSION,
      source: "git" as const,
      version: "0.3.1",
      channel: "pinned" as const,
      repo: "total-water-design/total-water-design-suite",
      ref: activeSha,
      sha: activeSha,
      payloadPath: activePayload,
      installedAt: "2026-09-10T00:00:00Z",
      previous: [],
    };
    writeInstallManifestAtomic(activeManifest, paths);
    const beforeManifest = fs.readFileSync(paths.manifestPath, "utf8");
    const beforeTarget = fs.readlinkSync(paths.currentPath);
    process.env[GITHUB_SOURCE_TOKEN_ENV] = "github_pat_clean_room_fixture_123";
    const runCommand = vi.fn(async (file: string, args: string[]) => {
      if (file === "curl") {
        expect(fs.readFileSync(args[args.indexOf("--config") + 1]!, "utf8")).toContain("Authorization: Bearer");
        throw new Error("curl: (22) The requested URL returned error: 404");
      }
      throw new Error(`Unexpected command: ${file}`);
    });

    await expect(stageGitCommand({ ref: requestedSha, repo: "total-water-design/total-water-design-suite", yes: true, json: true }, { runCommand }))
      .rejects.toThrow("404");
    expect(fs.readlinkSync(paths.currentPath)).toBe(beforeTarget);
    expect(fs.readFileSync(paths.manifestPath, "utf8")).toBe(beforeManifest);
    expect(fs.existsSync(path.join(paths.stagedRoot, `${requestedSha}.json`))).toBe(false);
    expect(runCommand).toHaveBeenCalledOnce();
  });

  it("builds git checkouts with NODE_ENV cleared so ambient production mode keeps devDependencies", async () => {
    process.env.NODE_ENV = "production";
    const sha = "d".repeat(40);
    const runCommand = createGitCheckoutRunCommand(sha);
    await expect(installGitPayload("paperclipai/paperclip", sha, runCommand, resolveInstallStorePaths())).resolves.toMatchObject({ version: "0.3.1", reused: false });
    const buildCalls = runCommand.mock.calls.filter(([file, args]) =>
      file === "bash" ||
      file === "corepack" ||
      (file === "npm" && args[0] === "pack") ||
      (file === process.execPath && args[0]?.endsWith("prepare-bundled-package.mjs")));
    expect(buildCalls).toHaveLength(9);
    for (const call of buildCalls) {
      const env = call[2]?.env;
      expect(env, `${call[0]} ${call[1].join(" ")} must run with an explicit env`).toBeDefined();
      expect(env, `${call[0]} ${call[1].join(" ")} must not inherit NODE_ENV`).not.toHaveProperty("NODE_ENV");
    }
    const uiPackCall = buildCalls.find(([file, , options]) => file === "corepack" && options?.env?.PAPERCLIP_RELEASE_REUSE_UI_DIST === "1");
    expect(uiPackCall).toBeDefined();
  });

  it("resolves the complete server workspace dependency closure in dependency order", () => {
    const checkout = path.join(root, "checkout");
    const packages = [
      { dir: "packages/shared", name: "@paperclipai/shared", dependencies: {} },
      { dir: "packages/db", name: "@paperclipai/db", dependencies: { "@paperclipai/shared": "workspace:*" } },
      { dir: "server", name: "@paperclipai/server", dependencies: { "@paperclipai/db": "workspace:*" } },
    ];
    fs.mkdirSync(path.join(checkout, "scripts"), { recursive: true });
    fs.writeFileSync(path.join(checkout, "scripts", "release-package-manifest.json"), JSON.stringify(packages.map(({ dir, name }) => ({ dir, name }))));
    for (const workspacePackage of packages) {
      fs.mkdirSync(path.join(checkout, workspacePackage.dir), { recursive: true });
      fs.writeFileSync(path.join(checkout, workspacePackage.dir, "package.json"), JSON.stringify({ name: workspacePackage.name, dependencies: workspacePackage.dependencies }));
    }

    expect(resolveGitInstallWorkspacePackages(checkout).map(({ name }) => name)).toEqual([
      "@paperclipai/shared",
      "@paperclipai/db",
      "@paperclipai/server",
    ]);
  });

  it("includes child-process stderr in command failures", async () => {
    await expect(runCommandWithDiagnostics(process.execPath, ["-e", "process.stderr.write('unsupported workspace dependency\\n'); process.exit(1)"]))
      .rejects.toThrow("unsupported workspace dependency");
  });

  it("installs through the shim, reports provenance, and uninstalls without deleting user data", async () => {
    const version = "2026.720.0";
    const runCommand = vi.fn(async (file: string, args: string[], _options?: unknown) => {
      if (file === "npm" && args[0] === "view") return { stdout: JSON.stringify(version), stderr: "" };
      if (file === "npm" && args[0] === "install") {
        const prefix = args[args.indexOf("--prefix") + 1];
        const entrypoint = path.join(prefix, "node_modules", "paperclipai", "dist", "index.js");
        fs.mkdirSync(path.dirname(entrypoint), { recursive: true });
        fs.writeFileSync(entrypoint, "#!/usr/bin/env node\n");
        return { stdout: "", stderr: "" };
      }
      if (file === process.execPath && args.at(-1) === "--version") {
        return { stdout: `${version}\n`, stderr: "" };
      }
      throw new Error(`Unexpected command: ${file} ${args.join(" ")}`);
    });

    await installCommand({}, { runCommand, now: () => new Date("2026-07-22T18:00:00.000Z") });

    const paths = resolveInstallStorePaths();
    const manifest = readInstallManifest(paths);
    expect(manifest?.version).toBe(version);
    expect(manifest?.channel).toBe("latest");
    expect(fs.realpathSync(paths.currentPath)).toBe(fs.realpathSync(manifest!.payloadPath));
    expect(fs.existsSync(paths.shimPath)).toBe(true);
    const installCall = runCommand.mock.calls.find(
      ([file, args]) => file === "npm" && args[0] === "install",
    );
    expect(installCall?.[1]).toContain("--@paperclipai:registry=https://registry.npmjs.org");
    const installOptions = installCall?.[2] as { env?: NodeJS.ProcessEnv } | undefined;
    expect(installOptions?.env?.npm_config_userconfig).toContain(".npmrc-");
    const entrypoint = path.join(manifest!.payloadPath, "node_modules", "paperclipai", "dist", "index.js");
    expect(resolveCliVersion(entrypoint)).toContain(`managed npm latest; payload ${manifest!.payloadPath}`);

    const userData = path.join(process.env.PAPERCLIP_HOME!, "instances", "default", "keep.txt");
    fs.mkdirSync(path.dirname(userData), { recursive: true });
    fs.writeFileSync(userData, "keep");
    const uninstallService = vi.fn(async () => {
      expect(fs.existsSync(paths.shimPath)).toBe(true);
    });
    await uninstallCommand({
      detectServiceManager: vi.fn(async () => ({
        supported: true as const,
        manager: {
          status: vi.fn(async () => ({ installed: true, active: true })),
          uninstall: uninstallService,
        } as never,
      })),
    });

    expect(uninstallService).toHaveBeenCalledOnce();
    expect(fs.existsSync(paths.cliRoot)).toBe(false);
    expect(fs.existsSync(paths.shimPath)).toBe(false);
    expect(fs.readFileSync(userData, "utf8")).toBe("keep");
  });

  it("refuses to remove the shared CLI while another instance service is installed", async () => {
    const paths = resolveInstallStorePaths();
    const otherUnitPath = path.join(process.env.HOME!, ".config", "systemd", "user", systemdServiceName("team-a"));
    fs.mkdirSync(path.dirname(otherUnitPath), { recursive: true });
    fs.writeFileSync(otherUnitPath, "unit");

    await expect(uninstallCommand({
      detectServiceManager: vi.fn(async () => ({
        supported: true as const,
        manager: { status: vi.fn(async () => ({ installed: false, active: false })) } as never,
      })),
      platform: "linux",
      userHomeDir: process.env.HOME!,
    })).rejects.toThrow("other instance services are installed");

    expect(fs.existsSync(paths.cliRoot)).toBe(false);
    expect(fs.existsSync(otherUnitPath)).toBe(true);
  });

  it("preserves the managed install when an existing systemd unit cannot be checked", async () => {
    const paths = resolveInstallStorePaths();
    fs.mkdirSync(path.dirname(paths.shimPath), { recursive: true });
    fs.writeFileSync(paths.shimPath, "managed shim");
    const unitPath = path.join(
      process.env.HOME!,
      ".config",
      "systemd",
      "user",
      systemdServiceName(resolvePaperclipInstanceId()),
    );
    fs.mkdirSync(path.dirname(unitPath), { recursive: true });
    fs.writeFileSync(unitPath, "unit");

    await expect(uninstallCommand({
      detectServiceManager: vi.fn(async () => ({
        supported: false as const,
        reason: "No usable systemd user manager was detected",
      })),
      platform: "linux",
      userHomeDir: process.env.HOME!,
    })).rejects.toThrow("Cannot verify or remove the background service");

    expect(fs.existsSync(paths.shimPath)).toBe(true);
    expect(fs.existsSync(unitPath)).toBe(true);
  });

  it("rejects a symlinked installs root before npm writes outside the store", async () => {
    const paths = resolveInstallStorePaths();
    const outside = path.join(root, "outside");
    fs.mkdirSync(paths.cliRoot, { recursive: true });
    fs.mkdirSync(outside);
    fs.symlinkSync(outside, paths.installsRoot, "dir");
    const runCommand = vi.fn(async () => ({ stdout: JSON.stringify("2026.720.0"), stderr: "" }));

    await expect(installCommand({}, { runCommand })).rejects.toThrow("non-directory install-store path");
    expect(runCommand).toHaveBeenCalledTimes(1);
    expect(fs.readdirSync(outside)).toEqual([]);
  });

  it("refuses to uninstall an unverified cli directory", async () => {
    const paths = resolveInstallStorePaths();
    const unrelatedFile = path.join(paths.cliRoot, "keep.txt");
    fs.mkdirSync(paths.cliRoot, { recursive: true });
    fs.writeFileSync(unrelatedFile, "keep");

    await expect(uninstallCommand()).rejects.toThrow("unverified install store");
    expect(fs.readFileSync(unrelatedFile, "utf8")).toBe("keep");
  });

  it("refuses to uninstall while another store mutation holds the lock", async () => {
    const paths = resolveInstallStorePaths();
    const payloadPath = payloadPathFor(paths, "npm", "2026.720.0");
    initializeInstallStore(paths);
    fs.mkdirSync(payloadPath, { recursive: true });
    flipCurrentAtomic(payloadPath, paths);
    writeInstallManifestAtomic({
      schemaVersion: INSTALL_MANIFEST_VERSION,
      source: "npm",
      version: "2026.720.0",
      channel: "latest",
      payloadPath,
      installedAt: "2026-07-22T18:00:00.000Z",
      previous: [],
    }, paths);

    await withInstallStoreLock(
      async () => {
        await expect(uninstallCommand()).rejects.toThrow("already running");
      },
      paths,
    );
    expect(fs.existsSync(paths.lockPath)).toBe(false);
  });

  it("refuses a symlinked git payload root before downloading", async () => {
    const paths = resolveInstallStorePaths(); initializeInstallStore(paths);
    const outside = path.join(root, "outside-git"); fs.mkdirSync(outside);
    fs.symlinkSync(outside, path.join(paths.installsRoot, "git"));
    const runCommand = vi.fn(async () => ({ stdout: "", stderr: "" }));
    await expect(installGitPayload("paperclipai/paperclip", "4".repeat(40), runCommand, paths)).rejects.toThrow("unsafe payload root");
    expect(runCommand).not.toHaveBeenCalled();
  });

});
