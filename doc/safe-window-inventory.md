# Safe-window inventory contract (v1)

`GET /api/recovery/safe-window-inventory` is the sole source-contract endpoint
for IV&R safe-window snapshots. It is not a recovery operation.

## Authorization and denial

The caller must connect directly from loopback and present
`X-Paperclip-Safe-Window-Inventory-Token`. The token is supplied at process
start through `PAPERCLIP_SAFE_WINDOW_INVENTORY_TOKEN`; it is distinct from
`PAPERCLIP_RECOVERY_TOKEN`. `PAPERCLIP_SAFE_WINDOW_INVENTORY_COMPANY_ID`
binds that principal to one company. The request has no body and no accepted
company selector; query values are ignored, so a holder cannot read another
company through this interface.

- `503`: the dedicated token or its company binding is absent.
- `403`: the peer is not loopback.
- `401`: the dedicated token is absent or mismatched.

## Response schema

The response has `contractVersion: "safe_window_inventory.v1"`, the fixed
caller identity `{ principal: "safe_window_inventory", companyId }`, and an
`inventory` value with one company record, all nonterminal run records, and
all nonterminal issue records in that company. Run fields are stable IDs,
status, agent/issue association, adapter/runtime metadata, process-metadata
presence flags, timestamps, and `safeWindowDisposition`.

`safeWindowDisposition` is `hot_adoptable` only for a running detached local
child-process adapter with recorded process metadata. It is `drain_required`
for queued or scheduled-retry runs, server-stdio/ACP runs, non-local-child
adapters, and runs without process metadata. `dispositionReason` states which
rule applied.

## Read-only boundary and limitations

The route invokes exactly `heartbeat.getSafeWindowInventory(companyId)`. That
method has only bounded database SELECTs from company, run, agent, and issue
state. It does not read a recovery token, call reconcile/reap/promote/resume,
wake or enqueue an agent, write issue/run state, read a secret file, inspect or
control processes/services, or expand privileges. The route performs no
filesystem, subprocess, service-control, or secret-service work.

This is a snapshot, not an activation authorization or process-liveness proof.
IV&R must take before/after snapshots and independently apply its controlled
safe-window procedure. A `hot_adoptable` classification is eligibility based
on persisted metadata only; it does not adopt, resume, or otherwise touch a
run.
