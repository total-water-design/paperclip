#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo bash deploy/install_ubuntu_24_04.sh" >&2
  exit 1
fi

APP_SOURCE="${1:-$(pwd)}"
APP_ROOT=/opt/totalrodesign
APP_DIR=$APP_ROOT/app
VENV=$APP_ROOT/venv
DATA_DIR=/var/lib/totalrodesign
CONFIG_DIR=/etc/totalrodesign
SERVICE_USER=totalrodesign
BACKUP_ROOT=/var/backups/totalrodesign
STAMP="$(date +%Y%m%d-%H%M%S)"
CANDIDATE_VENV="$APP_ROOT/venv-candidate-$STAMP-$$"
APP_ROLLBACK="$APP_ROOT/app.rollback-$STAMP-$$"
VENV_ROLLBACK="$APP_ROOT/venv.rollback-$STAMP-$$"
CUTOVER=0
SERVICE_WAS_ACTIVE=0

if systemctl is-active --quiet totalrodesign 2>/dev/null; then
  SERVICE_WAS_ACTIVE=1
fi

rollback_on_error() {
  rc=$?
  echo >&2
  echo "Installation failed (exit $rc)." >&2

  if [[ $CUTOVER -eq 1 ]]; then
    echo "Rolling back application files and virtual environment..." >&2
    rm -rf "$APP_DIR"
    if [[ -e "$APP_ROLLBACK" || -L "$APP_ROLLBACK" ]]; then
      mv "$APP_ROLLBACK" "$APP_DIR"
    fi

    rm -rf "$VENV"
    if [[ -e "$VENV_ROLLBACK" || -L "$VENV_ROLLBACK" ]]; then
      mv "$VENV_ROLLBACK" "$VENV"
    fi

    systemctl daemon-reload || true
    if [[ $SERVICE_WAS_ACTIVE -eq 1 ]]; then
      systemctl restart totalrodesign || true
    fi
  fi

  rm -rf "$CANDIDATE_VENV"
  exit "$rc"
}
trap rollback_on_error ERR

apt-get update
apt-get install -y python3-venv python3-pip nginx rsync

id -u "$SERVICE_USER" >/dev/null 2>&1 || \
  useradd --system --home "$APP_ROOT" --shell /usr/sbin/nologin "$SERVICE_USER"
mkdir -p "$APP_ROOT" "$DATA_DIR" "$CONFIG_DIR" "$BACKUP_ROOT" \
  "$DATA_DIR/feedback_outbox" "$DATA_DIR/mail_outbox"

# Back up the persistent production data and protected environment before any
# candidate installation work. The application/database are never recreated.
BACKUP_DIR="$BACKUP_ROOT/preinstall-$STAMP-$$"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
if [[ -f "$DATA_DIR/totalrodesign.db" ]]; then
  python3 - "$DATA_DIR/totalrodesign.db" "$BACKUP_DIR/totalrodesign.db" <<'PY_BACKUP'
import sqlite3, sys
source, target = sys.argv[1], sys.argv[2]
with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
PY_BACKUP
  chmod 600 "$BACKUP_DIR/totalrodesign.db"
fi
if [[ -f "$CONFIG_DIR/totalrodesign.env" ]]; then
  cp -a "$CONFIG_DIR/totalrodesign.env" "$BACKUP_DIR/totalrodesign.env"
  chmod 600 "$BACKUP_DIR/totalrodesign.env"
