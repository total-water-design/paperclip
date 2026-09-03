#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE="$(mktemp -d)"
trap 'rm -rf "$FIXTURE"' EXIT
REPO="$FIXTURE/repo"
STAGE="$FIXTURE/staging"

git init -q "$REPO"
git -C "$REPO" config user.name test
git -C "$REPO" config user.email test@example.invalid
printf 'tracked payload\n' > "$REPO/app.py"
git -C "$REPO" add app.py
git -C "$REPO" commit -qm candidate
SHA="$(git -C "$REPO" rev-parse HEAD)"

# These files model runner residue and secrets. A commit-derived bundle must
# contain neither tracked-worktree mutations nor untracked runtime material.
printf 'mutated runner bytes\n' > "$REPO/app.py"
printf 'SECRET=must-not-ship\n' > "$REPO/.env"
mkdir "$REPO/instance"
printf 'runtime data\n' > "$REPO/instance/app.db"

(
    cd "$REPO"
    "$ROOT/deploy/prepare_exact_commit_bundle.sh" \
        "$STAGE" "$SHA" total-water-design/total-water-design-suite "$SHA"
)

git init -q "$FIXTURE/materialized"
git -C "$FIXTURE/materialized" fetch -q "$STAGE/source.bundle" \
    refs/twds-deploy/candidate
git -C "$FIXTURE/materialized" checkout -q --detach FETCH_HEAD
[[ "$(git -C "$FIXTURE/materialized" rev-parse HEAD)" == "$SHA" ]]
[[ "$(cat "$FIXTURE/materialized/app.py")" == "tracked payload" ]]
[[ ! -e "$FIXTURE/materialized/.env" ]]
[[ ! -e "$FIXTURE/materialized/instance" ]]
[[ "$(cat "$STAGE/.deployment_commit")" == "$SHA" ]]
grep -qx "repository=total-water-design/total-water-design-suite" "$STAGE/.deployment_provenance"
grep -qx 'authorized_ref=refs/heads/alpha' "$STAGE/.deployment_provenance"
grep -qx "authorized_remote_sha=$SHA" "$STAGE/.deployment_provenance"
grep -qx "approved_sha=$SHA" "$STAGE/.deployment_provenance"
grep -qx "checked_out_sha=$SHA" "$STAGE/.deployment_provenance"

if (cd "$REPO" && "$ROOT/deploy/prepare_exact_commit_bundle.sh" \
    "$FIXTURE/rejected" "$SHA" total-water-design/total-water-design-suite \
    "0000000000000000000000000000000000000000") >/dev/null 2>&1; then
    echo "ERROR: mismatched authorized remote SHA was accepted" >&2
    exit 1
fi

echo "PASS - exact commit and provenance bundled; runner mutations and secrets excluded"
