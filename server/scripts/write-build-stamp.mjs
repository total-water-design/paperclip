// Write the build stamp for the server.
//
// The server `build` script runs this after `tsc`. It writes the commit SHA
// into `dist/build-manifest.json`. The runtime reads that manifest when the
// image has no `.git`, so health and telemetry retain immutable source
// attribution.
//
// The build resolves the commit in two steps:
//   1. `git rev-parse HEAD` in the server directory.
//   2. The `PAPERCLIP_BUILD_COMMIT` environment variable.
// A Docker image build excludes `.git`, so the git lookup fails there. The
// image build passes the commit in `PAPERCLIP_BUILD_COMMIT` instead, so the
// stamp still records the true built commit.
//
// A deployable build must fail closed when no full source SHA is available.
// Accepting a short SHA or silently omitting the manifest makes a runtime
// impossible to attribute after its checkout has been removed.

import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const serverDir = join(scriptDir, "..");
const distDir = join(serverDir, "dist");
const outFile = join(distDir, "build-manifest.json");
const FULL_SHA_RE = /^[0-9a-f]{40}$/i;

/**
 * Resolve the commit for the build manifest. Prefer the git commit. Fall back to
 * the supplied commit — the value a Docker image build passes in
 * `PAPERCLIP_BUILD_COMMIT` when `.git` is absent. Return null when neither
 * source gives a full SHA.
 *
 * @param {unknown} gitCommit The `git rev-parse` result, or null on failure.
 * @param {unknown} suppliedCommit The `PAPERCLIP_BUILD_COMMIT` value.
 * @returns {string | null}
 */
export function resolveBuildCommit(gitCommit, suppliedCommit) {
  const git = typeof gitCommit === "string" ? gitCommit.trim() : "";
  if (FULL_SHA_RE.test(git)) return git.toLowerCase();
  const supplied = typeof suppliedCommit === "string" ? suppliedCommit.trim() : "";
  if (FULL_SHA_RE.test(supplied)) return supplied.toLowerCase();
  return null;
}

/**
 * Read the full commit SHA with `git rev-parse HEAD` in the server
 * directory. Return the SHA, or null on any failure.
 *
 * @returns {string | null}
 */
function readGitCommit() {
  try {
    const out = execFileSync("git", ["rev-parse", "HEAD"], {
      cwd: serverDir,
      stdio: ["ignore", "pipe", "ignore"],
    })
      .toString()
      .trim();
    return out.length > 0 ? out : null;
  } catch {
    return null;
  }
}

/**
 * Resolve the commit and write a deterministic build manifest. Fail closed
 * when no immutable source SHA is available.
 */
function main() {
  const commit = resolveBuildCommit(readGitCommit(), process.env.PAPERCLIP_BUILD_COMMIT);

  if (!commit) {
    throw new Error("[build-manifest] PAPERCLIP_BUILD_COMMIT must be a full SHA when git metadata is unavailable");
  }

  mkdirSync(distDir, { recursive: true });
  writeFileSync(outFile, `${JSON.stringify({ schemaVersion: 1, sourceSha: commit }, null, 2)}\n`);
  console.log(`[build-manifest] wrote ${outFile} sourceSha=${commit}`);
}

// Run only when node invokes this file directly (the `build` script). A test
// that imports `resolveBuildCommit` does not run `main`.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
