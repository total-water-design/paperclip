import fs from "node:fs";
import { createHash } from "node:crypto";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import * as p from "@clack/prompts";
import pc from "picocolors";
import { isSupportedNodeVersion, MINIMUM_NODE_VERSION } from "@paperclipai/shared/node-version";
import {
  addManagedPathBlock,
  assertManagedShimWritable,
  buildNextManifest,
  flipCurrentAtomic,
  payloadPathFor,
  pruneInstallPayloads,
  readInstallManifest,
  resolveInstallStorePaths,
  withInstallStoreLock,
  writeInstallManifestAtomic,
  writeManagedShim,
  createStagedGitIdentity,
  readStagedGitIdentity,
  writeStagedGitIdentity,
  type InstallChannel,
  type InstallRecord,
} from "../install-store.js";

const execFileAsync = promisify(execFile);
export const PUBLIC_NPM_REGISTRY = "https://registry.npmjs.org";
const DEFAULT_GITHUB_REPO = "paperclipai/paperclip";
const EXACT_VERSION_PATTERN = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
/**
 * Deliberately separate from general-purpose GitHub CLI credentials. Deployment
 * automation projects this value only into the non-activating source-staging
 * process when it needs to read a protected repository.
 */
export const GITHUB_SOURCE_TOKEN_ENV = "PAPERCLIP_GITHUB_SOURCE_TOKEN";
/**
 * A host-managed, credential-free source projection root. Each accepted
 * projection is addressed only by its full commit SHA and contains a bounded
 * `source.tar.gz` plus a matching `source.json` integrity descriptor.
 */
export const PROJECTED_SOURCE_ROOT_ENV = "PAPERCLIP_PROJECTED_SOURCE_ROOT";
const MAX_PROJECTED_SOURCE_BYTES = 512 * 1024 * 1024;

export type InstallOptions = { canary?: boolean; version?: string; ref?: string; repo?: string; yes?: boolean };
export type StageOptions = { ref?: string; repo?: string; yes?: boolean; json?: boolean; projectedSource?: boolean };
export type ActivateStagedOptions = { sha: string; authorityFile: string; json?: boolean };

export type CommandRunner = (
  file: string,
  args: string[],
  options?: Parameters<typeof execFileAsync>[2],
) => Promise<{ stdout: string; stderr: string }>;

type ReleasePackageEntry = { dir: string; name: string };

export async function runCommandWithDiagnostics(
  file: string,
  args: string[],
  options?: Parameters<typeof execFileAsync>[2],
): Promise<{ stdout: string; stderr: string }> {
  try {
    return await execFileAsync(file, args, { ...options, encoding: "utf8" });
  } catch (error) {
    const stderr = error && typeof error === "object" && "stderr" in error && typeof error.stderr === "string"
      ? error.stderr.trim()
      : "";
    if (!stderr || (error instanceof Error && error.message.includes(stderr))) throw error;
    throw new Error(`${error instanceof Error ? error.message : String(error)}\n${stderr}`, { cause: error });
  }
}

export function resolveGitInstallWorkspacePackages(checkoutPath: string): ReleasePackageEntry[] {
  const manifestPath = path.join(checkoutPath, "scripts", "release-package-manifest.json");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8")) as ReleasePackageEntry[];
  const packageByName = new Map(manifest.map((entry) => [entry.name, entry]));
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const ordered: ReleasePackageEntry[] = [];

  const visit = (packageName: string): void => {
    if (visited.has(packageName)) return;
    if (visiting.has(packageName)) throw new Error(`Circular workspace dependency while staging ${packageName}.`);
    const entry = packageByName.get(packageName);
    if (!entry) throw new Error(`Git install cannot stage workspace dependency ${packageName}; it is missing from scripts/release-package-manifest.json.`);
    visiting.add(packageName);
    const packageJson = JSON.parse(fs.readFileSync(path.join(checkoutPath, entry.dir, "package.json"), "utf8")) as Record<string, unknown>;
    for (const section of ["dependencies", "optionalDependencies", "peerDependencies"] as const) {
      const dependencies = packageJson[section];
      if (!dependencies || typeof dependencies !== "object") continue;
      for (const dependencyName of Object.keys(dependencies)) {
        if (dependencyName.startsWith("@paperclipai/")) visit(dependencyName);
      }
    }
    visiting.delete(packageName);
    visited.add(packageName);
    ordered.push(entry);
  };

  visit("@paperclipai/server");
  return ordered;
}

