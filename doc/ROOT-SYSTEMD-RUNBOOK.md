# Root systemd Paperclip runbook

This runbook stages the root-managed unit at `deploy/systemd/paperclip.service`.
It is an operator procedure: do not run the install, enable, restart, or
destructive-recovery commands against a healthy instance until the production
host gate is approved.

## Invariants

- The unit runs `/usr/lib/paperclip/paperclip-preflight` before every start.
  It fails closed unless the selected config is exactly `local_trusted`,
  `private`, `127.0.0.1`, and port `3100`; public/LAN/custom binding and
  weakened deployment modes are rejected.
- This candidate is fixed to `WorkingDirectory=/home/paperclip`,
  `PAPERCLIP_HOME=/home/paperclip/.paperclip`, engineering workspaces at
  `/home/paperclip/workspaces`, and the checked shim
  `/home/paperclip/.local/bin/paperclipai`, executed by `/usr/bin/node`.
  The preflight rejects any different home, workspace, shim, or Node path.
- Preserve the named existing instance and explicitly name its config, embedded
  PostgreSQL data, backup, local storage, and local-encrypted secrets-key
  paths. The preflight rejects missing paths, symlinks, group/other-writable
  state, a disabled backup, or mismatched config references.
- Do not put secret values in the unit or environment file. The secrets key is
  a file reference only; inline `PAPERCLIP_SECRETS_MASTER_KEY` is rejected.
- The bounded abnormal-restart policy is five starts in 60 seconds, followed by
  a five-second delay. Deliberate operator stops do not restart the service.
- `ProtectSystem=strict`, `ProtectHome=read-only`, and the unit's write allow
  list permit only Paperclip state, engineering workspaces, and explicit
  agent/runtime/tool state (`.codex`, `.claude`, `.cache`, and `.local/share`).
  The network-only Bubblewrap spawn path remains usable because it constructs
  a usable `/dev`: fresh-root filesystems construct one with Bubblewrap's
  `--dev /dev`, while network-only spawns retain it with `--dev-bind /dev /dev`.

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

Confirm that the recorded paths identify the existing instance at
`/home/paperclip/.paperclip/instances/default`. This candidate supports only
the mechanically checked private layout below. If the running process has a
different bind, deployment mode, path layout, database, or secret provider,
stop here and obtain a separately approved migration; do not silently rewrite
it.

Create the unit and environment file using the recorded existing paths (the
values below are examples and must match the running instance exactly):

```sh
install -d -o root -g root -m 0755 /etc/paperclip
install -o root -g root -m 0644 deploy/systemd/paperclip.service /etc/systemd/system/paperclip.service
install -d -o root -g root -m 0755 /usr/lib/paperclip
install -o root -g root -m 0755 deploy/systemd/paperclip-preflight /usr/lib/paperclip/paperclip-preflight
install -o root -g paperclip -m 0640 /dev/null /etc/paperclip/paperclip.env
cat >/etc/paperclip/paperclip.env <<'EOF'
PAPERCLIP_HOME=/home/paperclip/.paperclip
PAPERCLIP_CONFIG=/home/paperclip/.paperclip/instances/default/config.json
PAPERCLIP_INSTANCE_ID=default
PAPERCLIP_EXECUTABLE=/home/paperclip/.local/bin/paperclipai
PAPERCLIP_NODE=/usr/bin/node
PAPERCLIP_DATA_DIR=/home/paperclip/.paperclip/instances/default/db
PAPERCLIP_BACKUP_DIR=/home/paperclip/.paperclip/instances/default/data/backups
PAPERCLIP_STORAGE_DIR=/home/paperclip/.paperclip/instances/default/data/storage
PAPERCLIP_SECRETS_KEY_FILE=/home/paperclip/.paperclip/instances/default/secrets/master.key
PAPERCLIP_WORKSPACES_DIR=/home/paperclip/workspaces
PAPERCLIP_SERVICE_MANAGED=1
EOF
chown root:paperclip /etc/paperclip/paperclip.env
chmod 0640 /etc/paperclip/paperclip.env
systemd-analyze verify /etc/systemd/system/paperclip.service
/usr/lib/paperclip/paperclip-preflight
```

Before this preflight can pass, `config.json` must contain absolute paths equal
to the five corresponding `PAPERCLIP_*_DIR` / `PAPERCLIP_SECRETS_KEY_FILE`
values, with `database.mode="embedded-postgres"`, an enabled backup, local-disk
storage, and `secrets.provider="local_encrypted"`. All paths must be inside
`$PAPERCLIP_HOME/instances/$PAPERCLIP_INSTANCE_ID`, exist before activation,
and not be group/other writable. Do not include `DATABASE_URL`, API keys, or
other secret values in shell history or the environment file.

## Reviewed permission tightening (do not execute during staging)

The currently preflight-controlled state directories may be mode `0775`. The
candidate fails closed on group/other-writable state, so a named production
operator must first record the exact modes and owners, then obtain review of
the affected paths. Do **not** run the following mutation while staging this
candidate or without that review and production-host approval:

```sh
stat -c '%a %U:%G %n' \
  /home/paperclip/.paperclip \
  /home/paperclip/.paperclip/instances \
  /home/paperclip/.paperclip/instances/default \
  /home/paperclip/.paperclip/instances/default/db \
  /home/paperclip/.paperclip/instances/default/data/backups \
  /home/paperclip/.paperclip/instances/default/data/storage \
  /home/paperclip/workspaces

# Approved production action only, after the above output is attached to the
# change record and an owner confirms these are the intended Paperclip paths:
chmod go-w /home/paperclip/.paperclip /home/paperclip/.paperclip/instances \
  /home/paperclip/.paperclip/instances/default \
  /home/paperclip/.paperclip/instances/default/db \
  /home/paperclip/.paperclip/instances/default/data/backups \
  /home/paperclip/.paperclip/instances/default/data/storage \
  /home/paperclip/workspaces
```

Re-run `stat` and `/usr/lib/paperclip/paperclip-preflight` afterward. This is
permission tightening only: it must not delete, initialize, migrate, copy, or
otherwise change the embedded PostgreSQL, backups, storage, or secret key.

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

## Handoff and sandbox checks

With an approved maintenance window, preserve the currently running instance
instead of starting a second one: capture its PID and instance state, stage the
unit, then use the approved service handoff. Before treating the handoff as
successful, require a healthy replacement PID and inspect the hot-restart
report. Every heartbeat recorded before handoff must appear in
`adoptedRunIds`, `finalizedWhileDownRunIds`, or an explicit recovery outcome;
an absent run is a failure.

The repository fixture proves the network-only Bubblewrap command includes
`--dev-bind /dev /dev`. Retain that check when updating the adapter sandbox; a network
namespace must not leave the sandbox without usable device nodes.

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

Do not delete `/home/paperclip/.paperclip`, instance configuration, embedded PostgreSQL
data, backups, storage, or secrets as part of rollback.
