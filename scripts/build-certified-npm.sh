#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
source_sha="${PAPERCLIP_SOURCE_SHA:-$(git -C "$repo_root" rev-parse HEAD)}"
canonical_command="PAPERCLIP_SOURCE_SHA=$source_sha corepack pnpm build:npm:certified"
artifact_dir="${PAPERCLIP_ARTIFACT_DIR:-$repo_root/artifacts}"
version="$(node -p "require('$repo_root/cli/package.json').version")"
archive="$artifact_dir/paperclipai-$version.tgz"
manifest="$artifact_dir/paperclipai-$version.certification.json"

git -C "$repo_root" diff --quiet --exit-code
git -C "$repo_root" diff --cached --quiet --exit-code
[[ -z "$(git -C "$repo_root" status --porcelain --untracked-files=normal)" ]] || { echo "certified build: source tree is dirty" >&2; exit 1; }
[[ "$source_sha" =~ ^[0-9a-f]{40}$ ]] || { echo "certified build: PAPERCLIP_SOURCE_SHA must be a full SHA" >&2; exit 1; }
[[ "$source_sha" == "$(git -C "$repo_root" rev-parse HEAD)" ]] || { echo "certified build: source label mismatch" >&2; exit 1; }

mkdir -p "$artifact_dir"
trap 'if [[ -f "$repo_root/cli/package.dev.json" ]]; then mv "$repo_root/cli/package.dev.json" "$repo_root/cli/package.json"; fi; rm -f "$repo_root/cli/README.md"' EXIT
"$repo_root/scripts/build-npm.sh" "$@"
stage="$(mktemp -d "${PAPERCLIP_TMPDIR:-/tmp}/paperclip-package.XXXXXX")"
trap 'rm -rf "$stage"; if [[ -f "$repo_root/cli/package.dev.json" ]]; then mv "$repo_root/cli/package.dev.json" "$repo_root/cli/package.json"; fi; rm -f "$repo_root/cli/README.md"' EXIT
mkdir -p "$stage/package"
cp "$repo_root/cli/package.json" "$stage/package/package.json"
cp "$repo_root/cli/README.md" "$stage/package/README.md"
mv "$repo_root/cli/package.dev.json" "$repo_root/cli/package.json"
rm -f "$repo_root/cli/README.md"
node "$repo_root/scripts/paperclip-artifact-identity.mjs" identity --repo "$repo_root" --output-dir "$repo_root/cli/dist" --source-sha "$source_sha" --build-command "$canonical_command"
cp -R "$repo_root/cli/dist" "$stage/package/"

epoch="$(git -C "$repo_root" show -s --format=%ct "$source_sha")"
COPYFILE_DISABLE=1 tar --sort=name --format=posix --mtime="@$epoch" --owner=0 --group=0 --numeric-owner --pax-option=delete=atime,delete=ctime -C "$stage" -cf - package | gzip -n -9 > "$archive"
node "$repo_root/scripts/paperclip-artifact-identity.mjs" certify --identity "$repo_root/cli/dist/paperclip-artifact-identity.json" --archive "$archive" --executable "$repo_root/cli/dist/index.js" --manifest "$manifest"
printf 'certified archive: %s\ncertification manifest: %s\n' "$archive" "$manifest"
