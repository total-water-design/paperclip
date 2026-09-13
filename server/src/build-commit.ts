import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

type ReadTextFile = (path: string) => string;

const FULL_SHA_RE = /^[0-9a-f]{40}$/i;
const DEFAULT_BUILD_MANIFEST_PATH = fileURLToPath(
  new URL("./build-manifest.json", import.meta.url),
);

export function parseBuildCommit(value: string | null | undefined): string | null {
  const commit = value?.trim() ?? "";
  return FULL_SHA_RE.test(commit) ? commit.toLowerCase() : null;
}

export function parseBuildManifest(value: string | null | undefined): string | null {
  try {
    const parsed = JSON.parse(value ?? "") as { schemaVersion?: unknown; sourceSha?: unknown };
    return parsed.schemaVersion === 1 && typeof parsed.sourceSha === "string"
      ? parseBuildCommit(parsed.sourceSha)
      : null;
  } catch {
    return null;
  }
}

export function readBuildCommit(
  opts: {
    environmentCommit?: string | null;
    buildManifestPath?: string;
    readTextFile?: ReadTextFile;
  } = {},
): string | null {
  const environmentCommit = parseBuildCommit(
    opts.environmentCommit === undefined
      ? process.env.PAPERCLIP_BUILD_COMMIT
      : opts.environmentCommit,
  );
  if (environmentCommit) return environmentCommit;

  try {
    const readTextFile = opts.readTextFile ?? ((path: string) => readFileSync(path, "utf8"));
    return parseBuildManifest(readTextFile(opts.buildManifestPath ?? DEFAULT_BUILD_MANIFEST_PATH));
  } catch {
    return null;
  }
}
