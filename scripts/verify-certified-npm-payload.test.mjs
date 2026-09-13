import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { collectRuntimeModules, verifyExtractedConsumer } from "./verify-certified-npm-payload.mjs";

function fixture({ source = 'console.log("help")', modules = {} } = {}) {
  const root = mkdtempSync(join(tmpdir(), "paperclip-payload-test-"));
  mkdirSync(join(root, "package", "dist"), { recursive: true });
  writeFileSync(join(root, "package", "package.json"), '{"name":"paperclipai"}\n');
  writeFileSync(join(root, "package", "dist", "index.js"), source);
  for (const [name, contents] of Object.entries(modules)) {
    const dir = join(root, "package", "node_modules", name);
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "package.json"), '{"name":"fixture","main":"index.js"}\n');
    writeFileSync(join(dir, "index.js"), contents);
  }
  return root;
}

test("resolves an actual extracted runtime module and executes --help", () => {
  const root = fixture({ source: 'require("zod"); console.log("help")', modules: { zod: "module.exports = {};" } });
  try {
    assert.deepEqual(verifyExtractedConsumer(root).runtimeModules, ["zod"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("rejects a declared-but-missing extracted runtime module", () => {
  const root = fixture({ source: 'require("zod"); console.log("help")' });
  try {
    assert.throws(() => verifyExtractedConsumer(root), /runtime module resolution failed/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("collects import, dynamic import, and require module edges", () => {
  assert.deepEqual(collectRuntimeModules('import z from "zod"; import("@paperclipai/server"); require("dotenv");'), ["@paperclipai/server", "dotenv", "zod"]);
});
