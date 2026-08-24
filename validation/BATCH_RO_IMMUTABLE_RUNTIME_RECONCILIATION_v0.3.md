# Batch RO — Immutable Runtime Selective Reconciliation v0.3

Owner branch: `feature/total-ro-design-batch-ro`

Blocked production release: Alpha `14aa40a3651955718c5e1318a651ea49c1ac3b0a`

## Reconciliation objective

Fix only the Batch RO production lifecycle defect that writes into `/opt/totalrodesign/app` during WSGI startup. Do not weaken systemd security, repeat/revert the successful EC2 venv recovery, or use this blocker correction to silently change the Alpha Batch RO calculation payload.

## Exact blocker-only files to reconcile into Alpha

Take from the owner branch:

1. `batch_ro_runtime.py`
   - manifest-only read/verify/import/register runtime;
   - no Base64/tar handling and no source writes.
2. `tools/materialize_batch_ro_build.py`
   - explicit pre-startup legacy release-preparation tool.
3. `tests/test_batch_ro_immutable_runtime.py`
   - manifest/missing/tamper/idempotence/no-write validation.
4. `validation/BATCH_RO_IMMUTABLE_RUNTIME_AUDIT_v0.3.md`
5. `validation/BATCH_RO_IMMUTABLE_RUNTIME_RECONCILIATION_v0.3.md`

For reconciliation/CI evidence, also retain or adapt:

- `.github/workflows/batch-ro-validation.yml`
- `.github/workflows/batch-ro-ec2-immutable-validation.yml`

Do **not** take the owner branch's directly tracked v0.2 `addons/batch_ro/*`, Batch UI, or owner runtime manifest into a blocker-only Alpha correction; those would constitute a Batch engine/runtime-content upgrade rather than just fixing startup lifecycle.

## Preserve the exact Alpha Batch calculation payload

Do **not** replace these four files from Alpha `14aa40a...`:

- `deploy/batch_ro_alpha/payload.segment01`
- `deploy/batch_ro_alpha/payload.segment02`
- `deploy/batch_ro_alpha/payload.part02`
- `deploy/batch_ro_alpha/payload.part03`

Their decoded payload SHA-256 is:

`04fd024a5a8894fc623c065477fa7ebca31e7a4d9454fa03ace03b850d9e0afa`

Create on the reconciled Alpha:

`deploy/batch_ro_alpha/payload.sha256`

with exactly:

`04fd024a5a8894fc623c065477fa7ebca31e7a4d9454fa03ace03b850d9e0afa`

The owner branch's historical later compact bundle is `8ed7dcfd...`; it is provenance only and must not be substituted for the Alpha payload in this blocker fix.

## Required Deployment & Release change

Apply this only to the **latest** `.github/workflows/deploy-alpha.yml`; do not replace that workflow wholesale from the Batch specialist branch.

During **Validate release source**, after basic source-presence checks but **before** `python3 -m compileall -q .` and before staging `rsync`, run:

```bash
EXPECTED_BATCH_SHA="$(tr -d '\r\n ' < deploy/batch_ro_alpha/payload.sha256)"
python3 tools/materialize_batch_ro_build.py \
  --from-legacy-payload \
  --expect-payload-sha "$EXPECTED_BATCH_SHA"
python3 tools/materialize_batch_ro_build.py --check
```

Then require at minimum:

```bash
for f in \
  addons/batch_ro/__init__.py \
  addons/batch_ro/engine.py \
  static/addons/batch_ro/batch_ro.svg \
  static/addons/batch_ro/batch_ro_addon.js \
  deploy/batch_ro_runtime_manifest.json; do
  test -f "$f"
done
```

The legacy payload also contains its Batch engineering-basis/test support files; the materializer may stage those as well, but normal WSGI runtime requires only the four runtime files plus the manifest.

The staging `rsync` then carries a complete immutable Batch artifact into `/opt/totalrodesign/app` **before** Gunicorn starts.

## Rollback preparation — mandatory for future corrected releases

The protected rollback path builds a temporary tree with:

`git archive "$PREVIOUS_SHA" | tar -x -C "$TMP"`

A corrected release stores the legacy payload in Git but its direct runtime files/manifest are generated during release preparation. Therefore, when the archived previous release contains both the tool and payload marker, materialize it in the rollback temp tree **before** staging rsync:

```bash
if [ -f "$TMP/tools/materialize_batch_ro_build.py" ] \
   && [ -f "$TMP/deploy/batch_ro_alpha/payload.sha256" ]; then
  (
    cd "$TMP"
    EXPECTED_BATCH_SHA="$(tr -d '\r\n ' < deploy/batch_ro_alpha/payload.sha256)"
    python3 tools/materialize_batch_ro_build.py \
      --from-legacy-payload \
      --expect-payload-sha "$EXPECTED_BATCH_SHA"
    python3 tools/materialize_batch_ro_build.py --check
  )
fi
```

This preserves rollback safety without granting runtime source-write permission.

## Keep from current Alpha / Total RO integration

Prefer current Alpha/reconciliation versions of:

- `wsgi.py` — it already calls `register_batch_ro_runtime(app, CALCS)`; do not duplicate registration;
- conventional RO calculations and tests;
- CCRO tracked source/runtime;
- Total RO navigation/UI shell and Suite contracts;
- entitlements;
- auth/database/platform changes;
- `.github/workflows/deploy-alpha.yml` except for the narrow pre-startup materialization/check additions;
- the successful dependency/EC2 venv recovery;
- production systemd security.

## Principal conflict

`batch_ro_runtime.py` is an intentional full replacement of the failed Alpha implementation. Alpha currently contains both:

- `materialize_batch_ro_files()` / `tarfile.extractall(ROOT)`; and
- `_patch_batch_ro_ui_host_probe()` / `write_text()`.

Both runtime mutations must disappear. The compatibility probe is applied, if needed, only by the release-preparation tool before staging.

## Acceptance gate after selective reconciliation

Require all of the following before deployment:

- exact Alpha Batch payload remains `04fd024a5a8894fc623c065477fa7ebca31e7a4d9454fa03ace03b850d9e0afa`;
- Python compile passes;
- exact Alpha Batch numerical tests pass;
- conventional RO regression passes;
- CCRO regression passes;
- Batch UI JavaScript syntax passes;
- generated runtime manifest verifies all four runtime files;
- WSGI imports with application source read-only;
- `/healthz` returns HTTP 200;
- `batch_ro` is registered in `CALCS`;
- `/ro` includes `/static/addons/batch_ro/batch_ro_addon.js`;
- Batch calculation API is registered/non-404;
- two repeated startups are idempotent;
- source-tree SHA fingerprint is identical before/after startup;
- missing/tampered runtime files fail closed clearly;
- no `tarfile.extractall(ROOT)` or equivalent normal-startup mutation remains;
- no `ProtectSystem`, `ReadWritePaths`, ownership or source-permission weakening;
- no production venv refresh/rebuild/revert is performed by this fix.

Do not merge the specialist branch wholesale. Reconcile only the immutable-runtime lifecycle correction above.
