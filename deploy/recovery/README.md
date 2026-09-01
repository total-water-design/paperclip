# Bounded Paperclip recovery provisioning

This directory is a deployment artifact, not an installer. Production
installation remains Board-gated.

The only authorized invocation is the root-owned helper at
`/usr/local/lib/paperclip/paperclip-recovery`, through the exact no-argument
sudoers entry in `paperclip-recovery.sudoers`. The helper rejects arguments and
requires the original sudo caller to be the `paperclip` OS identity. It can only
restart `paperclip.service`, wait for loopback health, and invoke the fixed
loopback `POST /api/recovery/reconcile` endpoint.

Provision a high-entropy `PAPERCLIP_RECOVERY_TOKEN` to the Paperclip service
environment and the identical token in `/etc/paperclip/recovery.token`. The
token file must be root-owned, mode `0640`, group `paperclip`; the helper reads
it only after sudo has elevated the exact fixed helper. Do not use a board API
key, agent API key, database credential, or a shared application secret.

The recovery endpoint is loopback-only and fails closed unless that token is
configured. It accepts no request parameters. It reads the authoritative
application run inventory, runs the canonical orphan/retry/stranded-issue/stale
lock reconciliation sequence, then returns non-secret before/after inventory
and reconciliation IDs. It performs no raw database, backup, configuration, or
repository mutation.
