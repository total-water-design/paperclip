#!/usr/bin/env node
/**
 * generate-npm-package-json.mjs
 *
 * Reads the dev package.json (which has workspace:* refs) and produces
 * a publishable package.json in cli/ with:
 *   - workspace:* dependencies removed
 *   - all external dependencies from workspace packages inlined
 *   - proper metadata for npm
 *
 * Reads from cli/package.dev.json if it exists (build already ran),
 * otherwise from cli/package.json.
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..");

function readPkg(relativePath) {
  return JSON.parse(readFileSync(resolve(repoRoot, relativePath, "package.json"), "utf8"));
}

// Read all workspace packages that are BUNDLED into the CLI.
// Note: "server" is excluded — it's published separately as a dependency.
const workspacePaths = [
  "cli",
  "packages/db",
  "packages/shared",
  "packages/adapter-utils",
  "packages/adapters/claude-local",
  "packages/adapters/codex-local",
  "packages/adapters/hermes-gateway",
  "packages/adapters/hermes",
  "packages/adapters/opencode-local",
  "packages/adapters/openclaw-gateway",
  "packages/plugins/sdk",
];

// The certified CLI bundles its complete JavaScript runtime closure.  The
// publish manifest must not imply an install/network fallback for dependencies
// that are already embedded in dist/index.js.
const externalWorkspacePackages = new Set();

// Collect all external dependencies from all workspace packages
const allDeps = {};

for (const pkgPath of workspacePaths) {
  const pkg = readPkg(pkgPath);
  const deps = pkg.dependencies || {};

  for (const [name, version] of Object.entries(deps)) {
    if (!externalWorkspacePackages.has(name)) continue;
    // For external workspace packages, read their version directly
    if (externalWorkspacePackages.has(name)) {
      const pkgDirMap = { "@paperclipai/server": "server" };
      const wsPkg = readPkg(pkgDirMap[name]);
      allDeps[name] = wsPkg.version;
      continue;
    }
    // Keep the more specific (pinned) version if conflict
    if (!allDeps[name] || !version.startsWith("^")) {
      allDeps[name] = version;
    }
  }

}

// Sort alphabetically.
const sortedDeps = Object.fromEntries(Object.entries(allDeps).sort(([a], [b]) => a.localeCompare(b)));

// Read the CLI package metadata — prefer the dev backup if it exists
const devPkgPath = resolve(repoRoot, "cli/package.dev.json");
const cliPkg = existsSync(devPkgPath)
  ? JSON.parse(readFileSync(devPkgPath, "utf8"))
  : readPkg("cli");

// Build the publishable package.json
const publishPkg = {
  name: cliPkg.name,
  version: cliPkg.version,
  description: cliPkg.description,
  type: cliPkg.type,
  bin: cliPkg.bin,
  keywords: cliPkg.keywords,
  license: cliPkg.license,
  repository: cliPkg.repository,
  homepage: cliPkg.homepage,
  bugs: cliPkg.bugs,
  files: cliPkg.files,
  engines: { node: ">=24.11.0" },
  dependencies: sortedDeps,
};

const output = JSON.stringify(publishPkg, null, 2) + "\n";
const outPath = resolve(repoRoot, "cli/package.json");
writeFileSync(outPath, output);

console.log(`  ✓  Generated publishable package.json (${Object.keys(sortedDeps).length} deps)`);
console.log(`     Version: ${cliPkg.version}`);