function assertSupportedNodeVersion(): void {
  if (!isSupportedNodeVersion(process.versions.node)) {
    throw new Error(`Managed installs require Node.js ${MINIMUM_NODE_VERSION} or newer (found ${process.version}).`);
  }
}

export function resolveNpmInstallRequest(options: InstallOptions): {
  spec: string;
  channel: InstallChannel;
} {
  if (options.canary && options.version) throw new Error("Choose either --canary or --version, not both.");
  if (options.version) {
    const version = options.version.trim();
    if (!EXACT_VERSION_PATTERN.test(version)) {
      throw new Error(`--version requires an exact published version, received '${options.version}'.`);
    }
    return { spec: version, channel: "pinned" };
  }
  return options.canary ? { spec: "canary", channel: "canary" } : { spec: "latest", channel: "latest" };
}

function parseResolvedVersion(stdout: string): string {
  const trimmed = stdout.trim();
  if (!trimmed) throw new Error("npm returned an empty version response.");
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (typeof parsed === "string") return parsed;
  } catch {
    if (EXACT_VERSION_PATTERN.test(trimmed)) return trimmed;
  }
  throw new Error(`npm returned an unexpected version response: ${trimmed}`);
}

export async function resolvePublishedVersion(spec: string, runCommand: CommandRunner): Promise<string> {
  const result = await runCommand(
    "npm",
    ["view", `paperclipai@${spec}`, "version", "--json", `--registry=${PUBLIC_NPM_REGISTRY}`],
    { maxBuffer: 1024 * 1024 },
  );
  return parseResolvedVersion(result.stdout);
}

export function resolveGitInstallRequest(options: InstallOptions): { repo: string; ref: string; pinned: boolean } | null {
  if (!options.ref && !options.repo) return null;
  if (!options.ref) throw new Error("--repo requires --ref.");
  if (options.canary || options.version) throw new Error("--ref cannot be combined with --canary or --version.");
  const repo = (options.repo ?? DEFAULT_GITHUB_REPO).trim();
  const ref = options.ref.trim();
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) throw new Error(`--repo must be an owner/name GitHub repository, received '${repo}'.`);
  if (!ref || ref.startsWith("-") || /[\0\r\n]/.test(ref)) throw new Error(`Invalid GitHub ref '${options.ref}'.`);
  return { repo, ref, pinned: /^[0-9a-f]{7,40}$/i.test(ref) };
}

async function runGitHubCurl(
  args: string[],
  runCommand: CommandRunner,
  options?: Parameters<CommandRunner>[2],
): Promise<{ stdout: string; stderr: string }> {
  // Anonymous GitHub requests are rate-limited per source IP (CI runners and
  // corporate NAT exhaust the shared quota); honor an ambient token when present.
  // The token travels via a curl --config file so it never appears in process args.
  const projectedSourceToken = process.env[GITHUB_SOURCE_TOKEN_ENV];
  if (projectedSourceToken !== undefined && !/^[A-Za-z0-9_-]+$/.test(projectedSourceToken)) {
    throw new Error(`${GITHUB_SOURCE_TOKEN_ENV} must contain only letters, digits, underscores, or hyphens.`);
  }
  // A projected staging token takes precedence. Retain GH_TOKEN/GITHUB_TOKEN
  // for backward-compatible interactive managed installs and updates.
  const token = projectedSourceToken || process.env.GH_TOKEN || process.env.GITHUB_TOKEN;
  if (!token) return runCommand("curl", args, options);
  const configDir = fs.mkdtempSync(path.join(os.tmpdir(), "paperclipai-gh-"));
  const configFile = path.join(configDir, "headers");
  try {
    fs.writeFileSync(configFile, `header = "Authorization: Bearer ${token}"\n`, { mode: 0o600 });
    return await runCommand("curl", ["--config", configFile, ...args], options);
  } finally {
    fs.rmSync(configDir, { recursive: true, force: true });
  }
}

