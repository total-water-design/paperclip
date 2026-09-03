# Root systemd Paperclip runbook

This runbook stages the root-managed unit at `deploy/systemd/paperclip.service`.
It is an operator procedure: do not run the install, enable, restart, or
destructive-recovery commands against a healthy instance until the production
host gate is approved.

## Invariants

- The unit runs `/usr/lib/paperclip/paperclip-preflight` and
  `/usr/lib/paperclip/paperclip-activation-preflight` before every start. The
  second gate binds the installed CLI to its certified source and rejects a live
  runtime carrying a different identity.
  It fails closed unless the selected config is exactly `local_trusted`,
  `private`, `127.0.0.1`, and port `3100`; public/LAN/custom binding and
  weakened deployment modes are rejected.
- The root-owned environment file names the actual `PAPERCLIP_EXECUTABLE` and
  `PAPERCLIP_NODE`; `/usr/local/bin/paperclipai` is not assumed. The preflight
  rejects a missing, symlinked, or non-executable binary.
- Preserve one existing instance and explicitly name its config, embedded
  PostgreSQL data, backup, local storage, and local-encrypted secrets-key
  paths. The preflight rejects missing paths, symlinks, group/other-writable
  state, a disabled backup, or mismatched config references.
- Do not put secret values in the unit or environment file. The secrets key is
  a file reference only; inline `PAPERCLIP_SECRETS_MASTER_KEY` is rejected.
- The bounded abnormal-restart policy is five starts in 60 seconds, followed by
  a five-second delay. Deliberate operator stops do not restart the service.

## Stage without changing the running process

Run these commands as root on the target host. They only inspect and stage
files; do not run `daemon-reload`, `enable`, `start`, `restart`, `kill`, or
`stop` in this section.

```sh
systemctl status paperclip.service --no-pager
curl -fsS http://127.0.0.1:3100/api/health | jq .
systemctl show paperclip.service -p MainPID --value
ps -fp "$(systemctl show paperclip.service -p MainPID --value)"

# Record actual existing instance paths before writing any service files.
old_pid="$(systemctl show paperclip.service -p MainPID --value)"
tr '\0' '\n' < "/proc/$old_pid/environ" | \
  grep -E '^(PAPERCLIP_HOME|PAPERCLIP_CONFIG|PAPERCLIP_INSTANCE_ID|DATABASE_URL)=' || true
```

Confirm that the recorded paths identify one existing instance. The root unit
supports only the mechanically checked private layout below. If the running
process has a different bind, deployment mode, path layout, database, or
secret provider, stop here and obtain a separately approved migration; do not
silently rewrite it.

Create the unit and environment file using the recorded existing paths (the
values below are examples and must match the running instance exactly):

```sh
install -d -o root -g root -m 0755 /etc/paperclip
install -o root -g root -m 0644 deploy/systemd/paperclip.service /etc/systemd/system/paperclip.service
install -d -o root -g root -m 0755 /usr/lib/paperclip
install -o root -g root -m 0755 deploy/systemd/paperclip-preflight /usr/lib/paperclip/paperclip-preflight
install -o root -g root -m 0755 scripts/paperclip-activation-preflight.sh /usr/lib/paperclip/paperclip-activation-preflight
install -o root -g paperclip -m 0640 /dev/null /etc/paperclip/paperclip.env
cat >/etc/paperclip/paperclip.env <<'EOF'
PAPERCLIP_HOME=/var/lib/paperclip
PAPERCLIP_CONFIG=/var/lib/paperclip/instances/default/config.json
PAPERCLIP_INSTANCE_ID=default
PAPERCLIP_EXECUTABLE=/opt/paperclip/current/bin/paperclipai
PAPERCLIP_NODE=/usr/bin/node
PAPERCLIP_DATA_DIR=/var/lib/paperclip/instances/default/db
PAPERCLIP_BACKUP_DIR=/var/lib/paperclip/instances/default/data/backups
PAPERCLIP_STORAGE_DIR=/var/lib/paperclip/instances/default/data/storage
PAPERCLIP_SECRETS_KEY_FILE=/var/lib/paperclip/instances/default/secrets/master.key
PAPERCLIP_ARTIFACT_MANIFEST=/opt/paperclip/current/paperclipai.certification.json
PAPERCLIP_ARTIFACT_IDENTITY=/opt/paperclip/current/node_modules/paperclipai/dist/paperclip-artifact-identity.json
PAPERCLIP_ARTIFACT_ARCHIVE=/opt/paperclip/current/artifacts/paperclipai.tgz
PAPERCLIP_RUNTIME_PID_FILE=/run/paperclip/paperclip.pid
PAPERCLIP_RUNTIME_IDENTITY=/run/paperclip/paperclip-runtime-identity.json
PAPERCLIP_SERVICE_MANAGED=1
EOF
chown root:paperclip /etc/paperclip/paperclip.env
chmod 0640 /etc/paperclip/paperclip.env
systemd-analyze verify /etc/systemd/system/paperclip.service
/usr/lib/paperclip/paperclip-preflight
/usr/lib/paperclip/paperclip-activation-preflight
```

