# TOT-3929 runtime-successor reconciliation record

## Inputs

- Verified merge base: `bcfd9b777c14af70dd197f57d85e7aadf165ae68`
- Codex stdio/protected-gate tip: `53e6da6f7987852075ee7c26f2b2a0342f56e99c`
- COS heartbeat/calendar-version tip: `be7e01e4af676d4e14c0e7eae4f4d8d7548b1d4b`
- COS bounded-heartbeat repair included by the successor: `685bc52e20e9c1342706d14912f0501bb94df4a3`

## Reconciliation method

The candidate starts at the COS calendar-version successor and merges the Codex
tip with a non-fast-forward merge. Git's three-way merge completed without
conflict. The only paths changed on both lines were:

- `packages/adapter-utils/src/local-process-sandbox.ts`
- `packages/adapter-utils/src/local-process-sandbox.test.ts`
- `packages/adapters/codex-local/src/server/execute.acp-fallback.test.ts`

No manual resolution was required. The COS side already carries the closed
consumer/drain behavior represented by the Codex line, together with its
additional sandbox compatibility and EPIPE containment work. The resulting
tree retains the Codex closed-consumer tests and implementation while retaining
the COS bounded heartbeat route, reporting-subtree authorization, activation
identity verifier, and calendar-versioned package metadata.

## Scope boundary

This record covers source reconciliation only. It does not authorize or record
runtime activation, restart, pointer mutation, runtime smoke execution,
privilege/egress expansion, protected-history merge, or independent
certification.
