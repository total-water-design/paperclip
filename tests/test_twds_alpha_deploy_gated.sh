#!/usr/bin/env bash
set -Eeuo pipefail

# Non-production source-integrity canary.  It uses an isolated temporary Git
# repository, staging directory, candidate root, evidence root, and mocked
# service commands; it never contacts Alpha or invokes the production paths.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE="$(mktemp -d)"
cleanup() {
    local rc=$?
    chmod 700 "$STAGE" 2>/dev/null || true
    if [[ $rc -ne 0 ]]; then
        find "$FIXTURE" -maxdepth 1 -name '*.out' -exec sh -c \
            'echo "--- $1"; cat "$1"' _ {} \;
    fi
    rm -rf "$FIXTURE"
    exit "$rc"
}
trap cleanup EXIT

APPROVAL="$FIXTURE/approved_sha"
LOCK="$FIXTURE/deploy.lock"
STAGE="$FIXTURE/staging"
MARKER="$STAGE/.deployment_commit"
BUNDLE="$STAGE/source.bundle"
PROVENANCE="$STAGE/.deployment_provenance"
LIVE="$FIXTURE/live_sha"
CANDIDATES="$FIXTURE/candidates"
EVIDENCE="$FIXTURE/deployments"
DEPLOYER="$FIXTURE/deployer"
GATE="$FIXTURE/gate"
REPO="$FIXTURE/repo"
OTHER_REPO="$FIXTURE/other-repo"
MOCKBIN="$FIXTURE/bin"

mkdir -p "$MOCKBIN"
printf '#!/usr/bin/env bash\nexit 0\n' > "$MOCKBIN/logger"
chmod +x "$MOCKBIN/logger"
cat > "$MOCKBIN/systemctl" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "list-unit-files" ]]; then
    printf 'totalrodesign.service enabled\n'
    exit 0
fi
if [[ "$1" == "is-active" ]]; then
    printf 'active\n'
    exit 0
fi
exit 0
EOF
chmod +x "$MOCKBIN/systemctl"
export PATH="$MOCKBIN:$PATH"

git init -q "$REPO"
git -C "$REPO" config user.name test
git -C "$REPO" config user.email test@example.invalid
mkdir -p "$REPO/deploy"
printf 'approved bytes\n' > "$REPO/ordinary.txt"
printf '# safe script bytes\n' > "$REPO/deploy/helper.py"
printf '# candidate app bytes\n' > "$REPO/app.py"
printf '# candidate auth bytes\n' > "$REPO/auth.py"
printf '# candidate wsgi bytes\n' > "$REPO/wsgi.py"
: > "$REPO/requirements.txt"
: > "$REPO/requirements-server.txt"
printf 'print("candidate template verification")\n' > "$REPO/deploy/verify_templates.py"
printf 'print("candidate auth verification")\n' > "$REPO/deploy/verify_auth_install.py"
git -C "$REPO" add .
git -C "$REPO" commit -qm approved
SHA="$(git -C "$REPO" rev-parse HEAD)"

git init -q "$OTHER_REPO"
git -C "$OTHER_REPO" config user.name test
git -C "$OTHER_REPO" config user.email test@example.invalid
printf 'unapproved\n' > "$OTHER_REPO/ordinary.txt"
git -C "$OTHER_REPO" add .
git -C "$OTHER_REPO" commit -qm unapproved

sed \
    -e "s|^APPROVAL=.*|APPROVAL=$APPROVAL|" \
    -e "s|^LOCK=.*|LOCK=$LOCK|" \
    -e "s|^STAGE_MARKER=.*|STAGE_MARKER=$MARKER|" \
    -e "s|^STAGE_BUNDLE=.*|STAGE_BUNDLE=$BUNDLE|" \
    -e "s|^STAGE_PROVENANCE=.*|STAGE_PROVENANCE=$PROVENANCE|" \
    -e "s|^LIVE_MARKER=.*|LIVE_MARKER=$LIVE|" \
    -e "s|^CANDIDATE_ROOT=.*|CANDIDATE_ROOT=$CANDIDATES|" \
    -e "s|^EVIDENCE_ROOT=.*|EVIDENCE_ROOT=$EVIDENCE|" \
    -e "s|^DEPLOYER=.*|DEPLOYER=$DEPLOYER|" \
    -e 's|^\[\[ \$EUID -eq 0 \]\].*|: # production root check|' \
    -e 's|^chown root:root |: test-chown |' \
    -e 's|^chown -R root:root |: test-chown-recursive |' \
    "$ROOT/deploy/twds-alpha-deploy-gated" > "$GATE"
chmod +x "$GATE"

make_bundle() {
    local repo="${1:-$REPO}"
    mkdir -p "$STAGE"
    git -C "$repo" bundle create "$BUNDLE" HEAD
}