export async function resolveGitHubRef(repo: string, ref: string, runCommand: CommandRunner): Promise<string> {
  const result = await runGitHubCurl(["--fail", "--silent", "--show-error", "--location", "--header", "Accept: application/vnd.github+json", "--header", "User-Agent: paperclipai-install", `https://api.github.com/repos/${repo}/commits/${encodeURIComponent(ref)}`], runCommand, { maxBuffer: 4 * 1024 * 1024 });
  let sha: unknown;
  try { sha = (JSON.parse(result.stdout) as { sha?: unknown }).sha; } catch { throw new Error(`GitHub returned an invalid response while resolving ${repo}@${ref}.`); }
  if (typeof sha !== "string" || !/^[0-9a-f]{40}$/i.test(sha)) throw new Error(`GitHub did not return a full commit SHA for ${repo}@${ref}.`);
  return sha.toLowerCase();
}

type ProjectedSourceDescriptor = {
  schemaVersion: 1;
  repo: string;
  sha: string;
  archiveSha256: string;
  sizeBytes: number;
};

function assertSafeProjectedPath(targetPath: string, label: string, expectedDirectory: boolean): fs.Stats {
  const stat = fs.lstatSync(targetPath);
  if (stat.isSymbolicLink() || (expectedDirectory ? !stat.isDirectory() : (!stat.isFile() || stat.nlink > 1))) {
    throw new Error(`Projected source ${label} is unsafe.`);
  }
  if ((stat.mode & 0o022) !== 0) throw new Error(`Projected source ${label} is writable by group or others.`);
  return stat;
}

/**
 * Resolve a host-projected archive without consulting GitHub or accepting an
 * arbitrary host path. The host must place this exact two-file projection at
 * `${PAPERCLIP_PROJECTED_SOURCE_ROOT}/${sha}` before the non-activating stage.
 */
export function resolveProjectedGitSource(repo: string, sha: string): string {
  const configuredRoot = process.env[PROJECTED_SOURCE_ROOT_ENV];
  if (!configuredRoot) throw new Error(`${PROJECTED_SOURCE_ROOT_ENV} is required with --projected-source.`);
  if (!path.isAbsolute(configuredRoot)) throw new Error(`${PROJECTED_SOURCE_ROOT_ENV} must be an absolute path.`);
  const root = path.resolve(configuredRoot);
  assertSafeProjectedPath(root, "root", true);
  const projection = path.join(root, sha);
  if (path.dirname(projection) !== root) throw new Error("Projected source SHA escapes the configured root.");
  assertSafeProjectedPath(projection, "directory", true);
  const descriptorPath = path.join(projection, "source.json");
  const archivePath = path.join(projection, "source.tar.gz");
  assertSafeProjectedPath(descriptorPath, "descriptor", false);
  const archiveStat = assertSafeProjectedPath(archivePath, "archive", false);
  if (archiveStat.size <= 0 || archiveStat.size > MAX_PROJECTED_SOURCE_BYTES) {
    throw new Error(`Projected source archive must be between 1 and ${MAX_PROJECTED_SOURCE_BYTES} bytes.`);
  }
  let descriptor: ProjectedSourceDescriptor;
  try { descriptor = JSON.parse(fs.readFileSync(descriptorPath, "utf8")) as ProjectedSourceDescriptor; }
  catch { throw new Error("Projected source descriptor is malformed."); }
  if (
    descriptor.schemaVersion !== 1 || descriptor.repo !== repo || descriptor.sha !== sha ||
    !/^[0-9a-f]{64}$/.test(descriptor.archiveSha256) || !Number.isSafeInteger(descriptor.sizeBytes) ||
    descriptor.sizeBytes !== archiveStat.size
  ) throw new Error("Projected source descriptor does not match the requested immutable candidate.");
  const archiveSha256 = createHash("sha256").update(fs.readFileSync(archivePath)).digest("hex");
  if (archiveSha256 !== descriptor.archiveSha256) throw new Error("Projected source archive SHA-256 does not match its descriptor.");
  return archivePath;
}

function payloadEntrypoint(payloadPath: string): string {
  return path.join(payloadPath, "node_modules", "paperclipai", "dist", "index.js");
}

export async function smokePayload(payloadPath: string, expectedVersion: string, runCommand: CommandRunner): Promise<void> {
  const entrypoint = payloadEntrypoint(payloadPath);
  if (!fs.existsSync(entrypoint)) throw new Error(`Installed package is missing its CLI entrypoint: ${entrypoint}`);
  const result = await runCommand(process.execPath, [entrypoint, "--version"], { maxBuffer: 1024 * 1024 });
  const reportedVersion = result.stdout.trim().split(/\s+/)[0];
  if (reportedVersion !== expectedVersion) {
    throw new Error(`Installed CLI smoke check reported ${reportedVersion || "no version"}; expected ${expectedVersion}.`);
  }
}

