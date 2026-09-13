#!/usr/bin/env node
/**
 * Restores TypeScript source entrypoints for workspace packages in a deployed
 * certified payload. These packages deliberately export ./src/*.ts during
 * development, while pnpm deploy correctly honours their npm `files` lists
 * and otherwise omits that source directory.
 */
import { cpSync, existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

const [repoRootArg, payloadRootArg] = process.argv.slice(2);
if (!repoRootArg || !payloadRootArg) throw new Error("usage: materialize-certified-runtime-sources.mjs <repo-root> <payload-root>");
const repoRoot = resolve(repoRootArg);
const payloadRoot = resolve(payloadRootArg);

function walk(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const target = join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === "node_modules" || entry.name === ".git" ? [] : walk(target);
    return entry.name === "package.json" ? [target] : [];
  });
}

for (const packageJsonPath of walk(repoRoot)) {
  const relative = packageJsonPath.slice(repoRoot.length + 1);
  const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf8"));
  if (!packageJson.name?.startsWith("@paperclipai/")) continue;
  const exportsText = JSON.stringify(packageJson.exports ?? {});
  if (!exportsText.includes("./src/")) continue;
  const source = join(dirname(packageJsonPath), "src");
  const deployed = join(payloadRoot, "node_modules", packageJson.name, "src");
  if (!existsSync(source) || !existsSync(dirname(deployed))) continue;
  cpSync(source, deployed, { recursive: true, force: true, dereference: false });
  process.stdout.write(`materialized ${packageJson.name}/src\n`);
}
