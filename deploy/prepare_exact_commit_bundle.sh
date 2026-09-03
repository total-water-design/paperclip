#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 4 ]]; then
    echo "usage: $0 STAGE REQUESTED_SHA REPOSITORY AUTHORIZED_REMOTE_SHA" >&2
    exit 64
fi

STAGE=$1
REQUESTED_SHA=$2
REPOSITORY=$3
AUTHORIZED_REMOTE_SHA=$4
AUTHORIZED_REF=refs/heads/alpha
BUNDLE_REF=refs/twds-deploy/candidate

[[ "$REQUESTED_SHA" =~ ^[0-9a-f]{40}$ ]] || {
    echo "ERROR: requested SHA is not a full lowercase Git SHA." >&2
    exit 1
}
[[ "$AUTHORIZED_REMOTE_SHA" == "$REQUESTED_SHA" ]] || {
    echo "ERROR: authorized remote SHA differs from requested SHA." >&2
    exit 1
}

CHECKED_OUT_SHA="$(git rev-parse HEAD)"
[[ "$CHECKED_OUT_SHA" == "$REQUESTED_SHA" ]] || {
    echo "ERROR: checked-out SHA differs from requested SHA." >&2
    exit 1
}

rm -rf -- "$STAGE"
mkdir -p -- "$STAGE"
trap 'git update-ref -d "$BUNDLE_REF"' EXIT
git update-ref "$BUNDLE_REF" "$REQUESTED_SHA"
git bundle create "$STAGE/source.bundle" "$BUNDLE_REF"
git bundle verify "$STAGE/source.bundle"
git bundle list-heads "$STAGE/source.bundle" |
    awk -v sha="$REQUESTED_SHA" -v ref="$BUNDLE_REF" \
        '$1 == sha && $2 == ref { found=1 } END { exit !found }'
git update-ref -d "$BUNDLE_REF"
trap - EXIT

printf '%s\n' "$REQUESTED_SHA" > "$STAGE/.deployment_commit"
{
    printf 'repository=%s\n' "$REPOSITORY"
    printf 'authorized_ref=%s\n' "$AUTHORIZED_REF"
    printf 'authorized_remote_sha=%s\n' "$AUTHORIZED_REMOTE_SHA"
    printf 'approved_sha=%s\n' "$REQUESTED_SHA"
    printf 'checked_out_sha=%s\n' "$CHECKED_OUT_SHA"
    printf 'prepared_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$STAGE/.deployment_provenance"

echo "Exact-commit bundle prepared."
echo "Commit: $(cat "$STAGE/.deployment_commit")"
