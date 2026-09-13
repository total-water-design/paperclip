import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { collectPaperclipRuntimeImports, verifyExtractedConsumer } from "./verify-certified-npm-payload.mjs";

function fixture({ dependencies = {}, source = "export default 1;" } = {}) {
  const root = mkdtempSync(join(tmpdir(), "paperclip-payload-test-"));
  mkdirSync(join(root, "package", "dist"), { recursive: true });
  writeFileSync(join(root, "package", "package.json"), `${JSON.stringify({ name: "paperclipai", dependencies })}\n`);
  writeFileSync(join(root, "package", "dist", "index.js"), source);
  return root;
}

test("accepts an extracted consumer whose residual Paperclip dependency is declared", () => {
  const root = fixture({
    dependencies: { "@paperclipai/server": "1.0.0" },
    source: 'import { start } from "@paperclipai/server"; start();',
  });
  try {
    assert.deepEqual(verifyExtractedConsumer(root).declaredPaperclipDependencies, ["@paperclipai/server"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("rejects an extracted consumer with an undeclared Paperclip runtime dependency", () => {
  const root = fixture({ source: 'import { start } from "@paperclipai/server"; start();' });
  try {
    assert.throws(() => verifyExtractedConsumer(root), /unresolved @paperclipai runtime dependencies: @paperclipai\/server/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("does not mistake generated plugin source strings for runtime imports", () => {
  const source = 'const generated = `import { definePlugin } from "@paperclipai/plugin-sdk"`; await import("@paperclipai/server");';
  assert.deepEqual([...collectPaperclipRuntimeImports(source)], ["@paperclipai/server"]);
});
