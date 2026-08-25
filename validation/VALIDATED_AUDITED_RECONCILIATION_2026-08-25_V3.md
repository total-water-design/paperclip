# TWDS Validated / Audited Reconciliation Ledger — 2026-08-25 V3

Starting protected Alpha / rollback target: `7851e9037ea39f0215765c30361a8692af0c64a2`

Reconciliation branch: `reconcile/validated-audited-ready-20260825-v3`

## Logical inventory

### Already represented in Alpha — no replay
- Suite Core / platform: validated Core launch-policy reconciliation is already in protected Alpha.
- Shared WaterStream / Shared Water Chemistry: preserve the previously validated integrated composition; do not use unapproved branch tips.
- Total Bio Design: previously audited milestone already represented.
- Total Water Academy: preserve the already-reconciled Academy version currently in Alpha.
- Total Water Balance: previously validated milestone already represented.
- Total ZLD Design: previously validated R3 milestone already represented.

### Included — Total Water Economics UI polish
Authoritative validated source: `ddfb1aae9c0b8f6811adb39951d4287124f057d4`

Audit/readiness tip: `51ea0c5147733255a1d6c97cc6e3ae6c81a97f1f`

Authoritative validation:
- workflow `Total Water Economics CI`
- run `32862098365`
- job `97848345812`
- conclusion `success`
- audit evidence: 63/63 tests plus Python compile and JavaScript syntax validation

Exact selectively reconciled paths:
- `static/economics_finance.css`
- `static/economics_polish.css`
- `templates/economics_suite_v04.html`
- `tests/test_water_economics_finance_ui.py`

Explicitly excluded:
- `.github/workflows/total-economic-design-ci.yml` — owner validation machinery, not runtime/product source.
- all Economics calculation and finance engines, including `economics.py`, `project_finance.py`, `total_economic_design.py`, economic schemas/guardrails/aggregators and RO economic adapters.

### Held — Total Water Academy v1.5 refresh
Validated implementation claimed by owner audit: `6155ea2f1fe6ac6823bc0f1668b0d1790abb3d5a`.
Audit record: `da85effc02a1a29fb99af09dcd968f93b5d9e5f5`.
Owner run: `32862938585` / job `97851142289`.

Reconciliation candidate `38efa5b24729111989f440949b9c8b562b871293` was NOT promoted. Integrated source/runtime validation passed, but real Chromium exposed an owner-source runtime defect: `/academy/placement` returned HTTP 500 because exact certified template `templates/academy/placement.html` dereferences `academy_meta.dir` while exact certified `academy_placement.py` does not provide `academy_meta` to `render_template`. Reconciliation does not develop owner fixes; Academy v1.5 is held until the Academy owner corrects and re-certifies the source. The current Alpha Academy remains authoritative.

### Held — Total Pretreatment Design
Current observed owner milestone had reconciliation handoff documentation but no qualifying exact authoritative successful Pretreatment validation/certification run identified. Held until owner supplies exact audited/validated milestone and run.

### Held — Total Post-Treatment Design
Owner branch still records unresolved cross-owner reconciliation blockers. Held until a reconciliation-ready audited milestone exists.

### Held — Total RO Design
The user-supplied Total RO Agent-2 reconciliation contract requires an exact successful certified owner SHA/run pair and prohibits inference from branch names, branch HEAD, logs or prior conversation. That pair has not been supplied under the contract, so no new RO source is reconciled in this campaign.

### Held — Total Water Design — System Integration & Optimization
No explicit current app-specific audited/validated reconciliation milestone identified.

## Engineering and runtime freeze

Starting Alpha remains authoritative for all engineering and runtime calculation surfaces. The v3 candidate must not modify:
- `calculations.py`
- Total RO frontend/runtime
- CCRO / Batch RO
- Shared Chemistry / WaterStream
- membrane / pump calculations
- RO economics calculations
- Total Water Economics engineering/finance engines
- Bio, Water Balance, ZLD, Academy runtime
- WSGI / authentication / Suite Core services
- dependencies
- deployment workflows or deployer hardening

## Required integrated validation

Before protected Alpha promotion, exact v3 candidate must pass:
- exact starting-Alpha ancestry and five-path allowlist (four Economics files + this ledger);
- exact Economics owner blob identity;
- all engineering/runtime preservation checks;
- Python/JavaScript syntax applicable to changed files;
- full applicable Total Water Economics regression matrix;
- current Suite startup and `/healthz`;
- Economics route/template rendering in local validation mode;
- baseline RO/ZLD/Academy/CCRO/Batch preservation;
- immutable Batch RO materialization/check;
- final Alpha immutability check.

No AWS deployment is authorized by this reconciliation campaign.