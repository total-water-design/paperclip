#!/usr/bin/env bash
set -euo pipefail

GATED_SUDOERS_PATTERN='NOPASSWD:[[:space:]]*/usr/local/sbin/twds-alpha-deploy-gated([[:space:]]|$)'
UNGATED_SUDOERS_PATTERN='NOPASSWD:[[:space:]]*/usr/local/sbin/twds-alpha-deploy([[:space:]]|$)'

check_sudoers_contract() {
  local sudoers_output="$1"
  printf '%s\n' "$sudoers_output"

  if ! grep -Eq "$GATED_SUDOERS_PATTERN" <<<"$sudoers_output"; then
    if grep -Eq "$UNGATED_SUDOERS_PATTERN" <<<"$sudoers_output"; then
      echo 'ERROR: ungated deployer bypass path is permitted: /usr/local/sbin/twds-alpha-deploy' >&2
    else
      echo 'ERROR: gated deployer is not permitted' >&2
    fi
    return 1
  fi

  if grep -Eq "$UNGATED_SUDOERS_PATTERN" <<<"$sudoers_output"; then
    echo 'ERROR: ungated deployer bypass path is permitted: /usr/local/sbin/twds-alpha-deploy' >&2
    return 1
  fi

  local remaining_nopasswd
  remaining_nopasswd="$(printf '%s\n' "$sudoers_output" \
    | sed -E "s#$GATED_SUDOERS_PATTERN##g" \
    | grep -E 'NOPASSWD:' || true)"
  if [[ -n "$remaining_nopasswd" ]]; then
    echo 'ERROR: unexpected additional passwordless sudo rule' >&2
    printf '%s\n' "$remaining_nopasswd" >&2
    return 1
  fi
}

expect_pass() {
  local name="$1"
  local fixture="$2"
  if ! check_sudoers_contract "$fixture" >/dev/null; then
    echo "FAIL - $name unexpectedly rejected" >&2
    return 1
  fi
  echo "PASS - $name"
}

expect_fail() {
  local name="$1"
  local fixture="$2"
  local expected_message="$3"
  local output
  if output="$(check_sudoers_contract "$fixture" 2>&1)"; then
    echo "FAIL - $name unexpectedly accepted" >&2
    return 1
  fi
  if ! grep -Fq "$expected_message" <<<"$output"; then
    echo "FAIL - $name did not name the expected violation" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
  echo "PASS - $name rejected with: $expected_message"
}

GATED_ONLY=$'User ubuntu may run the following commands on runner:\n    (ALL) NOPASSWD: /usr/local/sbin/twds-alpha-deploy-gated'
UNGATED_ONLY=$'User ubuntu may run the following commands on runner:\n    (ALL) NOPASSWD: /usr/local/sbin/twds-alpha-deploy'
BOTH_PRESENT=$'User ubuntu may run the following commands on runner:\n    (ALL) NOPASSWD: /usr/local/sbin/twds-alpha-deploy-gated\n    (ALL) NOPASSWD: /usr/local/sbin/twds-alpha-deploy'
UNRELATED_NOPASSWD=$'User ubuntu may run the following commands on runner:\n    (ALL) NOPASSWD: /usr/local/sbin/twds-alpha-deploy-gated\n    (ALL) NOPASSWD: ALL'

expect_pass 'gated-only fixture' "$GATED_ONLY"
expect_fail 'ungated-only fixture' "$UNGATED_ONLY" \
  'ungated deployer bypass path is permitted: /usr/local/sbin/twds-alpha-deploy'
expect_fail 'both-present fixture' "$BOTH_PRESENT" \
  'ungated deployer bypass path is permitted: /usr/local/sbin/twds-alpha-deploy'
expect_fail 'unrelated NOPASSWD fixture' "$UNRELATED_NOPASSWD" \
  'unexpected additional passwordless sudo rule'
