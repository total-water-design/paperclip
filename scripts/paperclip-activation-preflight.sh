#!/usr/bin/env bash
set -euo pipefail

fail() { printf 'paperclip activation preflight: %s\n' "$*" >&2; exit 1; }
for name in PAPERCLIP_ARTIFACT_MANIFEST PAPERCLIP_ARTIFACT_IDENTITY PAPERCLIP_EXECUTABLE; do
  [[ -n "${!name:-}" ]] || fail "missing $name"
  [[ -f "${!name}" && ! -L "${!name}" ]] || fail "$name must name a regular non-symlink file"
done
script_dir="$(cd "$(dirname "$0")" && pwd)"
verifier="${PAPERCLIP_ARTIFACT_VERIFIER:-$script_dir/paperclip-artifact-identity.mjs}"
[[ -f "$verifier" && ! -L "$verifier" ]] || fail "artifact verifier must be a regular non-symlink file: $verifier"
args=(preflight --manifest "$PAPERCLIP_ARTIFACT_MANIFEST" --identity "$PAPERCLIP_ARTIFACT_IDENTITY" --executable "$PAPERCLIP_EXECUTABLE")
[[ -z "${PAPERCLIP_ARTIFACT_ARCHIVE:-}" ]] || args+=(--archive "$PAPERCLIP_ARTIFACT_ARCHIVE")
if [[ -n "${PAPERCLIP_RUNTIME_PID_FILE:-}" && -s "$PAPERCLIP_RUNTIME_PID_FILE" ]]; then
  runtime_pid="$(tr -d '[:space:]' < "$PAPERCLIP_RUNTIME_PID_FILE")"
  [[ "$runtime_pid" =~ ^[0-9]+$ ]] || fail "runtime PID file is invalid"
  if kill -0 "$runtime_pid" 2>/dev/null; then
    [[ -n "${PAPERCLIP_RUNTIME_IDENTITY:-}" && -f "$PAPERCLIP_RUNTIME_IDENTITY" ]] || fail "a Paperclip runtime is active but has no identity record"
    args+=(--runtime-identity "$PAPERCLIP_RUNTIME_IDENTITY" --runtime-pid "$runtime_pid")
  fi
fi
exec "${PAPERCLIP_NODE:-node}" "$verifier" "${args[@]}"
