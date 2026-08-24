# Batch RO — Immutable Production Runtime Audit v0.3

Repository: `total-water-design/total-water-design-suite`

Owner branch: `feature/total-ro-design-batch-ro`

Production failure reference: Alpha `14aa40a3651955718c5e1318a651ea49c1ac3b0a`

Validated executable owner SHA: `89835e197fe47bc7f76fe62fff72f939f0fb9daf`

## Disposition

**PRODUCTION-RUNTIME BLOCKER CORRECTED, VALIDATED AND RECONCILIATION-READY.**

The correction changes packaging/startup lifecycle only. It does not change Batch RO equations, membrane transport, chemistry, energy integration, conventional RO, CCRO, entitlements, or Suite contracts.

## Exact root cause

The failed Alpha called:

`wsgi.py -> register_batch_ro_runtime(app, CALCS) -> materialize_batch_ro_files()`

and then executed `tarfile.extractall(ROOT)` beneath the checked-out application tree. The reconciled Alpha also rewrote `static/addons/batch_ro/batch_ro_addon.js` in place to patch its host-hook probe.

That incorrectly mixed **release-artifact preparation** with **normal application startup**. Under production `ProtectSystem=strict`, `/opt/totalrodesign/app` is intentionally immutable, so the WSGI worker correctly failed with `EROFS`.

Weakening systemd, changing ownership, or adding the application source tree to `ReadWritePaths` is explicitly unnecessary and prohibited.

## Corrected owner architecture

### Directly tracked runtime authority

Normal owner releases now track the four Batch RO runtime files directly:

- `addons/batch_ro/__init__.py`
- `addons/batch_ro/engine.py`
- `static/addons/batch_ro/batch_ro.svg`
- `static/addons/batch_ro/batch_ro_addon.js`

Their checked-in SHA-256 authority is:

`deploy/batch_ro_runtime_manifest.json`

Current identities:

- `addons/batch_ro/__init__.py` — `743544f2f318e2e86084cdd27206350923a94fdec0b3b8874884849108cad925`
- `addons/batch_ro/engine.py` — `99905e323cf92b7f6e8c20b31be99c1b6291eacdabcf13aeffb38932aeb12bfe`
- `static/addons/batch_ro/batch_ro.svg` — `d791fd6cb1ae8091449aafd563dccaf4a1c74d82ea5f3f212dbb51ef92e839f9`
- `static/addons/batch_ro/batch_ro_addon.js` — `a6ab7ac17b9b85f6ec72868aab69f55baa137f276b4e3296195d59776cb033af`

These values are intentionally identical to `deploy/batch_ro_runtime_manifest.json`; the manifest, not prose, is the runtime identity authority.

The UI is the last syntax-valid Alpha Batch UI, with only the existing lexical host-probe compatibility change moved from runtime rewriting into tracked source. Inputs, results, navigation behavior, entitlement flag and calculation API behavior were otherwise preserved for this production blocker.

### Read-only WSGI startup

`batch_ro_runtime.py` now uses only JSON/path/hash verification plus import/registration. It:

1. reads `deploy/batch_ro_runtime_manifest.json`;
2. validates schema/member set/SHA-256 syntax;
3. verifies all four already-present runtime files by SHA-256;
4. fails closed with `BatchRODeploymentError` if anything is missing, tampered, symlinked, unsafe or mismatched;
5. imports `addons.batch_ro.register_batch_ro` only after verification;
6. registers the existing calculation mode and `/ro` UI loader.

It contains no Base64/tar payload unpacking and no source write primitive.

## Legacy compact payload finding

The previously documented owner compact payload identity `ebe22f...` was incorrect. The bytes actually persisted on the owner branch decode to:

`8ed7dcfd5080cc382dad915ceb307f1dae628c368c6a91e7626f9f46a6cb030d`

Audit recovered a valid v0.2 Python engine from those bytes, but the bundled JavaScript member is syntactically corrupt. Therefore that compact bundle is retained only as provenance; it is **not** the executable/runtime authority.

The recovered v0.2 engine SHA-256 is the direct tracked engine identity above: `99905e323c...`.

## Exact failed-Alpha separation

Alpha `14aa40a...` contains the earlier compact Batch payload:

`04fd024a5a8894fc623c065477fa7ebca31e7a4d9454fa03ace03b850d9e0afa`

For a **blocker-only Alpha correction**, that payload must remain unchanged so the Batch calculation engine/equations in the failed release do not silently change.

`tools/materialize_batch_ro_build.py` contains an explicit **build/deployment-preparation only** mode:

`--from-legacy-payload`

It can decode the exact Alpha payload, apply the same host-probe compatibility transformation before startup, write the runtime files into the release workspace, create an Alpha-specific SHA-256 runtime manifest, and immediately verify it. Normal WSGI never imports or calls this path.

For the exact Alpha payload, build preparation produced and re-verified this runtime identity:

- `addons/batch_ro/__init__.py` — `743544f2f318e2e86084cdd27206350923a94fdec0b3b8874884849108cad925`
- `addons/batch_ro/engine.py` — `ee32e01ae8229d0411bb893ad93d40276148fee37c399658c32772b50830294d`
- `static/addons/batch_ro/batch_ro.svg` — `d791fd6cb1ae8091449aafd563dccaf4a1c74d82ea5f3f212dbb51ef92e839f9`
- `static/addons/batch_ro/batch_ro_addon.js` — `d3bd3a4b2c9241c8ebf6b36376cc50be3acf8422060909bc17150f3c507d7875`
- generated Alpha runtime manifest SHA-256 — `eba1fec46276c84454a6acc48c820aa23fd8ead43d1d9a06c6342541555c8259`

