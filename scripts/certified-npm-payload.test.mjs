import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, statSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const repo = path.resolve(import.meta.dirname, "..");
const packageVersion = JSON.parse(readFileSync(path.join(repo, "cli/package.json"), "utf8")).version;
const required = new Map([
  ["package/dist/deploy/systemd/paperclip-service-install", "payload_root="],
  ["package/dist/deploy/systemd/paperclip-preflight", "PAPERCLIP_SERVICE_MANAGED"],
  ["package/dist/deploy/systemd/paperclip.service", "paperclip-activation-preflight"],
  ["package/dist/deploy/systemd/paperclip.service.d/10-safe-shutdown.conf", "KillMode=mixed"],
  ["package/dist/deploy/systemd/paperclip.service.d/20-git-scan-containment.conf", "PAPERCLIP_WORKSPACE_GIT_SCAN_CONCURRENCY=1"],
  ["package/dist/deploy/systemd/paperclip-health-recovery", "recovery threshold reached"],
  ["package/dist/deploy/systemd/paperclip-recovery-token-provision", "token must be a non-whitespace value"],
  ["package/dist/deploy/recovery/paperclip-recovery", "/api/recovery/reconcile"],
  ["package/dist/deploy/recovery/paperclip-recovery.sudoers", "NOPASSWD"],
  ["package/dist/scripts/paperclip-activation-preflight.sh", "artifact identity verifier"],
  ["package/dist/scripts/paperclip-artifact-identity.mjs", "sourceSha"],
]);

const runtimeWorkspacePackages = [
  "@paperclipai/server",
  "@paperclipai/adapter-utils",
  "@paperclipai/db",
  "@paperclipai/shared",
  "@paperclipai/adapter-claude-local",
  "@paperclipai/adapter-codex-local",
  "@paperclipai/adapter-openclaw-gateway",
];

test("certified npm archive contains the complete reviewed service payload safely", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "paperclip-certified-payload-"));
  try {
    execFileSync("bash", [path.join(repo, "scripts/build-certified-npm.sh"), "--skip-checks", "--skip-typecheck"], {
      cwd: repo,
      env: { ...process.env, PAPERCLIP_ARTIFACT_DIR: root, PAPERCLIP_TMPDIR: root },
      stdio: "pipe",
    });
    const archive = path.join(root, `paperclipai-${packageVersion}.tgz`);
    const listing = execFileSync("tar", ["-tzf", archive], { encoding: "utf8" }).trim().split("\n");
    assert.ok(listing.every((entry) => entry === "package/" || (entry.startsWith("package/") && !entry.includes("../") && !entry.startsWith("/"))), "archive paths must remain beneath package/");
    for (const name of required.keys()) assert.ok(listing.includes(name), `missing ${name}`);
    execFileSync("tar", ["-xzf", archive, "-C", root]);
    for (const [name, marker] of required) assert.match(readFileSync(path.join(root, name), "utf8"), new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `${name} lacks marker`);
    for (const name of [
      "paperclip-service-install", "paperclip-preflight", "paperclip-health-recovery", "paperclip-recovery-token-provision",
    ]) assert.equal(statSync(path.join(root, `package/dist/deploy/systemd/${name}`)).mode & 0o111, 0o111, `${name} must be executable`);
    assert.equal(statSync(path.join(root, "package/dist/deploy/recovery/paperclip-recovery")).mode & 0o111, 0o111);
    assert.equal(statSync(path.join(root, "package/dist/scripts/paperclip-activation-preflight.sh")).mode & 0o111, 0o111);
    assert.equal(statSync(path.join(root, "package/dist/scripts/paperclip-artifact-identity.mjs")).mode & 0o111, 0o111);
    assert.ok(listing.some((entry) => entry.startsWith("package/node_modules/.pnpm/")), "archive must carry a production dependency closure");
    const resolver = [
      "const { createRequire } = require('node:module');",
      "const root = process.argv[1];",
      "const requireFromPayload = createRequire(`${root}/dist/index.js`);",
      `for (const dependency of ${JSON.stringify(runtimeWorkspacePackages)}) {`,
      "  const resolved = requireFromPayload.resolve(dependency);",
      "  if (!resolved.startsWith(`${root}/node_modules/`)) throw new Error(`dependency escaped payload: ${dependency} -> ${resolved}`);",
      "  process.stdout.write(`${dependency}\\t${resolved}\\n`);",
      "}",
    ].join("\n");
    const resolved = execFileSync(process.execPath, ["-e", resolver, path.join(root, "package")], { encoding: "utf8" });
    for (const dependency of runtimeWorkspacePackages) assert.match(resolved, new RegExp(`^${dependency}\\t`, "m"), `missing runtime dependency ${dependency}`);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
