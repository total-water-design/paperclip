#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, statSync } from "node:fs";
import { builtinModules } from "node:module";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const PACKAGE_ROOT = "package";
const STATIC_IMPORT = /^\s*import\s+(?:.*\sfrom\s+)?["']([^"']+)["']/;
const CALL_IMPORT = /\b(?:import|require)\(\s*(["'])([^"']+)\1\s*\)/g;
const BUILTIN_MODULES = new Set(builtinModules.map((name) => name.replace(/^node:/, "")));

function fail(message) {
  throw new Error(`certified payload: ${message}`);
}

function isRuntimeModule(specifier) {
  return !specifier.startsWith(".") && !specifier.startsWith("/") && !specifier.startsWith("node:") && !BUILTIN_MODULES.has(specifier) && !specifier.startsWith("@embedded-postgres/") && !specifier.startsWith("@paperclipai/plugin-sdk/");
}

// This reads executable import/require syntax, never manifest declarations.
// It captures each static external module edge Node must resolve after extract.
export function collectRuntimeModules(source) {
  const modules = new Set();
  for (const line of source.split("\n")) {
    const match = line.match(STATIC_IMPORT);
    if (match && isRuntimeModule(match[1])) modules.add(match[1]);
  }
  for (const match of source.matchAll(CALL_IMPORT)) {
    if (isRuntimeModule(match[2])) modules.add(match[2]);
  }
  return [...modules].sort();
}

function cleanEnvironment() {
  return { PATH: process.env.PATH ?? "", HOME: "", NODE_PATH: "", npm_config_userconfig: "/dev/null" };
}

function resolveRuntimeModules(entryPath, modules) {
  const resolver = [
    'import { pathToFileURL } from "node:url";',
    'const [entry, encoded] = process.argv.slice(1);',
    'const parent = pathToFileURL(entry).href;',
    'for (const specifier of JSON.parse(encoded)) await import.meta.resolve(specifier, parent);',
  ].join(" ");
  try {
    execFileSync(process.execPath, ["--input-type=module", "--eval", resolver, entryPath, JSON.stringify(modules)], {
      cwd: resolve(entryPath, "..", ".."), env: cleanEnvironment(), stdio: "pipe",
    });
  } catch (error) {
    const detail = Buffer.isBuffer(error.stderr) ? error.stderr.toString("utf8").trim() : "";
    fail(`extracted runtime module resolution failed${detail ? `: ${detail}` : ""}`);
  }
}

function executeHelp(entryPath) {
  try {
    execFileSync(process.execPath, [entryPath, "--help"], {
      cwd: resolve(entryPath, "..", ".."), env: cleanEnvironment(), stdio: "pipe", timeout: 15_000,
    });
  } catch (error) {
    const detail = Buffer.isBuffer(error.stderr) ? error.stderr.toString("utf8").trim() : "";
    fail(`extracted --help execution failed${detail ? `: ${detail}` : ""}`);
  }
}

export function verifyExtractedConsumer(extractedRoot) {
  const packageRoot = resolve(extractedRoot, PACKAGE_ROOT);
  const manifestPath = join(packageRoot, "package.json");
  const entryPath = join(packageRoot, "dist", "index.js");
  try { JSON.parse(readFileSync(manifestPath, "utf8")); } catch { fail("extracted consumer has no readable package/package.json"); }
  try { statSync(entryPath); } catch { fail("extracted consumer has no dist/index.js entrypoint"); }
  const runtimeModules = collectRuntimeModules(readFileSync(entryPath, "utf8"));
  resolveRuntimeModules(entryPath, runtimeModules);
  executeHelp(entryPath);
  return { entryPath: "package/dist/index.js", runtimeModules };
}

export function verifyArchive(archivePath) {
  const extractRoot = mkdtempSync(join(tmpdir(), "paperclip-certified-payload-"));
  try {
    execFileSync("tar", ["-xzf", archivePath, "-C", extractRoot], { stdio: "pipe" });
    return verifyExtractedConsumer(extractRoot);
  } finally {
    rmSync(extractRoot, { recursive: true, force: true });
  }
}

function readArchiveArg(argv) {
  const index = argv.indexOf("--archive");
  if (index === -1 || !argv[index + 1]) fail("usage: verify-certified-npm-payload.mjs --archive PATH");
  return resolve(argv[index + 1]);
}

if (process.argv[1] === new URL(import.meta.url).pathname) {
  try {
    const result = verifyArchive(readArchiveArg(process.argv.slice(2)));
    console.log(`certified payload: extracted runtime resolved (${result.runtimeModules.join(", ") || "bundled"}) and --help passed`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