The engine hash above is the exact `04fd...` failed-Alpha calculation engine after pre-startup materialization; it is intentionally not replaced by the owner v0.2 engine in the blocker-only correction.

## Equations / models changed

**NONE.**

The immutable-runtime blocker fix does not modify Batch RO governing equations or numerical models. Owner engine identity is frozen separately; blocker-only Alpha validation retains the exact old `04fd...` payload.

## Owner regression contract

`tests/test_batch_ro_addon.py` contains eight specialist regressions covering:

1. target recovery/cycle salt closure/energy;
2. dual-compartment zero productive reset downtime;
3. high external-volume warning;
4. system-pressure recovery limiter;
5. published membrane-channel liquid-volume geometry;
6. selected-membrane pressure-drop hard stop;
7. Full Water Analysis missing-ion fail-closed behavior;
8. recovery requests above 97% accepted at the API/model layer and then governed by physical limits.

`tests/test_batch_ro_immutable_runtime.py` separately validates direct manifest identity, idempotent repeated verification, missing-file failure, tamper failure, malformed/missing manifest failure, and absence of runtime payload/source-write primitives.

## Final remote validation evidence

### Portable exact-Alpha/read-only proof

GitHub Actions run: `32716551759`

Job: `97398922510`

Result: **SUCCESS**.

Validated against PR merge `4da98d95f0071a55e0ff25ef34460bde74c0cad9`, which GitHub recorded as validation-only head `cc46c953...` merged into executable owner SHA `89835e197fe47bc7f76fe62fff72f939f0fb9daf`.

Observed results:

- Python compile: PASS
- Batch RO owner engineering regressions: **8/8 PASS**
- Batch RO immutable-runtime regressions: **6/6 PASS**
- owner Batch engine byte identity: PASS (`99905e323c...`)
- exact Alpha `14aa40a...` selected: PASS
- exact Alpha Batch payload retained at `04fd024a...`: PASS
- exact Alpha pre-startup materialization and runtime manifest verification: PASS
- exact Alpha Batch numerical regressions: **4/4 PASS**
- exact Alpha immutable-runtime regressions: **6/6 PASS**
- conventional RO regression: **10/10 PASS**
- CCRO regression: **5/5 PASS**
- WSGI import against read-only application source: PASS
- `/healthz`: HTTP **200**
- `/ro`: HTTP **200**, Batch UI loader present
- `batch_ro` registered in `CALCS`: PASS
- Batch calculation route/API: registered and non-404
- repeated WSGI startup: **2/2 PASS**
- source SHA fingerprint before/after both startups: **identical**
- no normal-startup materialization/write primitive: PASS
- no systemd weakening required: PASS

### Self-hosted production-like EC2 proof

GitHub Actions run: `32716551761`

Job: `97398922607`

Runner: `twds-alpha-ec2` on machine `ip-172-31-23-97`

Checked-out executable owner SHA: `89835e197fe47bc7f76fe62fff72f939f0fb9daf`

Result: **SUCCESS**.

Observed results:

- isolated validation venv created under runner temp: PASS
- production venv untouched: PASS
- owner Batch engineering regressions: **8/8 PASS**
- owner immutable-runtime regressions: **6/6 PASS**
- exact Alpha worktree `14aa40a...`: PASS
- exact Alpha server dependencies installed **only** in isolated runner-temp validation venv: PASS
- exact Alpha `04fd...` Batch payload materialized before application startup: PASS
- exact Alpha Batch numerical regressions: **4/4 PASS**
- exact Alpha immutable-runtime regressions: **6/6 PASS**
- conventional RO regression: **10/10 PASS**
- CCRO regression: **5/5 PASS**
- read-only double WSGI startup: **2/2 PASS**
- `/healthz` 200, `/ro` 200, Batch UI loader and Batch calculation route: PASS
- source hashes before/after startup: **identical**
- no source writes beneath application tree: PASS
- no `tarfile.extractall(ROOT)` or equivalent runtime mutation: PASS
- no `ProtectSystem`/`ReadWritePaths`/ownership weakening: PASS
- no production venv operation: PASS

## Security disposition

No correction is required to:

- `ProtectSystem=strict`;
- source-directory ownership or permissions;
- `ReadWritePaths` for `/opt/totalrodesign/app`;
- Gunicorn service identity;
- the production EC2 Python venv.

Validation workflows used isolated runner-temp environments only. The successful EC2 venv recovery is outside this change and remains untouched.

## Final disposition

All mandatory immutable-runtime gates are satisfied for the corrected lifecycle architecture. The Batch RO blocker is ready for **selective reconciliation** into the current Alpha release composition.

Do not merge the specialist branch wholesale. Reconcile the lifecycle correction exactly as documented in `validation/BATCH_RO_IMMUTABLE_RUNTIME_RECONCILIATION_v0.3.md`, preserve the exact Alpha `04fd...` Batch calculation payload for this blocker-only release, and materialize/verify it during release preparation before staging/Gunicorn startup.