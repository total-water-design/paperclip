# TOT-3271 successor live-controls preflight v1

Disposition: **PRECHECK AUTHORING ONLY — NO EXECUTION AUTHORITY.** This distinct
successor packet replaces neither the terminal adverse record for TOT-3258 nor
its rejected approval. It expressly does not reuse immutable v2 lane authority.

## Frozen identity

| Role | Identity |
|---|---|
| Actual live predecessor / rollback | `72b50614011b457093cd5e3be189a4ca7a9aab75` |
| Target candidate | `904683f94e4788beca63244269b9dcd59dcff71d` |
| Candidate tree / parent tree | `3a5cfa99e28ba3f59d7d6761c9e49fd97ab8d724` |
| Candidate parent | `72b50614011b457093cd5e3be189a4ca7a9aab75` |
| Packet identity | `TOT-3271/successor-live-controls-preflight-v1` |
| Future packet location | `/var/lib/paperclip/activation-packets/TOT-3271/successor-live-controls-preflight-v1` |
| Activation / rollback entrypoint | **ABSENT BY DESIGN** |

`72b50614…` is the observed current pointer, manifest, authority, service argv,
and PostgreSQL-binary basis in the source record dated `2026-09-10T16:44:45Z`.
The v2 lane instead demanded rollback `98d8…`, absent `50-memory-limit.conf`,
and present `98-db-recovery-no-heartbeats.conf`; that disagreement is why its
activation was terminally adverse. This procedure accepts neither those expected
controls nor its approval.

## Future human-only read-only preflight

The separately authorized human must replace `NAMED_HUMAN_EXECUTOR_REQUIRED`
with their real name in the terminal record before starting. The allowed scope
is one read-only preflight session; it does not authorize staging, activation,
restart, reload, pointer change, service/PostgreSQL control, collection,
certification, or a second attempt.

Capture UTC start/end timestamps and execute these read-only commands verbatim,
recording each exact argv, exit status, stdout, and stderr separately:

```sh
id
date -u +%Y-%m-%dT%H:%M:%SZ
git -C /home/paperclip/workspaces/total-water-design-suite/.worktrees/tot-1595 show -s --format='commit=%H%ntree=%T%nparents=%P%ncommitter=%cI%nsubject=%s' 72b50614011b457093cd5e3be189a4ca7a9aab75 904683f94e4788beca63244269b9dcd59dcff71d
git -C /home/paperclip/workspaces/total-water-design-suite/.worktrees/tot-1595 diff --name-only 72b50614011b457093cd5e3be189a4ca7a9aab75..904683f94e4788beca63244269b9dcd59dcff71d
readlink -f /home/paperclip/.paperclip/cli/current
sha256sum /home/paperclip/.paperclip/cli/install.json /etc/paperclip/activation/default.authority.env /usr/local/bin/paperclipai-service-guard /home/paperclip/.local/bin/paperclipai
systemctl show paperclip.service --property=ActiveState,SubState,UnitFileState,MainPID,NRestarts,ExecStart,ExecStop,Restart,Environment
systemctl cat paperclip.service
find /etc/systemd/system/paperclip.service.d -maxdepth 1 -type f -printf '%f|%s|%m\n' | sort
sha256sum /etc/systemd/system/paperclip.service /etc/systemd/system/paperclip.service.d/*.conf
ps -p "$(systemctl show paperclip.service --property=MainPID --value)" -o pid=,args=
ss -ltnp
pgrep -a postgres
pg_controldata /home/paperclip/.paperclip/instances/default/db | grep '^Database cluster state:'
test ! -e /home/paperclip/.paperclip/cli/installs/git/904683f94e47
test -d /home/paperclip/.paperclip/cli/installs/git/72b50614011b
```

## Fail-closed stop conditions

Stop with `PREFLIGHT_ADVERSE` and perform no further command if any command is
missing, unreadable, nonzero, incomplete, or differs from the manifest. This
includes: a different human identity; candidate/tree/parent mismatch; current
pointer/install/authority/argv not all `72b50614…`; a candidate already present;
missing predecessor payload; guard or shim hash mismatch; an effective drop-in
set other than `10,20,30,40,45,50,97,99` with `98` absent; effective `Restart`
not `no`; nonempty `ExecStop`; PostgreSQL not on the expected production basis;
or unavailable listener/health evidence. No retry, substitution, mutation, or
reused approval follows an adverse result.

## Provenance contract

The human record must retain immutable raw files for each command: `argv`, UTC
start/end, terminal identity/TTY/host, numeric exit, complete stdout bytes,
complete stderr bytes, and session exit. It must also include the packet
manifest/procedure SHA-256 and byte counts, candidate/tree/parent output,
pointer/manifest/authority bytes, service/drop-in listing and hashes, process
argv/listeners, PostgreSQL evidence, and an explicit final token
`PREFLIGHT_PASS` or `PREFLIGHT_ADVERSE`. Missing data is adverse. A pass is
preflight evidence only; Independent Validation & Release and a fresh Board
gate remain separate prerequisites for any future action.

## Authoring limitations

The API bridge was unreachable and DNS prevented a live-origin query in this
run. No host command in this document was run by the author. The effective
control facts originate only from the preserved 2026-09-10 no-mutation record
and must be freshly recaptured by the named human.
