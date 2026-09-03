# TOT-1596 artifact identity evidence

## Scope and initial classification

Mandated worktree: `.worktrees/tot-1595`; initial branch SHA:
`15328114785e8e3b6c78f13af232dddc3936e036`. Reported mismatch source:
`2e5d2e988a47e608c3a6e470d88fd7107e6c3e5f`.

```text
$ git show -s --format='%H %ct %s' 2e5d2e988a47e608c3a6e470d88fd7107e6c3e5f
2e5d2e988a47e608c3a6e470d88fd7107e6c3e5f 1788289881 fix(secrets): close scoped capability validation gaps

$ git show 2e5d2e988:server/scripts/write-build-stamp.mjs | rg 'short|no stamp'
git rev-parse --short HEAD
The build must not fail when no commit is available.
```

Classification: source identity existed, but the generated server stamp
reduced it to an abbreviated SHA and failed open when Git or a label was
unavailable. The CLI bundle and npm archive had no cryptographic source
identity. The packaging path did not certify the archive digest or bind
installed bytes to source. Runtime health exposed a version/build stamp, but
activation did not compare installed bytes with a running process. These gaps
allow a correct checkout, stale generated bundle/archive/install, and older
running process to be presented together.

Limitations: the originally reported tarball, installed tree, and live process
were not supplied to this isolated worktree, and this task forbids Alpha or
production access/restart. Their historical byte hashes cannot be recovered.
The source behavior is reproduced at the reported commit; generated, archive,
installed, and runtime mismatch cases use local fixtures.

## Candidate controls

`scripts/build-certified-npm.sh` rejects dirty/mislabeled source, records the
full SHA, clean state, exact Node/pnpm versions, lock digest, canonical command,
and generated file digests, then creates a fixed-mtime sorted zero-owner gzip
archive. Its sidecar certification binds the archive and installed CLI entry.
`scripts/paperclip-activation-preflight.sh` verifies those identities and
rejects a live PID with absent or stale runtime identity. The systemd unit
invokes the gate before start. No host activation is performed.

## Verification record

The functional candidate at `93ba1976a` was clean before both package runs.
The second run used the same command, toolchain, checkout, and lockfile.

```text
$ corepack pnpm test:artifact-identity
✔ identity is byte reproducible and rejects a false source label
✔ identity rejects an untracked source file
✔ activation rejects stale runtime and changed installed executable
tests 3; pass 3; fail 0

$ corepack pnpm --filter paperclipai test -- root-systemd-preflight
$ corepack pnpm --filter @paperclipai/server test -- heartbeat-workspace-session
exit 0

$ PAPERCLIP_ARTIFACT_DIR="$PAPERCLIP_RUN_SCRATCH_DIR/build-a" corepack pnpm build:npm:certified --skip-typecheck
certified archive: .../build-a/paperclipai-0.3.1.tgz
$ PAPERCLIP_ARTIFACT_DIR="$PAPERCLIP_RUN_SCRATCH_DIR/build-b" corepack pnpm build:npm:certified --skip-typecheck
certified archive: .../build-b/paperclipai-0.3.1.tgz
$ sha256sum build-{a,b}/paperclipai-0.3.1.tgz
1c7dc396a6e726c3badedb129f1313d410f718e7b48a455f2d1e0ce4d04f0df9  build-a/paperclipai-0.3.1.tgz
1c7dc396a6e726c3badedb129f1313d410f718e7b48a455f2d1e0ce4d04f0df9  build-b/paperclipai-0.3.1.tgz
$ cmp build-a/paperclipai-0.3.1.tgz build-b/paperclipai-0.3.1.tgz
exit 0
$ tar -tzf build-a/paperclipai-0.3.1.tgz | rg 'paperclip-artifact-identity.json|dist/index.js$'
package/dist/index.js
package/dist/paperclip-artifact-identity.json
```

The first full build also completed the 34-project recursive TypeScript/Rust
typecheck, bundle, and syntax checks before its wrapper correctly failed closed
on a tracked README lifecycle defect. The wrapper was fixed to restore tracked
package inputs before certification; the two successful package runs above
then used `--skip-typecheck` rather than repeating that unchanged full check.

Expected negative errors asserted by the focused suite are `source label
mismatch`, `source tree is dirty`, `stale runtime identity`, and `installed
executable digest differs from certification manifest`.

Changed-file scope is limited to the artifact identity/build/preflight scripts,
their focused tests, the systemd gate and runbook, package command registration,
the preserved strict Git-origin normalization/test from
`task/tot-1589-git-origin-normalization`, and this evidence document. Final
candidate SHA and local/remote equality are recorded on the issue after the
evidence-only commit and push.
