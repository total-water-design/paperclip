import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, statSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const repo = path.resolve(import.meta.dirname, "..");
const required = new Map([
  ["dist/deploy/systemd/paperclip-service-install", "payload_root="],
  ["dist/deploy/systemd/paperclip-preflight", "PAPERCLIP_SERVICE_MANAGED"],
  ["dist/deploy/systemd/paperclip.service", "paperclip-activation-preflight"],
  ["dist/deploy/systemd/paperclip.service.d/10-safe-shutdown.conf", "KillMode=mixed"],
  ["dist/deploy/systemd/paperclip.service.d/20-git-scan-containment.conf", "PAPERCLIP_WORKSPACE_GIT_SCAN_CONCURRENCY=1"],
  ["dist/deploy/systemd/paperclip-health-recovery", "recovery threshold reached"],
  ["dist/deploy/systemd/paperclip-recovery-token-provision", "token must be a non-whitespace value"],
  ["dist/deploy/recovery/paperclip-recovery", "/api/recovery/reconcile"],
  ["dist/deploy/recovery/paperclip-recovery.sudoers", "NOPASSWD"],
  ["dist/scripts/paperclip-activation-preflight.sh", "artifact identity verifier"],
  ["dist/scripts/paperclip-artifact-identity.mjs", "sourceSha"],
]);

test("certified staging payload installs the CLI at the mandatory host-side path", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "paperclip-certified-payload-"));
  try {
    execFileSync("bash", [path.join(repo, "scripts/build-certified-npm.sh"), "--skip-checks", "--skip-typecheck"], {
      cwd: repo,
      env: { ...process.env, PAPERCLIP_ARTIFACT_DIR: root, PAPERCLIP_TMPDIR: root },
      stdio: "pipe",
    });
    const archive = path.join(root, "paperclipai-0.3.1.tgz");
    const listing = execFileSync("tar", ["-tzf", archive], { encoding: "utf8" }).trim().split("\n");
    assert.ok(listing.every((entry) => entry === "package/" || (entry.startsWith("package/") && !entry.includes("../") && !entry.startsWith("/"))), "archive paths must remain beneath package/");
    assert.ok(listing.includes("package/package.json"), "missing staging manifest");
    assert.ok(listing.includes("package/paperclipai-cli.tgz"), "missing nested CLI package");
    const payload = path.join(root, "payload");
    mkdirSync(payload);
    execFileSync("tar", ["-xzf", archive, "--strip-components=1", "-C", payload]);
    execFileSync("npm", ["install", "--no-audit", "--no-fund"], { cwd: payload, stdio: "pipe" });
    for (const [name, marker] of required) assert.match(readFileSync(path.join(payload, "node_modules/paperclipai", name), "utf8"), new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `${name} lacks marker`);
    for (const name of [
      "paperclip-service-install", "paperclip-preflight", "paperclip-health-recovery", "paperclip-recovery-token-provision",
    ]) assert.equal(statSync(path.join(payload, `node_modules/paperclipai/dist/deploy/systemd/${name}`)).mode & 0o111, 0o111, `${name} must be executable`);
    assert.equal(statSync(path.join(payload, "node_modules/paperclipai/dist/deploy/recovery/paperclip-recovery")).mode & 0o111, 0o111);
    assert.equal(statSync(path.join(payload, "node_modules/paperclipai/dist/scripts/paperclip-activation-preflight.sh")).mode & 0o111, 0o111);
    assert.equal(statSync(path.join(payload, "node_modules/paperclipai/dist/scripts/paperclip-artifact-identity.mjs")).mode & 0o111, 0o111);
    assert.equal(
      execFileSync("node", ["node_modules/paperclipai/dist/index.js", "--version"], { cwd: payload, encoding: "utf8" }).trim(),
      "0.3.1",
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