reset_fixture() {
    rm -rf "$STAGE" "$CANDIDATES"
    mkdir -p "$STAGE"
    printf '%s\n' "$SHA" > "$APPROVAL"
    printf '%s\n' "$SHA" > "$MARKER"
    cat > "$PROVENANCE" <<EOF
repository=total-water-design/total-water-design-suite
authorized_ref=refs/heads/alpha
authorized_remote_sha=$SHA
approved_sha=$SHA
checked_out_sha=$SHA
prepared_at_utc=2026-08-30T12:00:00Z
EOF
    rm -f "$LIVE" "$FIXTURE/deployer_started" "$FIXTURE/release_deployer" \
        "$FIXTURE/staging_code_executed" "$FIXTURE/deployed_ordinary"
    make_bundle
}

assert_rejected() {
    local label="$1"
    shift
    if "$@" >"$FIXTURE/$label.out" 2>&1; then
        echo "not ok - $label (unexpected success)"
        cat "$FIXTURE/$label.out"
        exit 1
    fi
    echo "ok - $label"
}

write_success_deployer() {
    cat > "$DEPLOYER" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
source_tree="\$1"
cat "\$source_tree/ordinary.txt" > '$FIXTURE/deployed_ordinary'
[[ "\$(cat "\$source_tree/deploy/helper.py")" == '# safe script bytes' ]]
printf '%s\n' '$SHA' > '$LIVE'
EOF
    chmod +x "$DEPLOYER"
}

# 1. Approved SHA plus an untampered bundle succeeds.
reset_fixture
write_success_deployer
"$GATE" >"$FIXTURE/success.out" 2>&1
[[ "$(cat "$FIXTURE/deployed_ordinary")" == "approved bytes" ]]
grep -qx "approved_sha=$SHA" "$EVIDENCE/$SHA.deployment"
grep -qx "service=totalrodesign.service version=$SHA state=active" "$EVIDENCE/$SHA.deployment"
echo "ok - approved SHA and untampered bundle deploy exact commit bytes"

# 9. Success consumes approval exactly once.
[[ ! -s "$APPROVAL" ]]
assert_rejected "successful deployment approval cannot be consumed twice" "$GATE"

# 2. Marker mismatch fails.
reset_fixture
printf '%040d\n' 0 > "$MARKER"
assert_rejected "marker mismatch fails" "$GATE"

# 2a. Incomplete or mismatched provenance fails before root imports the bundle.
reset_fixture
sed -i "s/^checked_out_sha=.*/checked_out_sha=$(printf '%040d' 0)/" "$PROVENANCE"
assert_rejected "provenance SHA mismatch fails" "$GATE"
reset_fixture
mv "$PROVENANCE" "$FIXTURE/real-provenance"
ln -s "$FIXTURE/real-provenance" "$PROVENANCE"
assert_rejected "provenance symlink substitution fails closed" "$GATE"

# 3. Corrupted bundle fails.
reset_fixture
printf 'corruption' >> "$BUNDLE"
truncate -s 64 "$BUNDLE"
assert_rejected "corrupted bundle fails" "$GATE"

# 4. A valid bundle that omits the approved SHA fails.
reset_fixture
make_bundle "$OTHER_REPO"
assert_rejected "bundle without approved SHA fails" "$GATE"

# 5. Ordinary runner-staging changes cannot affect the materialized source.
reset_fixture
printf 'tampered staging bytes\n' > "$STAGE/ordinary.txt"
write_success_deployer
"$GATE" >"$FIXTURE/ordinary-tamper.out" 2>&1
[[ "$(cat "$FIXTURE/deployed_ordinary")" == "approved bytes" ]]
echo "ok - ordinary staging modification cannot affect deployed source"

# 6. Staged deploy scripts are never executed by root.
reset_fixture
mkdir -p "$STAGE/deploy"
cat > "$STAGE/deploy/helper.py" <<EOF
#!/usr/bin/env bash
touch '$FIXTURE/staging_code_executed'
EOF
chmod +x "$STAGE/deploy/helper.py"
write_success_deployer
"$GATE" >"$FIXTURE/script-tamper.out" 2>&1
[[ ! -e "$FIXTURE/staging_code_executed" ]]
echo "ok - staged deploy script modification cannot cause execution"

# 7. Marker and bundle symlink substitutions fail closed.
reset_fixture
mv "$MARKER" "$FIXTURE/real-marker"
ln -s "$FIXTURE/real-marker" "$MARKER"
assert_rejected "marker symlink substitution fails closed" "$GATE"
reset_fixture
mv "$BUNDLE" "$FIXTURE/real-bundle"
ln -s "$FIXTURE/real-bundle" "$BUNDLE"
assert_rejected "bundle symlink substitution fails closed" "$GATE"

