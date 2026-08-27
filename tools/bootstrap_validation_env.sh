#!/usr/bin/env bash

set -Eeuo pipefail

readonly GET_PIP_URL="https://bootstrap.pypa.io/get-pip.py"
readonly GET_PIP_SHA256="fb24e693bab954209a063d90953621412ccad4a500905a726286e038f508ddf6"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
readonly TARGET="${1:-${HOME}/.twds-validation-venv}"
readonly GET_PIP_PATH="$TARGET/get-pip.py"

IMPORT_GATE="NOT RUN"
BROWSER_GATE="NOT RUN"
APP_GATE="NOT RUN"
VERSIONS="unavailable"

print_summary() {
    local exit_code=$?
    if (( exit_code != 0 )); then
        [[ "$IMPORT_GATE" == "RUNNING" ]] && IMPORT_GATE="FAIL"
        [[ "$BROWSER_GATE" == "RUNNING" ]] && BROWSER_GATE="FAIL"
        [[ "$APP_GATE" == "RUNNING" ]] && APP_GATE="FAIL"
    fi

    printf '\nTWDS validation environment summary\n'
    printf '  Venv:             %s\n' "$TARGET"
    printf '  Versions:         %s\n' "$VERSIONS"
    printf '  Import gate:      %s\n' "$IMPORT_GATE"
    printf '  Chromium gate:    %s\n' "$BROWSER_GATE"
    printf '  Application gate: %s\n' "$APP_GATE"
    if (( exit_code == 0 )); then
        printf '  Overall:          PASS\n'
    else
        printf '  Overall:          FAIL (exit %d)\n' "$exit_code"
    fi
}
trap print_summary EXIT

command -v python3 >/dev/null || { echo "ERROR: python3 is required but was not found." >&2; exit 1; }
command -v curl >/dev/null || { echo "ERROR: curl is required to fetch $GET_PIP_URL." >&2; exit 1; }

cd -- "$REPO_ROOT"
mkdir -p -- "$TARGET"
python3 -m venv --without-pip "$TARGET"
curl --fail --silent --show-error --location "$GET_PIP_URL" --output "$GET_PIP_PATH"
actual_sha256="$(sha256sum "$GET_PIP_PATH" | awk '{print $1}')"
if [[ "$actual_sha256" != "$GET_PIP_SHA256" ]]; then
    echo "ERROR: get-pip.py SHA-256 mismatch; refusing to execute it." >&2
    echo "Expected: $GET_PIP_SHA256" >&2
    echo "Actual:   $actual_sha256" >&2
    exit 1
fi

"$TARGET/bin/python" "$GET_PIP_PATH"
"$TARGET/bin/python" -m pip install -r requirements.txt pytest playwright

if ! find "${HOME}/.cache/ms-playwright" -maxdepth 1 -type d \
    \( -name 'chromium-*' -o -name 'chromium_headless_shell-*' \) \
    -print -quit 2>/dev/null | grep -q .; then
    "$TARGET/bin/python" -m playwright install chromium
fi

IMPORT_GATE="RUNNING"
"$TARGET/bin/python" - <<'PY'
import flask
import numpy
import playwright
import pytest
PY
IMPORT_GATE="PASS"

VERSIONS="$("$TARGET/bin/python" - <<'PY'
from importlib.metadata import version
print(", ".join(f"{name} {version(name)}" for name in ("pytest", "flask", "numpy", "playwright")))
PY
)"

BROWSER_GATE="RUNNING"
"$TARGET/bin/python" - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    try:
        page = browser.new_page()
        page.goto("data:text/html,<h1>ok</h1>")
        assert page.locator("h1").inner_text() == "ok"
    finally:
        browser.close()
PY
BROWSER_GATE="PASS"

APP_GATE="RUNNING"
TOTALRO_DATA_DIR="$(mktemp -d "${TMPDIR:-/tmp}/twds-validation-data.XXXXXX")"
export TOTALRO_DATA_DIR
cleanup_data_dir() { rm -rf -- "$TOTALRO_DATA_DIR"; }
trap cleanup_data_dir RETURN
"$TARGET/bin/python" - <<'PY'
import threading
import urllib.request
from werkzeug.serving import make_server
from app import app

server = make_server("127.0.0.1", 0, app)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=15) as response:
        assert response.status == 200, response.status
finally:
    server.shutdown()
    thread.join(timeout=15)
    server.server_close()
PY
rm -rf -- "$TOTALRO_DATA_DIR"
trap - RETURN
APP_GATE="PASS"
