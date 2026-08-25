# Total ZLD Design — FFE + Configurable Train Integration Audit R3

Date: 2026-08-24

Branch: `app/total-zld-design`

Validated source SHA: `cb88813b73992c93f7cee870427bf8f1da1ce4e9`

Status: **READY FOR RECONCILIATION — YES, FILES/HUNKS ONLY**

## Scope

R3 closes the browser/project-state blockers identified after the falling-film evaporator and configurable process-train milestone at `1b497d58ae959bc872d7cdd9f95ddd2b27d3583b`.

The engineering equations in `total_zld_design/falling_film_evaporator.py`, `total_zld_design/process_train.py`, `total_zld_design/fo_regression.py`, and `total_zld_design/thermal_legacy.py` were not changed during the blocker-fix cycle.

The blocker-fix delta from `1b497d58...` to the validated source contains only:

- `total_zld_design/web/static/zld.js`
- `total_zld_design/web/static/zld_contract.js`
- `tests/test_zld_project_train_integration.py`

No workflow, deployment, WSGI, database, Suite Core, chemistry, FO regression, thermal regression, or FFE calculation equation changed.

## Blockers fixed

### 1. FFE-only project save

FIXED.

The common ZLD project path now accepts an external unit calculation from `window.ZLDTrain.getActiveCalculation()` when the legacy FO/thermal `last` result is absent. The project snapshot uses `last || external`, so an FFE-only workflow can calculate and save without first running FO or the legacy thermal train.

The project payload carries the configurable `process_train` and the selected `active_unit_instance_id`.

### 2. Multiple FFE instances

FIXED.

The browser now maintains `activeUnitInstanceId`. Opening a train item selects that exact instance and loads its stored FFE `config` and `last_result`. `runFFE()` writes `config` and `last_result` to the selected FFE instance rather than always updating the first FFE in the train.

A separate `latestExternalResult` / `latestExternalInstanceId` retains the most recent FFE calculation for project saving even when the user navigates to a different unit after calculation.

### 3. Project train / FFE restore and stale-state leakage

FIXED.

Train restoration now occurs through the normal `loadProject()` path instead of monkey-patching `window.fetch`.

On project load:

- stored `project.process_train` is restored through `window.ZLDTrain.setState(...)`;
- a missing process train explicitly resets to the default train;
- stored `project.active_unit_instance_id` is selected;
- an FFE project restores the corresponding calculation/configuration to that exact instance.

`newProject()` explicitly resets the configurable train.

### 4. Duplicate calculation listener setup

FIXED.

The old `initEngineeringExtensions` path is removed. The contract script now has one `DOMContentLoaded` initializer and no fetch monkey-patch. Shared calculation-state binding is invoked from that single initializer.

## Protected calculation regressions

The authoritative workbook-derived calculation files remain unchanged:

- `total_zld_design/fo_regression.py` blob `ac30a8143cc2088287f15145fbac4e2ebc657ad2`
- `total_zld_design/thermal_legacy.py` blob `ca5de57c8c6c9b4c2c5f6e7956c336d2fa760d5f`

No fixture regeneration or regression recalibration was performed.

## Validation results

Local validation scratch workspace combined the authoritative v0.2 workbook regression package with the FFE/process-train implementation and integration-state tests.

Result:

- **23 passed**
- **0 failed**
- **0 skipped**
- pytest duration **0.05 s**

The 23 tests cover the authoritative workbook regressions plus FFE design behavior, process-train manipulation/state, and the browser/project integration invariants introduced to close the four blockers.

Python source compilation was also performed on the FFE/process-train modules and their focused integration tests using Python's compiler: all five checked files compiled successfully.

Node.js syntax checks were green on locally reconstructed current client logic. Because the private GitHub checkout is not directly materializable in the execution container, the audit does not claim that Node parsed byte-for-byte GitHub blobs. The authoritative GitHub source was separately inspected at the validated branch tip and confirms the required project/train state paths and removal of the obsolete fetch monkey-patch initializer.

## Falling-film evaporator engineering audit

The FFE calculation remains a design-screening model with a hard applicability guard around the Shahzad/Burhan/Ng horizontal-tube saline falling-film correlation.

Published correlation use is limited to:

- saturation temperature: 280–305 K
- salinity: 35,000–95,000 ppm
- film Reynolds number: 45–90
- Prandtl number: 5–10

Outside that range the ZLD engine requires a separate validated `design_overall_u_w_m2_k` and does not silently use the published correlation as validated hypersaline ZLD physics.

Current FFE design scope includes nonvolatile-solute mass balance, sensible/latent duty, BPE input, LMTD, film HTC, overall U, heat-transfer area, tube count, minimum liquid loading/distributor flow, recirculation/feed ratio, vapor volumetric load and preliminary vapor disengagement diameter.

The correlation remains explicitly horizontal-tube falling-film data, not a universal vertical VFFE correlation.

## Configurable process train audit

The server-side train model remains capable of:

- add
- remove
- move/reorder
- enable/disable
- duplicate unit types with unique instance IDs
- per-instance configuration and last-result persistence
- engineering advisories for unconventional sequences

The browser now binds FFE calculation/configuration to selected instance IDs and project snapshots persist the train.

The current train remains a configuration/state model; it does **not** claim a fully coupled arbitrary-order whole-train process solver.

## CI / tooling

No GitHub status checks are attached to validated source SHA `cb88813b73992c93f7cee870427bf8f1da1ce4e9`.

No workflow or CI configuration was created or modified as part of this milestone.

## Alpha conflict surface

Read-only comparison at R3 audit time:

- ZLD branch ahead of Alpha: 70 commits
- ZLD branch behind Alpha: 123 commits
- merge base: `d6d420ca69695a0266a93734210948b950af4f7b`

Therefore **DO NOT MERGE `app/total-zld-design` WHOLESALE**.

Reconcile by files/hunks only. Preserve Alpha as authoritative for:

- `wsgi.py` and runtime chemistry ordering
- CCRO under `addons/ccro/`
- mobile/PWA behavior and template wiring
- shared pump infrastructure / current `pump_db.py`
- current Suite Core shared UI files
- current Suite dashboard
- deployment configuration

The R3 blocker-fix files are ZLD client/test files and do not authorize restoration of stale branch-owned shared/runtime files.

## Remaining known limitations — not reconciliation blockers

- arbitrary-order train stream handoff/coupled solver is not yet implemented
- multi-effect FFE/MEE vapor and energy cascade is not yet implemented
- rigorous species-specific BPE and hypersaline thermophysical properties remain a Shared Water Chemistry / solution-property dependency
- precipitation/fouling degradation of FFE U requires species/process calibration
- source FFE correlation is horizontal-tube and restricted to its published range
- hypersaline conditions require a validated vendor/pilot/design U
- non-condensable gas and vacuum-system sizing are future equipment-design work
- final mechanical exchanger/shell/tubesheet design remains vendor/mechanical scope

These limitations remain explicitly disclosed engineering-preview scope rather than hidden validation failures.

**VALIDATION AUDIT R3: PASS**

**READY FOR RECONCILIATION: YES — FILES/HUNKS ONLY**
