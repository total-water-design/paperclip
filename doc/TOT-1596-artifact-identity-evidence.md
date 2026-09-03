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

Final raw checks, reproducibility hashes, changed-file scope, candidate SHA,
and local/remote equality are appended after verification.