Before this preflight can pass, `config.json` must contain absolute paths equal
to the five corresponding `PAPERCLIP_*_DIR` / `PAPERCLIP_SECRETS_KEY_FILE`
values, with `database.mode="embedded-postgres"`, an enabled backup, local-disk
storage, and `secrets.provider="local_encrypted"`. All paths must be inside
`$PAPERCLIP_HOME/instances/$PAPERCLIP_INSTANCE_ID`, exist before activation,
and not be group/other writable. Do not include `DATABASE_URL`, API keys, or
other secret values in shell history or the environment file.

Create release artifacts only from a clean checkout with
`PAPERCLIP_SOURCE_SHA=$(git rev-parse HEAD) corepack pnpm build:npm:certified`.
The command rejects abbreviated or false labels and tracked dirty state. It
uses the commit timestamp, sorted entries, and zero numeric ownership for the
archive and emits its certification manifest alongside it. If the PID file
names a live process, activation additionally requires a runtime identity with
the certified `sourceSha` and `executableSha256`; an absent or stale identity
fails closed. Keep the archive, installed identity, and certification sidecar
together as one release unit.

## Production-host gate: install and health verification

Only after explicit approval, make a restorable copy of the previous unit and
reload the supervisor. These commands are intentionally operational and must
not be run during code staging.

```sh
install -d -m 0700 /root/paperclip-service-rollback
test ! -e /etc/systemd/system/paperclip.service || \
  cp -a /etc/systemd/system/paperclip.service /root/paperclip-service-rollback/paperclip.service.previous
test ! -e /etc/paperclip/paperclip.env || \
  cp -a /etc/paperclip/paperclip.env /root/paperclip-service-rollback/paperclip.env.previous
test ! -e /usr/lib/paperclip/paperclip-preflight || \
  cp -a /usr/lib/paperclip/paperclip-preflight /root/paperclip-service-rollback/paperclip-preflight.previous
/usr/lib/paperclip/paperclip-preflight
systemctl daemon-reload
systemctl enable paperclip.service
systemctl start paperclip.service
systemctl is-active --quiet paperclip.service
curl -fsS http://127.0.0.1:3100/api/health | jq -e '.status == "ok"'
systemctl show paperclip.service -p MainPID -p ActiveState -p NRestarts --no-pager
```

`systemctl start` is safe only when no other Paperclip process owns the same
instance. The foreground-run single-writer guard protects normal starts; do not
use `paperclipai run --force` for the service.

## Destructive supervisor recovery test

Run only after the unit is active and the production-host gate specifically
authorizes a brief interruption. This deliberately terminates the managed main
PID, then proves that systemd starts a replacement and health returns without
Board intervention.

```sh
before_pid="$(systemctl show paperclip.service -p MainPID --value)"
test "$before_pid" -gt 1
systemctl kill --signal=SIGKILL --kill-who=main paperclip.service
timeout 60 sh -c 'until systemctl is-active --quiet paperclip.service && curl -fsS http://127.0.0.1:3100/api/health | jq -e '.status == "ok"' >/dev/null; do sleep 1; done'
after_pid="$(systemctl show paperclip.service -p MainPID --value)"
test "$after_pid" -gt 1 && test "$after_pid" != "$before_pid"
systemctl show paperclip.service -p ActiveState -p NRestarts -p ExecMainStatus --no-pager
```

## Orphan and heartbeat reconciliation verification

Before the destructive test, record any active heartbeat run IDs through the
Board API. After recovery, inspect the startup reconciliation log and require
each recorded run to be either still running, safely finalized, or explicitly
requeued/recovered; no run may disappear silently.

```sh
journalctl -u paperclip.service --since '-5 min' --no-pager | \
  grep -Ei 'startup heartbeat recovery|orphan|reconc|lost|requeued|adopted'
curl -fsS http://127.0.0.1:3100/api/health | jq -e '.status == "ok"'
```

For each recorded run, use the authenticated Board API to retrieve
`/api/heartbeat-runs/<run-id>` and retain the status evidence with the change
record. If any run is lost without a recorded recovery disposition, stop and
open a recovery issue before declaring the change successful.

## Rollback

If startup, health, or reconciliation fails, restore the backed-up unit and
environment file, reload systemd, and restart only under an approved production
gate. The instance state is intentionally left untouched.

```sh
cp -a /root/paperclip-service-rollback/paperclip.service.previous /etc/systemd/system/paperclip.service
cp -a /root/paperclip-service-rollback/paperclip.env.previous /etc/paperclip/paperclip.env
cp -a /root/paperclip-service-rollback/paperclip-preflight.previous /usr/lib/paperclip/paperclip-preflight
systemctl daemon-reload
systemctl restart paperclip.service
curl -fsS http://127.0.0.1:3100/api/health | jq -e '.status == "ok"'
```

Do not delete `/var/lib/paperclip`, instance configuration, embedded PostgreSQL
data, backups, storage, or secrets as part of rollback.