export async function installNpmPayload(
  version: string,
  runCommand: CommandRunner,
  paths = resolveInstallStorePaths(),
): Promise<{ payloadPath: string; reused: boolean }> {
  const payloadPath = payloadPathFor(paths, "npm", version);
  if (fs.existsSync(payloadPath)) {
    await smokePayload(payloadPath, version, runCommand);
    return { payloadPath, reused: true };
  }
  const sourceRoot = path.dirname(payloadPath);
  fs.mkdirSync(sourceRoot, { recursive: true, mode: 0o700 });
  const sourceStat = fs.lstatSync(sourceRoot);
  if (!sourceStat.isDirectory() || sourceStat.isSymbolicLink()) {
    throw new Error(`Refusing to install into unsafe payload root ${sourceRoot}.`);
  }
  fs.chmodSync(paths.cliRoot, 0o700);
  fs.chmodSync(paths.installsRoot, 0o700);
  fs.chmodSync(sourceRoot, 0o700);
  const stagingPath = path.join(sourceRoot, `.${version}.tmp-${process.pid}-${Date.now()}`);
  const npmUserConfigPath = path.join(sourceRoot, `.npmrc-${process.pid}-${Date.now()}`);
  fs.rmSync(stagingPath, { recursive: true, force: true });
  try {
    fs.writeFileSync(
      npmUserConfigPath,
      `registry=${PUBLIC_NPM_REGISTRY}\n@paperclipai:registry=${PUBLIC_NPM_REGISTRY}\n`,
      { mode: 0o600 },
    );
    await runCommand(
      "npm",
      [
        "install",
        "--prefix",
        stagingPath,
        `paperclipai@${version}`,
        `--registry=${PUBLIC_NPM_REGISTRY}`,
        `--@paperclipai:registry=${PUBLIC_NPM_REGISTRY}`,
        "--no-audit",
        "--no-fund",
      ],
      {
        cwd: sourceRoot,
        env: { ...process.env, npm_config_userconfig: npmUserConfigPath },
        maxBuffer: 16 * 1024 * 1024,
      },
    );
    await smokePayload(stagingPath, version, runCommand);
    fs.renameSync(stagingPath, payloadPath);
    return { payloadPath, reused: false };
  } finally {
    fs.rmSync(stagingPath, { recursive: true, force: true });
    fs.rmSync(npmUserConfigPath, { force: true });
  }
}

function gitBuildEnv(extra: NodeJS.ProcessEnv = {}): NodeJS.ProcessEnv {
  const env = { ...process.env, ...extra };
  // Source builds need devDependencies (esbuild, typescript); ambient NODE_ENV=production
  // makes pnpm/npm omit them, so the checkout build must not inherit it.
  delete env.NODE_ENV;
  return env;
}

