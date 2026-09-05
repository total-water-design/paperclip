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
- The root-owned environment file names the native installed CLI entry point at
  `/home/paperclip/.paperclip/cli/current/node_modules/paperclipai/dist/index.js`
  and launches it with `/usr/bin/node`; `/opt/paperclip` and a global launcher
  are not assumed. The preflight rejects missing or unsafe files.
- Preserve one existing instance and explicitly name its config, embedded
  PostgreSQL data, backup, local storage, and local-encrypted secrets-key
  paths. The preflight rejects missing paths, symlinks, other-writable state,
  a disabled backup, or mismatched config references. Group-writable state is
  accepted for the dedicated `paperclip` group used by the verified layout.
- Do not put secret values in the unit or environment file. The secrets key is
  a file reference only; inline `PAPERCLIP_SECRETS_MASTER_KEY` is rejected.
- The separate recovery principal is provisioned only through
  `paperclip-recovery-token-provision`. It reads one protected stdin line,
  writes root-owned `0640` token/environment files, and never displays the
  value. Until this is complete the unit and preflight fail closed.
- Health recovery runs as `paperclip` and can elevate only the exact
  no-argument `/usr/local/lib/paperclip/paperclip-recovery` helper through the
  shipped sudoers entry. The health script never invokes `systemctl` directly.
- The bounded abnormal-restart policy is five starts in 60 seconds, followed by
  a five-second delay. Deliberate operator stops do not restart the service.
- `ProtectSystem=strict` and `ProtectHome=read-only` remain enabled. Runtime
  writes are limited to `/home/paperclip/.paperclip/instances`; the installed
  CLI and its certification material remain read-only to the service.
- The service installer snapshots the primary unit, the complete drop-in
  directory, CLI `current` pointer and `install.json`, certification staging,
  recovery files, and unit enable/active states before any replacement. It
  installs the reviewed `10-safe-shutdown.conf` and
  `20-git-scan-containment.conf` as the only effective drop-ins. Rollback moves
  the complete candidate set aside and restores the snapshot byte-for-byte.

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

Review `deploy/systemd/paperclip.env` against the recorded instance. It is bound
to the verified `/home/paperclip/.paperclip` native layout and must match the
running instance exactly. Build the certified archive and manifest from the
exact candidate before entering the production gate. The service installer
snapshots the pre-candidate CLI pointer before a separately reviewed CLI install
changes it, and stages immutable certification sidecars outside the release
tree:

```sh
PAPERCLIP_CERTIFIED_ARCHIVE_SOURCE=/approved/stage/paperclipai.tgz \
PAPERCLIP_CERTIFICATION_MANIFEST_SOURCE=/approved/stage/paperclipai.certification.json \
PAPERCLIP_ROLLBACK_ROOT=/root/paperclip-service-rollback \
  deploy/systemd/paperclip-service-install install
# Only now may the separately approved exact-candidate CLI install atomically
# update /home/paperclip/.paperclip/cli/current and cli/install.json.
# A Board-approved operator supplies the high-entropy token on protected stdin.
read -rsp 'Recovery token: ' token; printf '\n' >&2
printf '%s\n' "$token" | /usr/lib/paperclip/paperclip-recovery-token-provision
unset token
systemd-analyze verify /etc/systemd/system/paperclip.service \
  /etc/systemd/system/paperclip-health-recovery.service \
  /etc/systemd/system/paperclip-health-recovery.timer
/usr/lib/paperclip/paperclip-preflight
/usr/lib/paperclip/paperclip-activation-preflight
systemctl cat paperclip.service
```

The effective unit output must contain the primary unit plus exactly
`10-safe-shutdown.conf` and `20-git-scan-containment.conf`; any unexpected
drop-in is a stop condition. Do not edit an installed unit, drop-in, archive,
manifest, identity file, or executable to make preflight pass.

Before this preflight can pass, `config.json` must contain absolute paths equal
to the five corresponding `PAPERCLIP_*_DIR` / `PAPERCLIP_SECRETS_KEY_FILE`
values, with `database.mode="embedded-postgres"`, an enabled backup, local-disk
storage, and `secrets.provider="local_encrypted"`. All paths must be inside
`$PAPERCLIP_HOME/instances/$PAPERCLIP_INSTANCE_ID`, exist before activation,
and not be other writable. Group write is limited to the dedicated service
group. Do not include `DATABASE_URL`, API keys, or
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

Use the fixed, loopback-only authenticated recovery endpoint for authoritative
run inventory and canonical reconciliation. Do not use an operator API key or
the obsolete heartbeat-run routes.

```sh
/usr/lib/paperclip/paperclip-service-transition reconcile
jq . "$PAPERCLIP_TRANSITION_EVIDENCE_DIR/reconciliation.json"
```

Retain the endpoint's non-secret before/after inventory and reconciliation IDs
with the change record. If it fails, stop and open a recovery issue.

## Rollback

If startup, health, or reconciliation fails, restore the backed-up unit and
environment file, reload systemd, and restart only under an approved production
gate. The instance state is intentionally left untouched.

```sh
PAPERCLIP_ROLLBACK_ROOT=/root/paperclip-service-rollback \
  /usr/lib/paperclip/paperclip-service-install rollback
curl -fsS http://127.0.0.1:3100/api/health | jq -e '.status == "ok"'
```

Do not delete `/home/paperclip/.paperclip`, instance configuration, embedded
PostgreSQL data, backups, storage, or secrets as part of rollback.

## Permission gate input (record only)

No permission change is authorized by this runbook. Read-only live inspection
recorded these exact four future-gate inputs, all owned by
`paperclip:paperclip` with mode `0775`:

- `/home/paperclip/.paperclip/instances`
- `/home/paperclip/.paperclip/instances/default`
- `/home/paperclip/.paperclip/instances/default/data/backups`
- `/home/paperclip/.paperclip/instances/default/data/storage`

Any future permission operation must name the exact candidate and remain
limited to those four paths. It must not be inferred from this document or
performed as part of install, activation, or rollback.
