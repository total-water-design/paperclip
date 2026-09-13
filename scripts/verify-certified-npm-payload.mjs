#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const PACKAGE_ROOT = "package";
const PAPERCLIP_PACKAGE = /^(@paperclipai\/[a-z0-9-]+)(?:\/|$)/;

function fail(message) {
  throw new Error(`certified payload: ${message}`);
}

function walk(root, current = root) {
  const files = [];
  for (const name of readdirSync(current).sort()) {
    const path = join(current, name);
    const stat = statSync(path);
    if (stat.isDirectory()) files.push(...walk(root, path));
    else if (stat.isFile()) files.push(path);
  }
  return files;
}

function skipQuoted(source, start, quote) {
  for (let index = start + 1; index < source.length; index += 1) {
    if (source[index] === "\\") index += 1;
    else if (source[index] === quote) return index + 1;
  }
  return source.length;
}

function skipSpace(source, index) {
  while (/\s/.test(source[index] ?? "")) index += 1;
  return index;
}

function readQuotedSpecifier(source, index) {
  if (source[index] !== '"' && source[index] !== "'") return null;
  const end = source.indexOf(source[index], index + 1);
  if (end === -1) return null;
  return { value: source.slice(index + 1, end), end: end + 1 };
}

export function collectPaperclipRuntimeImports(source) {
  const imports = new Set();
  for (let index = 0; index < source.length;) {
    const char = source[index];
    if (char === '"' || char === "'" || char === "`") {
      index = skipQuoted(source, index, char);
      continue;
    }
    if (source.startsWith("//", index)) {
      index = source.indexOf("\n", index + 2);
      if (index === -1) break;
      continue;
    }
    if (source.startsWith("/*", index)) {
      index = source.indexOf("*/", index + 2);
      if (index === -1) break;
      index += 2;
      continue;
    }
    const word = source.slice(index).match(/^(import|require)\b/)?.[1];
    if (!word) {
      index += 1;
      continue;
    }
    let cursor = skipSpace(source, index + word.length);
    if (word === "import" && source[cursor] !== "(") {
      const from = source.slice(cursor).match(/\bfrom\s*(["'])/);
      if (!from) {
        index = cursor;
        continue;
      }
      cursor += from.index + from[0].length - 1;
    } else if (source[cursor] === "(") {
      cursor = skipSpace(source, cursor + 1);
    } else {
      index = cursor;
      continue;
    }
    const specifier = readQuotedSpecifier(source, cursor);
    if (specifier) {
      const match = specifier.value.match(PAPERCLIP_PACKAGE);
      if (match) imports.add(match[1]);
      index = specifier.end;
    } else index = cursor + 1;
  }
  return imports;
}

export function verifyExtractedConsumer(extractedRoot) {
  const packageRoot = resolve(extractedRoot, PACKAGE_ROOT);
  const manifestPath = join(packageRoot, "package.json");
  const entryPath = join(packageRoot, "dist", "index.js");
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  } catch {
    fail("extracted consumer has no readable package/package.json");
  }
  try {
    statSync(entryPath);
  } catch {
    fail("extracted consumer has no dist/index.js entrypoint");
  }

  const declared = new Set([
    ...Object.keys(manifest.dependencies ?? {}),
    ...Object.keys(manifest.optionalDependencies ?? {}),
  ]);
  const unresolved = new Set();
  for (const file of walk(packageRoot)) {
    if (!file.endsWith(".js") && !file.endsWith(".mjs") && !file.endsWith(".cjs")) continue;
    const source = readFileSync(file, "utf8");
    for (const importedPackage of collectPaperclipRuntimeImports(source)) {
      if (!declared.has(importedPackage)) unresolved.add(importedPackage);
    }
  }
  if (unresolved.size > 0) {
    fail(`extracted consumer has unresolved @paperclipai runtime dependencies: ${[...unresolved].sort().join(", ")}`);
  }
  return {
    entryPath: "package/dist/index.js",
    declaredPaperclipDependencies: [...declared].filter((name) => name.startsWith("@paperclipai/")).sort(),
  };
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
    console.log(`certified payload: extracted consumer resolves @paperclipai dependencies (${result.declaredPaperclipDependencies.join(", ") || "bundled"})`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