export async function installGitPayload(repo: string, sha: string, runCommand: CommandRunner, paths = resolveInstallStorePaths(), sourceArchivePath?: string): Promise<{ payloadPath: string; reused: boolean; version: string }> {
  const identifier = sha.slice(0, 12);
  const payloadPath = payloadPathFor(paths, "git", identifier);
  if (fs.existsSync(payloadPath)) {
    const metadata = JSON.parse(fs.readFileSync(path.join(payloadPath, "node_modules", "paperclipai", "package.json"), "utf8")) as { version: string };
    await smokePayload(payloadPath, metadata.version, runCommand);
    return { payloadPath, reused: true, version: metadata.version };
  }
  const sourceRoot = path.dirname(payloadPath);
  fs.mkdirSync(sourceRoot, { recursive: true, mode: 0o700 });
  const sourceStat = fs.lstatSync(sourceRoot);
  if (!sourceStat.isDirectory() || sourceStat.isSymbolicLink()) {
    throw new Error(`Refusing to install into unsafe payload root ${sourceRoot}.`);
  }
  fs.chmodSync(paths.cliRoot, 0o700);
  fs.chmodSync(paths.installsRoot, 0o700);
  fs.chmodSync(sourceRoot, 0o700);
  const stagingRoot = path.join(sourceRoot, `.${identifier}.tmp-${process.pid}-${Date.now()}`);
  const checkoutPath = path.join(stagingRoot, "source");
  const archivePath = path.join(stagingRoot, "source.tar.gz");
  const stagedPayload = path.join(stagingRoot, "payload");
  fs.rmSync(stagingRoot, { recursive: true, force: true });
  fs.mkdirSync(checkoutPath, { recursive: true, mode: 0o700 });
  // Workspace build scripts invoke bare `pnpm`; on a machine where pnpm exists only
  // through corepack, nothing puts it on PATH, so provision a shim into the staging dir.
  const pnpmShimDir = path.join(stagingRoot, "pnpm-bin");
  fs.mkdirSync(pnpmShimDir, { recursive: true, mode: 0o700 });
  const buildEnv = (extra: NodeJS.ProcessEnv = {}) =>
    gitBuildEnv({ PATH: [pnpmShimDir, process.env.PATH].filter(Boolean).join(path.delimiter), ...extra });
  try {
    if (sourceArchivePath) fs.copyFileSync(sourceArchivePath, archivePath, fs.constants.COPYFILE_EXCL);
    else await runGitHubCurl(["--fail", "--silent", "--show-error", "--location", "--output", archivePath, `https://codeload.github.com/${repo}/tar.gz/${sha}`], runCommand, { maxBuffer: 4 * 1024 * 1024 });
    await runCommand("tar", ["-xzf", archivePath, "--strip-components=1", "-C", checkoutPath], { maxBuffer: 4 * 1024 * 1024 });
    await runCommand("corepack", ["enable", "pnpm", "--install-directory", pnpmShimDir], { cwd: checkoutPath, env: buildEnv(), maxBuffer: 4 * 1024 * 1024 });
    await runCommand("corepack", ["pnpm", "install", "--frozen-lockfile"], { cwd: checkoutPath, env: buildEnv(), maxBuffer: 32 * 1024 * 1024 });
    await runCommand("bash", ["scripts/build-npm.sh", "--skip-checks", "--skip-typecheck"], { cwd: checkoutPath, env: buildEnv(), maxBuffer: 32 * 1024 * 1024 });
    await runCommand("corepack", ["pnpm", "-r", "--filter", "@paperclipai/server...", "--if-present", "run", "build"], { cwd: checkoutPath, env: buildEnv(), maxBuffer: 32 * 1024 * 1024 });
    const metadata = JSON.parse(fs.readFileSync(path.join(checkoutPath, "cli", "package.json"), "utf8")) as { version: string };
    const workspacePackages = resolveGitInstallWorkspacePackages(checkoutPath);
    for (const [index, workspacePackage] of workspacePackages.entries()) {
      const packageDir = path.join(checkoutPath, workspacePackage.dir);
      const packageJson = JSON.parse(fs.readFileSync(path.join(packageDir, "package.json"), "utf8")) as { bundleDependencies?: string[]; bundledDependencies?: string[] };
      const bundledDependencies = packageJson.bundleDependencies ?? packageJson.bundledDependencies ?? [];
      if (bundledDependencies.length > 0) {
        const stagedPackage = path.join(stagingRoot, `workspace-package-${index}`);
        await runCommand(process.execPath, [path.join(checkoutPath, "scripts", "prepare-bundled-package.mjs"), packageDir, stagedPackage], { cwd: checkoutPath, env: buildEnv(), maxBuffer: 32 * 1024 * 1024 });
        await runCommand("npm", ["pack", stagedPackage, "--pack-destination", stagingRoot], { cwd: checkoutPath, env: buildEnv(), maxBuffer: 16 * 1024 * 1024 });
      } else {
        await runCommand("corepack", ["pnpm", "--dir", workspacePackage.dir, "pack", "--pack-destination", stagingRoot], { cwd: checkoutPath, env: buildEnv({ PAPERCLIP_RELEASE_REUSE_UI_DIST: "1" }), maxBuffer: 32 * 1024 * 1024 });
      }
    }
    await runCommand("npm", ["pack", "--pack-destination", stagingRoot], { cwd: path.join(checkoutPath, "cli"), env: buildEnv(), maxBuffer: 16 * 1024 * 1024 });
    const tarballs = fs.readdirSync(stagingRoot).filter((entry) => entry.endsWith(".tgz"));
    const cliTarball = tarballs.find((entry) => entry === `paperclipai-${metadata.version}.tgz`);
    const workspaceTarballs = tarballs.filter((entry) => entry !== cliTarball);
    if (!cliTarball || workspaceTarballs.length !== workspacePackages.length) {
      throw new Error(`Git install packaging produced ${workspaceTarballs.length} workspace tarballs; expected ${workspacePackages.length}.`);
    }
    await runCommand("npm", ["install", "--prefix", stagedPayload, path.join(stagingRoot, cliTarball), ...workspaceTarballs.map((entry) => path.join(stagingRoot, entry)), "--no-audit", "--no-fund"], { cwd: stagingRoot, maxBuffer: 32 * 1024 * 1024 });
    await smokePayload(stagedPayload, metadata.version, runCommand);
    fs.renameSync(stagedPayload, payloadPath);
    return { payloadPath, reused: false, version: metadata.version };
  } finally { fs.rmSync(stagingRoot, { recursive: true, force: true }); }
}