# 8. Failed deployment preserves approval.
reset_fixture
cat > "$DEPLOYER" <<'EOF'
#!/usr/bin/env bash
exit 42
EOF
chmod +x "$DEPLOYER"
assert_rejected "failed deployment is rejected" "$GATE"
[[ "$(tr -d '\r\n ' < "$APPROVAL")" == "$SHA" ]]
echo "ok - failed deployment preserves approval"

# 10. A concurrent invocation is rejected while the first holds the lock.
reset_fixture
cat > "$DEPLOYER" <<EOF
#!/usr/bin/env bash
touch '$FIXTURE/deployer_started'
while [[ ! -f '$FIXTURE/release_deployer' ]]; do sleep 0.05; done
printf '%s\n' '$SHA' > '$LIVE'
EOF
chmod +x "$DEPLOYER"
"$GATE" >"$FIXTURE/first.out" 2>&1 &
first_pid=$!
while [[ ! -f "$FIXTURE/deployer_started" ]]; do kill -0 "$first_pid"; sleep 0.05; done
assert_rejected "concurrent invocation is rejected" "$GATE"
grep -q "another Alpha deployment gate invocation is active" \
    "$FIXTURE/concurrent invocation is rejected.out"
touch "$FIXTURE/release_deployer"
wait "$first_pid"
[[ ! -s "$APPROVAL" ]]
echo "ok - first concurrent invocation completes and consumes approval"

# 11. The gate invokes the real privileged deployer with its root-owned
# candidate.  The wrapper makes runner staging unreadable immediately before
# exec; success therefore proves the deployer neither reads nor executes it.
reset_fixture
APP_ROOT="$FIXTURE/app-root"
BACKUPS="$FIXTURE/backups"
FP_HELPER="$FIXTURE/requirements_fingerprint.py"
REAL_DEPLOYER="$FIXTURE/real-deployer"
LIVE_VENV="$FIXTURE/live-venv"
cp "$ROOT/deploy/requirements_fingerprint.py" "$FP_HELPER"
chmod 644 "$FP_HELPER"
mkdir -p "$APP_ROOT/app" "$LIVE_VENV/bin"
printf 'old live bytes\n' > "$APP_ROOT/app/ordinary.txt"
ln -s /usr/bin/python3 "$LIVE_VENV/bin/python"
LIVE_FP="$(/usr/bin/python3 "$FP_HELPER" "$REPO/requirements-server.txt" --repo-root "$REPO")"
printf '%s\n' "$LIVE_FP" > "$LIVE_VENV/.twds_requirements_fingerprint"
ln -s "$LIVE_VENV" "$APP_ROOT/venv"
cat > "$MOCKBIN/curl" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$MOCKBIN/curl"
sed \
    -e "s|^CANDIDATE_ROOT=.*|CANDIDATE_ROOT=$CANDIDATES|" \
    -e "s|^APP_ROOT=.*|APP_ROOT=$APP_ROOT|" \
    -e "s|^BACKUP_ROOT=.*|BACKUP_ROOT=$BACKUPS|" \
    -e "s|^FP_HELPER=.*|FP_HELPER=$FP_HELPER|" \
    -e 's|^SERVICE_USER=.*|SERVICE_USER=paperclip|' \
    -e 's|^if \[\[ \$EUID -ne 0 \]\]; then|if false; then|' \
    -e 's|== root:root|== paperclip:paperclip|g' \
    -e 's|^  \[\[ "\$owner" == root && "\$group" == root \]\] \|\| fail.*|  : # ownership test cannot run unprivileged|' \
    -e 's|^chown |: test-chown |' \
    -e 's|^  chown |  : test-chown |' \
    "$ROOT/deploy/twds-alpha-deploy" > "$REAL_DEPLOYER"
chmod +x "$REAL_DEPLOYER"
cat > "$DEPLOYER" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
chmod 000 '$STAGE'
'$REAL_DEPLOYER' "\$1"
cp "\$1/.deployment_commit" '$LIVE'
EOF
chmod +x "$DEPLOYER"
mkdir -p "$STAGE/deploy"
cat > "$STAGE/deploy/verify_templates.py" <<EOF
#!/usr/bin/env bash
touch '$FIXTURE/staging_code_executed'
EOF
chmod +x "$STAGE/deploy/verify_templates.py"
"$GATE" >"$FIXTURE/real-deployer.out" 2>&1
chmod 700 "$STAGE"
[[ "$(cat "$APP_ROOT/app/ordinary.txt")" == "approved bytes" ]]
[[ ! -e "$FIXTURE/staging_code_executed" ]]
grep -q "VALIDATING ROOT-OWNED CANDIDATE TREE" "$FIXTURE/real-deployer.out"
echo "ok - real deployer exclusively deploys the root-owned candidate, not runner staging"
