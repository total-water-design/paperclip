# Pre-activation safe-window inventory (predecessor utility)

`paperclip-preactivation-safe-window-inventory` is a source-only transition
utility for the active predecessor, where the candidate-only
`GET /api/recovery/safe-window-inventory` route does not yet exist.

It removes the deadlock by taking the required inventory **before the candidate
is activated**.  A separately authorized transition staging may place this
single file beside the active `2026.831.1` runtime, without replacing the
Paperclip package, restarting a service, or invoking the candidate.  The
utility connects only through the predecessor's local PostgreSQL peer socket
and emits a conservative fixed-company snapshot.  Candidate activation remains
outside this source artifact and requires its own canonical gate.

## Fixed scope and authentication

The utility accepts no arguments and only runs as the `paperclip` OS identity.
It reads exactly one non-secret root-owned `0640` file:
`/etc/paperclip/preactivation-safe-window-company`.  That file contains the
fixed UUID-like company ID (letters, digits, and hyphens only).  It refuses a
missing, symlinked, incorrectly owned/mode, or malformed binding.

It uses PostgreSQL peer authentication on the fixed `/var/run/postgresql`
socket as database user `paperclip`.  It does not accept, read, write, or
forward a database URL, password, API key, recovery token, safe-window token,
or arbitrary company selector.  A deployment whose predecessor database does
not offer this peer socket is deliberately unsupported and must not substitute
a credential-bearing invocation.

## Classification and limitation

The one `READ ONLY` transaction reads only `heartbeat_runs` for the fixed
company and statuses `queued`, `running`, or `scheduled_retry`.  Each returned
run is classified `drain_required`, including local-child candidates.  This is
deliberately more conservative than the candidate's hot-adoption classifier:
an empty run list can support proceeding to the next controlled gate; any
listed run requires a drain/stop decision outside this utility.

The helper does not query issues, inspect processes, wake/resume/reconcile
runs, access secrets, call HTTP, write a file, or invoke `systemctl`.  Apart
from fixed POSIX identity/metadata reads, its only data operation is the fixed
`psql` read-only transaction. It is a snapshot, not activation
authorization or process-liveness proof.  IV&R must independently review the
source, take required snapshots, and apply the approved promotion procedure.