function pathContains(directory: string): boolean {
  const normalized = path.resolve(directory);
  return (process.env.PATH ?? "").split(path.delimiter).filter(Boolean).some((entry) => path.resolve(entry) === normalized);
}

function shellRcPath(): string | null {
  const home = process.env.HOME;
  if (!home) return null;
  const shell = path.basename(process.env.SHELL ?? "");
  if (shell === "bash") return path.join(home, ".bashrc");
  if (shell === "zsh") return path.join(home, ".zshrc");
  return null;
}

async function ensureShimOnPath(options: InstallOptions): Promise<void> {
  const paths = resolveInstallStorePaths();
  const binDir = path.dirname(paths.shimPath);
  if (pathContains(binDir)) return;
  const manualInstruction = `export PATH="$HOME/.local/bin:$PATH"`;
  const rcPath = shellRcPath();
  if (!process.stdin.isTTY || !process.stdout.isTTY || !rcPath) {
    console.log(pc.yellow(`Add Paperclip to PATH for this shell:\n  ${manualInstruction}`));
    return;
  }
  const confirmed = options.yes === true ? true : await p.confirm({ message: `Add ~/.local/bin to PATH in ${rcPath}?`, initialValue: true });
  if (p.isCancel(confirmed) || !confirmed) {
    console.log(pc.yellow(`PATH was not changed. Run:\n  ${manualInstruction}`));
    return;
  }
  const changed = addManagedPathBlock(rcPath);
  console.log(changed ? pc.green(`Updated ${rcPath}.`) : pc.dim(`${rcPath} already contains the PATH block.`));
}

async function confirmGitInstall(options: InstallOptions, repo: string, ref: string): Promise<void> {
  const warning = `Installing ${repo}@${ref} executes dependency and build scripts from that repository.`;
  console.log(pc.yellow(`Warning: ${warning}`));
  if (options.yes === true) return;
  if (!process.stdin.isTTY || !process.stdout.isTTY) {
    throw new Error(`${warning} Re-run with --yes to consent in non-interactive environments.`);
  }
  const confirmed = await p.confirm({
    message: `${warning} Continue?`,
    initialValue: false,
  });
  if (p.isCancel(confirmed) || !confirmed) {
    throw new Error("Git-ref install cancelled before downloading or executing repository code.");
  }
}

