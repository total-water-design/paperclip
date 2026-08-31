# Root systemd Paperclip runbook

This runbook stages the root-managed unit at `deploy/systemd/paperclip.service`.
It is an operator procedure: do not run the install, enable, restart, or
destructive-recovery commands against a healthy instance until the production
host gate is approved.

## Invariants

- Keep `server.deploymentMode` as `local_trusted` and `server.exposure` as
  `private`.
- Keep the configured server host as `127.0.0.1` and port as `3100`.
- Preserve the existing `PAPERCLIP_HOME`, `PAPERCLIP_CONFIG`, embedded
  PostgreSQL data directory, backup directory, storage, and secrets key. Do
  not initialize a new instance or replace any of those paths.
- Do not put secrets in the unit. `/etc/paperclip/paperclip.env` must be root
  owned and mode `0600`.
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

Confirm that the recorded `PAPERCLIP_HOME` contains the live instance's
`instances/default/` directory and that the existing configuration resolves to
the same embedded PostgreSQL data, backup, storage, and secrets paths. If the
current process is not already using `/var/lib/paperclip`, do not silently
change it: migrate only through a separately approved, backup-verified change.

Create the unit and environment file using the recorded existing paths (the
values below are examples and must match the running instance exactly):

```sh
install -d -o root -g root -m 0755 /etc/paperclip
install -o root -g root -m 0644 deploy/systemd/paperclip.service /etc/systemd/system/paperclip.service
install -o root -g root -m 0600 /dev/null /etc/paperclip/paperclip.env
cat >/etc/paperclip/paperclip.env <<'EOF'
PAPERCLIP_HOME=/var/lib/paperclip
PAPERCLIP_CONFIG=/var/lib/paperclip/instances/default/config.json
PAPERCLIP_INSTANCE_ID=default
PAPERCLIP_SERVICE_MANAGED=1
EOF
systemd-analyze verify /etc/systemd/system/paperclip.service
```

If the selected state root is not `/var/lib/paperclip`, update both the
environment file and the unit's `ReadWritePaths=` to the same approved absolute
path before verification. Do not include `DATABASE_URL`, API keys, or other
secrets in shell history; use the existing root-only environment/configuration
source instead.

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
systemctl daemon-reload
systemctl restart paperclip.service
curl -fsS http://127.0.0.1:3100/api/health | jq -e '.status == "ok"'
```

Do not delete `/var/lib/paperclip`, instance configuration, embedded PostgreSQL
data, backups, storage, or secrets as part of rollback.
