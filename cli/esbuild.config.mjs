/**
 * esbuild configuration for building the paperclipai CLI for npm.
 *
 * Bundles all workspace packages (@paperclipai/*) into a single file.
 * External npm packages remain as regular dependencies.
 */

import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..");

// Workspace packages whose code should be bundled into the CLI.
// Note: "server" is excluded — it's published separately and resolved at runtime.
const workspacePaths = [
  "cli",
  "packages/db",
  "packages/shared",
  "packages/adapter-utils",
  "packages/adapters/claude-local",
  "packages/adapters/codex-local",
  "packages/adapters/cursor-cloud",
  "packages/adapters/cursor-local",
  "packages/adapters/gemini-local",
  "packages/adapters/grok-local",
  "packages/adapters/hermes-gateway",
  "packages/adapters/hermes",
  "packages/adapters/kimi-local",
  "packages/adapters/opencode-local",
  "packages/adapters/openclaw-gateway",
  "packages/adapters/pi-local",
  "packages/plugins/sdk",
];

// Certified payloads must execute after a clean extraction with no package
// manager, registry, credentials, or inherited workspace node_modules. Keep
// the CLI's complete JavaScript dependency closure in the bundle instead of
// leaving either workspace or registry packages for Node to resolve later.
const externalWorkspacePackages = new Set();
const externals = new Set();
for (const p of workspacePaths) {
  const pkg = JSON.parse(readFileSync(resolve(repoRoot, p, "package.json"), "utf8"));
  for (const name of Object.keys(pkg.dependencies || {})) {
    if (externalWorkspacePackages.has(name)) externals.add(name);
  }
}
// Also add all published workspace packages as external
for (const name of externalWorkspacePackages) {
  externals.add(name);
}

/** @type {import('esbuild').BuildOptions} */
export default {
  entryPoints: ["src/index.ts"],
  bundle: true,
  platform: "node",
  target: "node24",
  format: "esm",
  outfile: "dist/index.js",
  banner: { js: "#!/usr/bin/env node" },
  // Node built-ins remain external automatically; every resolvable package
  // import is embedded in dist/index.js for the certified archive.
  external: [...externals].sort(),
  treeShaking: true,
  sourcemap: true,
};
