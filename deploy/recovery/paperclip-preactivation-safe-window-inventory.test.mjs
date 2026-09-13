import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

const script = fileURLToPath(new URL("./paperclip-preactivation-safe-window-inventory", import.meta.url));
const source = readFileSync(script, "utf8");

test("denies caller supplied arguments before inspecting host state", () => {
  assert.throws(
    () => execFileSync("/bin/sh", [script, "unexpected"], { encoding: "utf8", stdio: "pipe" }),
    (error) => error.status === 64 && /accepts no arguments/.test(error.stderr),
  );
});

test("fixes company scope and peer authentication without a credential path", () => {
  assert.match(source, /company_file=\/etc\/paperclip\/preactivation-safe-window-company/);
  assert.match(source, /root:640/);
  assert.match(source, /--host=\/var\/run\/postgresql/);
  assert.match(source, /--username=paperclip/);
  assert.match(source, /BEGIN TRANSACTION READ ONLY;/);
  assert.doesNotMatch(source, /DATABASE_URL|PGPASSWORD|recovery\.token|safe-window-inventory-token/);
});

test("has no mutation, recovery, service-control, or agent invocation surface", () => {
  const executableLines = source.split("\n").filter((line) => !line.startsWith("#")).join("\n");
  assert.match(source, /status IN \('queued', 'running', 'scheduled_retry'\)/);
  assert.match(source, /'safeWindowDisposition', 'drain_required'/);
  assert.doesNotMatch(executableLines, /\b(?:INSERT|UPDATE|DELETE|ALTER|CREATE|DROP)\b/);
  assert.doesNotMatch(executableLines, /systemctl|curl|reconcile|resume|wake|sudo|kill/);
  assert.doesNotMatch(executableLines, /mktemp|mkdir|rm |chmod|chown/);
});
