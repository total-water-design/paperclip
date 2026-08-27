#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE="$(mktemp -d)"
trap 'rm -rf "$FIXTURE"' EXIT

SHA=0123456789abcdef0123456789abcdef01234567
APPROVAL="$FIXTURE/approved_sha"
LOCK="$FIXTURE/deploy.lock"
STAGE="$FIXTURE/staging_sha"
LIVE="$FIXTURE/live_sha"
DEPLOYER="$FIXTURE/deployer"
GATE="$FIXTURE/gate"

sed \
    -e "s|^APPROVAL=.*|APPROVAL=$APPROVAL|" \
    -e "s|^LOCK=.*|LOCK=$LOCK|" \
    -e "s|^STAGE_MARKER=.*|STAGE_MARKER=$STAGE|" \
    -e "s|^LIVE_MARKER=.*|LIVE_MARKER=$LIVE|" \
    -e "s|^DEPLOYER=.*|DEPLOYER=$DEPLOYER|" \
    -e 's|^\[\[ \$EUID -eq 0 \]\].*|: # root check covered by production syntax check|' \
    "$ROOT/deploy/twds-alpha-deploy-gated" > "$GATE"
chmod +x "$GATE"

reset_fixture() {
    printf '%s\n' "$SHA" > "$APPROVAL"
    printf '%s\n' "$SHA" > "$STAGE"
    rm -f "$LIVE"
}

assert_rejected() {
    local label=$1
    shift
    if "$@" >"$FIXTURE/$label.out" 2>&1; then
        echo "not ok - $label (unexpected success)"
        cat "$FIXTURE/$label.out"
        exit 1
    fi
    echo "ok - $label"
}

reset_fixture
cat > "$DEPLOYER" <<EOF
#!/usr/bin/env bash
printf '%s\n' '$SHA' > '$LIVE'
EOF
chmod +x "$DEPLOYER"
"$GATE" >"$FIXTURE/success.out" 2>&1
[[ ! -s "$APPROVAL" ]]
echo "ok - deployer succeeds and approval is consumed"

assert_rejected "replay with consumed approval is rejected" "$GATE"

reset_fixture
cat > "$DEPLOYER" <<'EOF'
#!/usr/bin/env bash
exit 42
EOF
chmod +x "$DEPLOYER"
assert_rejected "deployer failure is rejected" "$GATE"
[[ "$(tr -d '\r\n ' < "$APPROVAL")" == "$SHA" ]]
echo "ok - deployer failure preserves approval"

reset_fixture
cat > "$DEPLOYER" <<EOF
#!/usr/bin/env bash
touch '$FIXTURE/deployer_started'
while [[ ! -f '$FIXTURE/release_deployer' ]]; do
    sleep 0.05
done
printf '%s\n' '$SHA' > '$LIVE'
EOF
chmod +x "$DEPLOYER"
"$GATE" >"$FIXTURE/first.out" 2>&1 &
first_pid=$!
while [[ ! -f "$FIXTURE/deployer_started" ]]; do
    kill -0 "$first_pid"
    sleep 0.05
done
assert_rejected "concurrent invocation is rejected" "$GATE"
grep -q "another Alpha deployment gate invocation is active" "$FIXTURE/concurrent invocation is rejected.out"
touch "$FIXTURE/release_deployer"
wait "$first_pid"
[[ ! -s "$APPROVAL" ]]
echo "ok - first concurrent invocation completes and consumes approval"