fi
if compgen -G "$BACKUP_DIR/*" >/dev/null; then
  sha256sum "$BACKUP_DIR"/* > "$BACKUP_DIR/SHA256SUMS.txt"
  chmod 600 "$BACKUP_DIR/SHA256SUMS.txt"
fi
echo "Persistent-data backup prepared at $BACKUP_DIR"

# Build and validate the candidate release BEFORE replacing the live code.
echo "Building isolated candidate virtual environment..."
rm -rf "$CANDIDATE_VENV"
python3 -m venv "$CANDIDATE_VENV"
"$CANDIDATE_VENV/bin/pip" install --upgrade pip setuptools wheel
"$CANDIDATE_VENV/bin/pip" install -r "$APP_SOURCE/requirements-server.txt"

echo "Compiling every Jinja template in the candidate release..."
"$CANDIDATE_VENV/bin/python" "$APP_SOURCE/deploy/verify_templates.py"

echo "Running isolated authentication/server smoke test against the candidate release..."
"$CANDIDATE_VENV/bin/python" "$APP_SOURCE/deploy/verify_auth_install.py"

echo "Candidate validation passed. Beginning live cutover..."
if [[ $SERVICE_WAS_ACTIVE -eq 1 ]]; then
  systemctl stop totalrodesign
fi

CUTOVER=1
rm -rf "$APP_ROLLBACK" "$VENV_ROLLBACK"
if [[ -e "$APP_DIR" || -L "$APP_DIR" ]]; then
  mv "$APP_DIR" "$APP_ROLLBACK"
fi
mkdir -p "$APP_DIR" "$APP_DIR/instance"
rsync -a --delete \
  --exclude '.build_venv*' --exclude '__pycache__' --exclude '.pytest_cache' \
  --exclude 'dist' --exclude 'build' \
  "$APP_SOURCE/" "$APP_DIR/"
mkdir -p "$APP_DIR/instance"

# Keep the validated environment at its original path (venv script shebangs
# contain that path) and point the stable service path at it with a symlink.
if [[ -e "$VENV" || -L "$VENV" ]]; then
  mv "$VENV" "$VENV_ROLLBACK"
fi
ln -s "$CANDIDATE_VENV" "$VENV"

if [[ ! -f "$CONFIG_DIR/totalrodesign.env" ]]; then
  cp "$APP_DIR/deploy/totalrodesign.env.example" "$CONFIG_DIR/totalrodesign.env"
  echo
  echo "Created $CONFIG_DIR/totalrodesign.env"
  echo "EDIT IT BEFORE STARTING THE SERVICE, especially TOTALRO_SECRET_KEY and SMTP password."
fi
chown root:"$SERVICE_USER" "$CONFIG_DIR/totalrodesign.env"
chmod 640 "$CONFIG_DIR/totalrodesign.env"

cp "$APP_DIR/deploy/totalrodesign.service" /etc/systemd/system/totalrodesign.service
cp "$APP_DIR/deploy/nginx-totalrodesign.conf" /etc/nginx/sites-available/totalrodesign
ln -sfn /etc/nginx/sites-available/totalrodesign /etc/nginx/sites-enabled/totalrodesign
rm -f /etc/nginx/sites-enabled/default

# Application code and virtual environment are root-owned/read-only to the
# service. Only the database/outboxes and Flask instance directory are writable.
chown -R root:"$SERVICE_USER" "$APP_ROOT"
chmod -R g+rX,o-rwx "$APP_ROOT"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$DATA_DIR" "$APP_DIR/instance"
chmod 750 "$APP_ROOT" "$APP_DIR" "$APP_DIR/instance" "$DATA_DIR"

nginx -t
systemctl daemon-reload

if systemctl is-active --quiet nginx; then
  systemctl reload nginx
fi
if [[ $SERVICE_WAS_ACTIVE -eq 1 ]]; then
  systemctl restart totalrodesign
  systemctl is-active --quiet totalrodesign
fi

trap - ERR
CUTOVER=0

# Cutover succeeded; previous code/environment are no longer needed.
rm -rf "$APP_ROLLBACK" "$VENV_ROLLBACK"

echo
printf '%s\n' \
  "Files installed." \
  "Candidate release passed template and authenticated runtime validation before live cutover." \
  "1. Edit: sudo nano /etc/totalrodesign/totalrodesign.env" \
  "2. Create the first administrator using deploy/DEPLOY_AWS_AUTH.md" \
  "3. Start: sudo systemctl enable --now totalrodesign nginx" \
  "Existing active services were reloaded/restarted after validation."
