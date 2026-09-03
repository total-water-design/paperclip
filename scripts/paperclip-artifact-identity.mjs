#!/usr/bin/env node

import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const FORMAT = "paperclip-artifact-certification/v1";
const IDENTITY_NAME = "paperclip-artifact-identity.json";

function fail(message) {
  throw new Error(`artifact identity: ${message}`);
}

export function sha256File(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function git(repo, args) {
  return execFileSync("git", ["-C", repo, ...args], { encoding: "utf8" }).trim();
}

export function assertCertifiedSource(repo, claimedSourceSha) {
  const sourceSha = git(repo, ["rev-parse", "HEAD"]);
  if (!/^[0-9a-f]{40}$/.test(claimedSourceSha ?? "")) fail("source label must be an exact full Git SHA");
  if (claimedSourceSha !== sourceSha) fail(`source label mismatch: claimed ${claimedSourceSha}, checkout ${sourceSha}`);
  const dirty = git(repo, ["status", "--porcelain", "--untracked-files=normal"]);
  if (dirty) fail(`source tree is dirty:\n${dirty}`);
  return sourceSha;
}

function filesUnder(root, current = root) {
  const result = [];
  for (const name of readdirSync(current).sort()) {
    if (name === IDENTITY_NAME) continue;
    const path = resolve(current, name);
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) fail(`generated output contains symlink: ${relative(root, path)}`);
    if (stat.isDirectory()) result.push(...filesUnder(root, path));
    else if (stat.isFile()) result.push(path);
  }
  return result;
}

export function digestTree(root) {
  const entries = filesUnder(root).map((path) => ({
    path: relative(root, path).split("\\").join("/"),
    sha256: sha256File(path),
    size: lstatSync(path).size,
  }));
  const digest = createHash("sha256");
  for (const entry of entries) digest.update(`${entry.path}\0${entry.size}\0${entry.sha256}\n`);
  return { sha256: digest.digest("hex"), entries };
}

function stableJson(value) {
  if (Array.isArray(value)) return value.map(stableJson);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableJson(value[key])]));
  }
  return value;
}

function writeJson(path, value) {
  mkdirSync(resolve(path, ".."), { recursive: true });
  writeFileSync(path, `${JSON.stringify(stableJson(value), null, 2)}\n`);
}

export function createIdentity({ repo, outputDir, sourceSha, canonicalBuildCommand }) {
  const exactSha = assertCertifiedSource(repo, sourceSha);
  const lockPath = resolve(repo, "pnpm-lock.yaml");
  const output = digestTree(outputDir);
  const identity = {
    format: FORMAT,
    source: { sha: exactSha, clean: true },
    toolchain: {
      node: process.version,
      pnpm: execFileSync("corepack", ["pnpm", "--version"], { encoding: "utf8" }).trim(),
    },
    lockfile: { path: "pnpm-lock.yaml", sha256: sha256File(lockPath) },
    build: { command: canonicalBuildCommand },
    generatedOutput: output,
  };
  writeJson(resolve(outputDir, IDENTITY_NAME), identity);
  return identity;
}

export function createCertification({ identityPath, archivePath, executablePath, outputPath }) {
  const identity = JSON.parse(readFileSync(identityPath, "utf8"));
  if (identity.format !== FORMAT) fail("unsupported embedded identity format");
  const certification = {
    ...identity,
    archive: { name: basename(archivePath), sha256: sha256File(archivePath), size: lstatSync(archivePath).size },
    installedExecutable: { path: "dist/index.js", sha256: sha256File(executablePath) },
  };
  writeJson(outputPath, certification);
  return certification;
}

export function verifyActivation({ manifestPath, identityPath, executablePath, archivePath, runtimeIdentityPath }) {
  const certified = JSON.parse(readFileSync(manifestPath, "utf8"));
  const installed = JSON.parse(readFileSync(identityPath, "utf8"));
  if (certified.format !== FORMAT || installed.format !== FORMAT) fail("unsupported identity format");
  if (JSON.stringify(stableJson(installed)) !== JSON.stringify(stableJson({
    format: certified.format, source: certified.source, toolchain: certified.toolchain,
    lockfile: certified.lockfile, build: certified.build, generatedOutput: certified.generatedOutput,
  }))) fail("installed/generated bundle identity differs from certification manifest");
  if (sha256File(executablePath) !== certified.installedExecutable.sha256) fail("installed executable digest differs from certification manifest");
  if (archivePath && sha256File(archivePath) !== certified.archive.sha256) fail("archive digest differs from certification manifest");
  if (runtimeIdentityPath) {
    const runtime = JSON.parse(readFileSync(runtimeIdentityPath, "utf8"));
    if (runtime.sourceSha !== certified.source.sha || runtime.executableSha256 !== certified.installedExecutable.sha256) {
      fail(`stale runtime identity: running ${runtime.sourceSha ?? "unknown"}/${runtime.executableSha256 ?? "unknown"}, certified ${certified.source.sha}/${certified.installedExecutable.sha256}`);
    }
  }
  return certified;
}

function args(argv) {
  const result = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    if (!argv[i].startsWith("--")) result._.push(argv[i]);
    else result[argv[i].slice(2)] = argv[++i];
  }
  return result;
}

function required(options, name) {
  if (!options[name]) fail(`missing --${name}`);
  return resolve(options[name]);
}

function main() {
  const options = args(process.argv.slice(2));
  const command = options._[0];
  if (command === "identity") {
    createIdentity({ repo: required(options, "repo"), outputDir: required(options, "output-dir"), sourceSha: options["source-sha"], canonicalBuildCommand: options["build-command"] ?? "corepack pnpm build:npm:certified" });
  } else if (command === "certify") {
    createCertification({ identityPath: required(options, "identity"), archivePath: required(options, "archive"), executablePath: required(options, "executable"), outputPath: required(options, "manifest") });
  } else if (command === "preflight") {
    verifyActivation({ manifestPath: required(options, "manifest"), identityPath: required(options, "identity"), executablePath: required(options, "executable"), archivePath: options.archive ? resolve(options.archive) : null, runtimeIdentityPath: options["runtime-identity"] ? resolve(options["runtime-identity"]) : null });
    console.log("artifact identity: activation preflight passed");
  } else fail("usage: identity|certify|preflight [options]");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try { main(); } catch (error) { console.error(error.message); process.exit(1); }
}
