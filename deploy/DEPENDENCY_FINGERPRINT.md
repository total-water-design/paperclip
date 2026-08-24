# TWDS dependency-closure deployment hardening

## Purpose

The protected Alpha deployer must never decide that the server Python environment is current by comparing only `requirements-server.txt` bytes.

Current Alpha uses:

```text
requirements-server.txt
  -> -r requirements.txt
```

Any future local `-r` / `--requirement` include is part of the same effective server dependency closure.

The RO-first incident proved the failure mode: `requirements.txt` changed while `requirements-server.txt` did not, so new application code restarted against a stale venv. This hardening closes that class of failure.

## Recursive fingerprint

`deploy/requirements_fingerprint.py` recursively follows local `-r`, compact `-rfile`, `--requirement file`, and `--requirement=file` references. It deterministically hashes:

- every manifest path in the recursive include graph;
- SHA-256 of the exact bytes of every manifest;
- include edges between manifests.

It fails closed for missing manifests, include cycles, repository escapes, remote includes, invalid UTF-8, and malformed/unterminated include directives.

Canonical command:

```bash
python deploy/requirements_fingerprint.py requirements-server.txt --repo-root .
```

## Critical MFA QR acceptance case

The next Suite Core release may add:

```text
segno>=1.6,<2
```

to `requirements.txt` while leaving `requirements-server.txt` byte-identical.

The regression suite explicitly proves:

```text
old closure without segno != new closure with segno
```

and separately proves that changes in deeper local requirement includes also invalidate the fingerprint.

## Root-owned deployment flow

The GitHub runner retains one privileged entrypoint only:

```text
NOPASSWD: /usr/local/sbin/twds-alpha-deploy
```

No arbitrary root shell, `pip`, `systemctl`, sudoers editing, or writable application source is granted to the runner.

The hardened root-owned deployer performs:

```text
staged exact release
  -> recursive candidate dependency fingerprint
  -> compare with fingerprint persisted inside validated live venv

same
  -> reuse validated live venv
  -> protected application backup/cutover/restart/health

different
  -> build isolated candidate venv
  -> install exact requirements-server.txt closure
  -> pip check
  -> template/runtime/auth import validation
  -> compile candidate source
  -> persist candidate fingerprint in candidate venv
  -> only then back up and cut over app + venv
  -> restart and health check
  -> rollback app and previous venv on failure
```

The fingerprint persistence location is:

```text
/opt/totalrodesign/venv/.twds_requirements_fingerprint
```

Because `/opt/totalrodesign/venv` is the stable symlink to the validated environment, the marker travels with the actual validated venv target.

## One-time installation / seed

`deploy/install_dependency_closure_hardening.sh` is a root-administrator installation step. It:

1. validates the already-authorized live venv with `pip check` and existing template/auth runtime smoke scripts;
2. does **not** install packages, rebuild the venv, or restart the application;
3. backs up the existing root deployer;
4. installs the trusted fingerprint helper root-owned under `/usr/local/lib/twds-alpha/`;
5. installs the hardened deployer at the existing sudo-authorized path `/usr/local/sbin/twds-alpha-deploy`;
6. computes the recursive fingerprint of the current live application dependency closure and persists that fingerprint with the already-validated live venv.

The installer deliberately does not modify sudoers.

## Security / rollback invariants

This hardening must not:

- change application calculations or engineering models;
- alter Suite Core behavior or entitlements;
- change WaterStream or Shared Chemistry behavior;
- grant the GitHub runner arbitrary sudo;
- remove `ProtectSystem=strict`;
- broaden the application source tree into `ReadWritePaths`;
- reset or replace the production database;
- replace production secrets;
- weaken automatic rollback.

The current production venv remains untouched during CI/infrastructure validation. Root installation is a separate authorized infrastructure action; until it is installed and seeded, the existing host deployer is not yet dependency-closure hardened.
