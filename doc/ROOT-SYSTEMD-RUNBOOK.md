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
  `/home/paperclip/workspaces`, and the checked executable shell shim
  `/home/paperclip/.local/bin/paperclipai`, which is invoked directly so its
  shebang can dispatch to its managed Node CLI. The preflight rejects any
  different home, workspace, shim, or `/usr/bin/node` host path.
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

The checked-in `deploy/systemd/paperclip.env` is the production-layout fixture
for the named `default` instance. Compare it with the recorded process before
installing. If any value differs, stop: this procedure is not a migration.
Create an evidence directory on the approved change record, capture the current
service/run state, then use the reversible installer:

```sh
export PAPERCLIP_INSTANCE_ID=default
export PAPERCLIP_TRANSITION_EVIDENCE_DIR=/root/change-record/paperclip-systemd-$(date -u +%Y%m%dT%H%M%SZ)
export PAPERCLIP_ROLLBACK_ROOT="$PAPERCLIP_TRANSITION_EVIDENCE_DIR/rollback"
install -d -m 0700 "$PAPERCLIP_TRANSITION_EVIDENCE_DIR"
deploy/systemd/paperclip-service-transition capture
deploy/systemd/paperclip-service-install install
chown root:paperclip /etc/paperclip/paperclip.env
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

The installer records whether each managed file was present or absent and the
unit's prior enabled/active state before changing files. It does not touch the
named instance. Only after explicit approval, perform the handoff below.

```sh
/usr/lib/paperclip/paperclip-preflight
systemctl enable paperclip.service
export PAPERCLIP_MANUAL_PID='<captured manual PID>'
/usr/lib/paperclip/paperclip-service-transition handoff
/usr/lib/paperclip/paperclip-service-transition reconcile
systemctl is-active --quiet paperclip.service
curl -fsS http://127.0.0.1:3100/api/health | jq -e '.status == "ok"'
systemctl show paperclip.service -p MainPID -p ActiveState -p NRestarts --no-pager
```

The handoff refuses an uninspectable PID or a process whose environment does
not name the selected instance. It sends SIGTERM, waits up to 300 seconds for
the old PID to exit, and only then starts systemd. It records the old command,
instance environment, before/after run inventories, service state, and journal.
The reconciliation command fails unless every pre-handoff run has a current
state and every terminal run has an explicit recovery disposition. Never use
`paperclipai run --force` for the service.

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
# The literal approval value is deliberate and must only be exported inside
# the authorized destructive-test window.
export PAPERCLIP_ALLOW_SIGKILL_TEST=APPROVED
/usr/lib/paperclip/paperclip-service-transition sigkill-test
unset PAPERCLIP_ALLOW_SIGKILL_TEST
```

Without that exact authorization variable the command fails before sending a
signal. Repository tests establish the gate and accounting mechanics only;
they do not claim that a production SIGKILL or live reconciliation occurred.

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

If startup, health, or reconciliation fails, use the same exported rollback
root. Files previously present are restored byte-for-byte; files previously
absent are moved into the change record's `replaced/` quarantine (not deleted),
and prior enabled/disabled plus active/inactive state is restored. The instance
state is intentionally left untouched.

```sh
deploy/systemd/paperclip-service-install rollback
grep -qx active "$PAPERCLIP_ROLLBACK_ROOT/prior.active" && \
  curl -fsS http://127.0.0.1:3100/api/health | jq -e '.status == "ok"' || true
```

Do not delete `/home/paperclip/.paperclip`, instance configuration, embedded PostgreSQL
data, backups, storage, or secrets as part of rollback.
