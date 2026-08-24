#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

# One-time root installation of the audited dependency-closure deployer.
# It does not rebuild the production venv and does not restart the service.

if [[ $EUID -ne 0 ]]; then
  echo "Run as an authorized root administrator." >&2
  exit 1
fi

SOURCE_ROOT="${1:-$(pwd)}"
APP_DIR=/opt/totalrodesign/app
VENV=/opt/totalrodesign/venv
LIB_DIR=/usr/local/lib/twds-alpha
DEPLOYER=/usr/local/sbin/twds-alpha-deploy
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FP_NAME=.twds_requirements_fingerprint

for f in \
  "$SOURCE_ROOT/deploy/requirements_fingerprint.py" \
  "$SOURCE_ROOT/deploy/twds-alpha-deploy"; do
  [[ -f "$f" ]] || { echo "Missing infrastructure source: $f" >&2; exit 1; }
done
[[ -x "$VENV/bin/python" ]] || { echo "Production venv is unavailable: $VENV" >&2; exit 1; }
[[ -f "$APP_DIR/requirements-server.txt" ]] || { echo "Live application requirements are unavailable." >&2; exit 1; }

# Validate the current, already-authorized production environment before
# associating its dependency closure fingerprint. No packages are installed.
"$VENV/bin/python" -m pip check
"$VENV/bin/python" "$APP_DIR/deploy/verify_templates.py"
"$VENV/bin/python" "$APP_DIR/deploy/verify_auth_install.py"
"$VENV/bin/python" - <<'PY'
import importlib.metadata as md
import pyotp
import cryptography
print("pyotp", md.version("pyotp"))
print("cryptography", cryptography.__version__)
print("gunicorn", md.version("gunicorn"))
PY

mkdir -p "$LIB_DIR"
if [[ -e "$DEPLOYER" ]]; then
  cp -a "$DEPLOYER" "$DEPLOYER.pre-dependency-closure-$STAMP"
  chmod 0500 "$DEPLOYER.pre-dependency-closure-$STAMP"
fi

install -o root -g root -m 0644 \
  "$SOURCE_ROOT/deploy/requirements_fingerprint.py" \
  "$LIB_DIR/requirements_fingerprint.py"
install -o root -g root -m 0750 \
  "$SOURCE_ROOT/deploy/twds-alpha-deploy" \
  "$DEPLOYER"

/usr/bin/python3 -m py_compile "$LIB_DIR/requirements_fingerprint.py"
bash -n "$DEPLOYER"

LIVE_FP="$(/usr/bin/python3 "$LIB_DIR/requirements_fingerprint.py" \
  "$APP_DIR/requirements-server.txt" --repo-root "$APP_DIR")"
[[ "$LIVE_FP" =~ ^[0-9a-f]{64}$ ]] || { echo "Invalid live dependency fingerprint." >&2; exit 1; }
printf '%s\n' "$LIVE_FP" > "$VENV/$FP_NAME"
chown root:root "$VENV/$FP_NAME"
chmod 0444 "$VENV/$FP_NAME"

# Preserve the deliberately narrow runner privilege. This installer does not
# edit sudoers. Existing policy should continue to authorize only DEPLOYER.
echo "DEPENDENCY_CLOSURE_HARDENING_INSTALLED=1"
echo "LIVE_VENV_REBUILT=0"
echo "SERVICE_RESTARTED=0"
echo "LIVE_FINGERPRINT=$LIVE_FP"
echo "DEPLOYER=$DEPLOYER"