export async function installCommand(
  options: InstallOptions,
  dependencies: { runCommand?: CommandRunner; now?: () => Date } = {},
): Promise<void> {
  assertSupportedNodeVersion();
  const runCommand = dependencies.runCommand ?? runCommandWithDiagnostics;
  const gitRequest = resolveGitInstallRequest(options);
  if (gitRequest) {
    await confirmGitInstall(options, gitRequest.repo, gitRequest.ref);
    const sha = await resolveGitHubRef(gitRequest.repo, gitRequest.ref, runCommand);
    const paths = resolveInstallStorePaths();
    const installed = await withInstallStoreLock(async () => {
      assertManagedShimWritable(paths);
      const currentManifest = readInstallManifest(paths);
      const payload = await installGitPayload(gitRequest.repo, sha, runCommand, paths);
      const record: InstallRecord = { source: "git", version: payload.version, channel: "pinned", repo: gitRequest.repo, ref: gitRequest.ref, sha, payloadPath: payload.payloadPath, installedAt: (dependencies.now?.() ?? new Date()).toISOString() };
      const nextManifest = buildNextManifest(record, currentManifest);
      const oldTarget = fs.existsSync(paths.currentPath) ? fs.readlinkSync(paths.currentPath) : null;
      flipCurrentAtomic(payload.payloadPath, paths);
      try { writeInstallManifestAtomic(nextManifest, paths); } catch (error) { if (oldTarget) flipCurrentAtomic(path.resolve(paths.cliRoot, oldTarget), paths); else fs.rmSync(paths.currentPath, { force: true }); throw error; }
      writeManagedShim(paths); pruneInstallPayloads(nextManifest, paths); return payload;
    }, paths);
    await ensureShimOnPath(options);
    console.log(pc.green(`${installed.reused ? "Activated cached" : "Installed"} paperclipai git payload ${sha.slice(0, 12)}.`));
    return;
  }
  const request = resolveNpmInstallRequest(options);
  console.log(`Resolving paperclipai@${request.spec} from ${PUBLIC_NPM_REGISTRY}...`);
  const version = await resolvePublishedVersion(request.spec, runCommand);
  console.log(`Installing paperclipai@${version}...`);

  const paths = resolveInstallStorePaths();
  const installed = await withInstallStoreLock(async () => {
    assertManagedShimWritable(paths);
    const currentManifest = readInstallManifest(paths);
    const payload = await installNpmPayload(version, runCommand, paths);
    const record: InstallRecord = {
      source: "npm",
      version,
      channel: request.channel,
      payloadPath: payload.payloadPath,
      installedAt: (dependencies.now?.() ?? new Date()).toISOString(),
    };
    const nextManifest = buildNextManifest(record, currentManifest);
    const oldTarget = fs.existsSync(paths.currentPath) ? fs.readlinkSync(paths.currentPath) : null;
    flipCurrentAtomic(payload.payloadPath, paths);
    try {
      writeInstallManifestAtomic(nextManifest, paths);
    } catch (error) {
      if (oldTarget) flipCurrentAtomic(path.resolve(paths.cliRoot, oldTarget), paths);
      else fs.rmSync(paths.currentPath, { force: true });
      throw error;
    }
    writeManagedShim(paths);
    pruneInstallPayloads(nextManifest, paths);
    return payload;
  }, paths);
  await ensureShimOnPath(options);

  console.log(pc.green(`${installed.reused ? "Activated cached" : "Installed"} paperclipai ${version} (${request.channel}).`));
  console.log(pc.dim(`Payload: ${installed.payloadPath}`));
  console.log(`Run ${pc.cyan("paperclipai --version")} to verify the managed install.`);
}

function authorityValue(contents: string, key: string): string | null {
  const match = contents.match(new RegExp(`^${key}=([^\\r\\n]*)$`, "m"));
  return match?.[1] ?? null;
}

function assertAuthorityMatches(identity: ReturnType<typeof readStagedGitIdentity>, authorityFile: string): void {
  const stat = fs.lstatSync(authorityFile);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error("Activation authority must be a regular non-symlink file.");
  const contents = fs.readFileSync(authorityFile, "utf8");
  const expected: Record<string, string> = {
    AUTHORIZED_SHA: identity.sha,
    AUTHORIZED_PAYLOAD: identity.payloadPath,
    AUTHORIZED_MANIFEST_SHA256: identity.manifestSha256,
    AUTHORIZED_ENTRYPOINT_SHA256: identity.entrypointSha256,
    AUTHORIZED_ADAPTER_BRIDGE_SHA256: identity.adapterBridgeSha256,
    AUTHORIZED_SERVER_ROUTE_SHA256: identity.serverRouteSha256,
  };
  for (const [key, value] of Object.entries(expected)) {
    if (authorityValue(contents, key) !== value) throw new Error(`Activation authority does not match staged identity field ${key}.`);
  }
}

