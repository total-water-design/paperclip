import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { createCertification, createIdentity, verifyActivation } from "./paperclip-artifact-identity.mjs";

function fixture() {
  const root = mkdtempSync(path.join(os.tmpdir(), "paperclip-identity-"));
  execFileSync("git", ["init", "-q", root]);
  execFileSync("git", ["-C", root, "config", "user.email", "test@example.invalid"]);
  execFileSync("git", ["-C", root, "config", "user.name", "Test"]);
  writeFileSync(path.join(root, "pnpm-lock.yaml"), "lockfileVersion: '9.0'\n");
  writeFileSync(path.join(root, "source"), "source\n");
  writeFileSync(path.join(root, ".gitignore"), "out/\n");
  execFileSync("git", ["-C", root, "add", "."]); execFileSync("git", ["-C", root, "commit", "-qm", "fixture"]);
  const sha = execFileSync("git", ["-C", root, "rev-parse", "HEAD"], { encoding: "utf8" }).trim();
  return { root, sha };
}

test("identity is byte reproducible and rejects a false source label", () => {
  const { root, sha } = fixture(); const out = path.join(root, "out"); mkdirSync(out); writeFileSync(path.join(out, "index.js"), "ok\n");
  createIdentity({ repo: root, outputDir: out, sourceSha: sha, canonicalBuildCommand: "pnpm certified" });
  const first = readFileSync(path.join(out, "paperclip-artifact-identity.json"));
  createIdentity({ repo: root, outputDir: out, sourceSha: sha, canonicalBuildCommand: "pnpm certified" });
  assert.deepEqual(readFileSync(path.join(out, "paperclip-artifact-identity.json")), first);
  assert.throws(() => createIdentity({ repo: root, outputDir: out, sourceSha: "0".repeat(40), canonicalBuildCommand: "pnpm certified" }), /source label mismatch/);
});

test("identity rejects an untracked source file", () => {
  const { root, sha } = fixture(); const out = path.join(root, "out"); mkdirSync(out); writeFileSync(path.join(out, "index.js"), "ok\n");
  writeFileSync(path.join(root, "untracked-source.ts"), "export {};\n");
  assert.throws(() => createIdentity({ repo: root, outputDir: out, sourceSha: sha, canonicalBuildCommand: "pnpm certified" }), /source tree is dirty/);
});

test("activation rejects stale runtime and changed installed executable", () => {
  const { root, sha } = fixture(); const out = path.join(root, "out"); mkdirSync(out); const executable = path.join(out, "index.js"); writeFileSync(executable, "ok\n");
  createIdentity({ repo: root, outputDir: out, sourceSha: sha, canonicalBuildCommand: "pnpm certified" });
  const identity = path.join(out, "paperclip-artifact-identity.json"); const archive = path.join(root, "a.tgz"); writeFileSync(archive, "archive"); const manifest = path.join(root, "cert.json");
  createCertification({ identityPath: identity, archivePath: archive, executablePath: executable, outputPath: manifest });
  const runtime = path.join(root, "runtime.json"); writeFileSync(runtime, JSON.stringify({ sourceSha: "1".repeat(40), executableSha256: "2".repeat(64) }));
  assert.throws(() => verifyActivation({ manifestPath: manifest, identityPath: identity, executablePath: executable, archivePath: archive, runtimeIdentityPath: runtime }), /stale runtime identity/);
  writeFileSync(executable, "tampered\n");
  assert.throws(() => verifyActivation({ manifestPath: manifest, identityPath: identity, executablePath: executable }), /executable digest differs/);
});