/** Stage a full-SHA Git candidate without changing current, install.json, shim, authority, or service state. */
export async function stageGitCommand(options: StageOptions, dependencies: { runCommand?: CommandRunner; now?: () => Date } = {}): Promise<void> {
  assertSupportedNodeVersion();
  const request = resolveGitInstallRequest(options);
  if (!request) throw new Error("Staging requires --ref <exact-commit-sha>.");
  if (!request.pinned || request.ref.length !== 40) throw new Error("Staging requires --ref to be an exact full 40-character commit SHA.");
  await confirmGitInstall(options, request.repo, request.ref);
  const runCommand = dependencies.runCommand ?? runCommandWithDiagnostics;
  const sha = request.ref.toLowerCase();
  const projectedArchive = options.projectedSource ? resolveProjectedGitSource(request.repo, sha) : undefined;
  if (!projectedArchive) {
    const resolvedSha = await resolveGitHubRef(request.repo, request.ref, runCommand);
    if (resolvedSha !== sha) throw new Error("Resolved GitHub commit differs from the requested exact SHA.");
  }
  const paths = resolveInstallStorePaths();
  const result = await withInstallStoreLock(async () => {
    const payload = await installGitPayload(request.repo, sha, runCommand, paths, projectedArchive);
    const identity = createStagedGitIdentity({ source: "git", sha, repo: request.repo, ref: request.ref, version: payload.version, payloadPath: payload.payloadPath, stagedAt: (dependencies.now?.() ?? new Date()).toISOString() }, paths);
    const identityPath = writeStagedGitIdentity(identity, paths);
    return { identity, identityPath, reused: payload.reused };
  }, paths);
  const authorityInput = [
    `AUTHORIZED_SHA=${result.identity.sha}`,
    `AUTHORIZED_PAYLOAD=${result.identity.payloadPath}`,
    `AUTHORIZED_MANIFEST_SHA256=${result.identity.manifestSha256}`,
    `AUTHORIZED_ENTRYPOINT_SHA256=${result.identity.entrypointSha256}`,
    `AUTHORIZED_ADAPTER_BRIDGE_SHA256=${result.identity.adapterBridgeSha256}`,
    `AUTHORIZED_SERVER_ROUTE_SHA256=${result.identity.serverRouteSha256}`,
  ].join("\n");
  const output = { staged: true, identityPath: result.identityPath, identity: result.identity, authorityInput };
  console.log(options.json ? JSON.stringify(output) : `${result.reused ? "Verified cached" : "Staged"} Git payload ${sha}.\nIdentity: ${result.identityPath}\n\nGuard authority input:\n${authorityInput}`);
}

/**
 * Commit an already-authorized staged identity. The authority is read-only and
 * must match every executable identity before `current` can move. Any manifest
 * write failure restores the prior current payload, leaving the service guard
 * able to start only the already-authorized payload.
 */
export async function activateStagedGitCommand(options: ActivateStagedOptions): Promise<void> {
  const sha = options.sha.toLowerCase();
  const paths = resolveInstallStorePaths();
  const result = await withInstallStoreLock(async () => {
    const identity = readStagedGitIdentity(sha, paths);
    assertAuthorityMatches(identity, path.resolve(options.authorityFile));
    const active = readInstallManifest(paths);
    if (!active || !fs.existsSync(paths.currentPath) || fs.realpathSync(paths.currentPath) !== fs.realpathSync(active.payloadPath)) {
      throw new Error("Refusing staged activation without a verified active rollback payload.");
    }
    const oldTarget = fs.readlinkSync(paths.currentPath);
    const next = buildNextManifest({ source: "git", version: identity.version, channel: "pinned", repo: identity.repo, ref: identity.ref, sha: identity.sha, payloadPath: identity.payloadPath, installedAt: identity.stagedAt }, active);
    const recomputed = createStagedGitIdentity({ ...identity, source: "git" }, paths);
    for (const field of ["manifestSha256", "entrypointSha256", "adapterBridgeSha256", "serverRouteSha256"] as const) {
      if (recomputed[field] !== identity[field]) throw new Error(`Staged identity no longer matches ${field}.`);
    }
    flipCurrentAtomic(identity.payloadPath, paths);
    try { writeInstallManifestAtomic(next, paths); } catch (error) { flipCurrentAtomic(path.resolve(paths.cliRoot, oldTarget), paths); throw error; }
    return { payloadPath: identity.payloadPath, sha: identity.sha };
  }, paths);
  console.log(options.json ? JSON.stringify({ activated: true, ...result }) : `Activated staged Git payload ${result.sha} at ${result.payloadPath}.`);
}
