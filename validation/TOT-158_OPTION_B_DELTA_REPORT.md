# TOT-158 Option B residual-convergence delta report

## Provenance and method

- Starting protected `alpha` branch SHA named by the Board: `5c48824362239ce1083bc42505388e9fe20aa99f`.
- Before measurements used that exact commit in a detached checkout, with reporting-only instrumentation added to expose the accepted iteration's raw residual and relaxation history. The acceptance predicate remained unchanged.
- After measurements used the TOT-158 implementation checkout. Both checkouts used `/home/paperclip/.venvs/tot57/bin/python`.
- Each runtime is one `time.perf_counter()` observation and is descriptive, not a performance benchmark.
- Flow tolerance: `max(0.001 m3/h, 0.0001 * max(1, element feed m3/h))`; TDS tolerance: `0.000001 * max(1, element feed mg/L)`. These registered values were not changed.

## Raw before output

```text
{"c_residual_mg_l": 0.0028407809547967844, "case": "TOT-73-BWRO", "damping_history": [0.45], "final_damping": 0.45, "iterations": 16, "observed_salt_rejection_pct": 99.51727806856971, "permeate_flow_m3h": 1.7333414658283812, "permeate_tds_mg_l": 9.654438628605954, "q_residual_m3h": 0.0001641417665645406, "recovery": 0.1485721256424327, "runtime_s": 0.0005838650104124099}
{"c_residual_mg_l": 0.06835575489621704, "case": "TOT-73-SWRO", "damping_history": [0.45], "final_damping": 0.45, "iterations": 13, "observed_salt_rejection_pct": 99.77843578983412, "permeate_flow_m3h": 1.1767938642485194, "permeate_tds_mg_l": 70.90054725308313, "q_residual_m3h": 0.00035158089836784256, "recovery": 0.07955789504778722, "runtime_s": 0.00047416897723451257}
{"c_residual_mg_l": -0.4770779318798759, "case": "TOT-158-damped", "damping_history": [0.45, 0.225, 0.12], "final_damping": 0.12, "iterations": 86, "observed_salt_rejection_pct": 98.03692497572676, "permeate_flow_m3h": 0.14186027874353455, "permeate_tds_mg_l": 1177.8450145639354, "q_residual_m3h": -5.397681548890976e-06, "recovery": 0.14186027874353455, "runtime_s": 0.0017617010162211955}
```

The before predicate reported all three cases as converged. The damped case's true TDS residual was `0.4770779318798759 mg/L`, exceeding its `0.06 mg/L` tolerance even though the 12% relaxed step was inside tolerance.

## Raw after output

```text
{"c_residual_mg_l": 0.0016535724120956274, "case": "TOT-73-BWRO", "damping_history": [0.45], "final_damping": 0.45, "iterations": 17, "observed_salt_rejection_pct": 99.51724086319042, "permeate_flow_m3h": 1.7333812607848724, "permeate_tds_mg_l": 9.655182736191398, "q_residual_m3h": 8.843323664731173e-05, "recovery": 0.14857553663870335, "runtime_s": 0.0005754079902544618}
{"c_residual_mg_l": 0.022658415989653236, "case": "TOT-73-SWRO", "damping_history": [0.45], "final_damping": 0.45, "iterations": 15, "observed_salt_rejection_pct": 99.7783484135821, "permeate_flow_m3h": 1.1769145705456894, "permeate_tds_mg_l": 70.92850765372786, "q_residual_m3h": 9.02197551864159e-05, "recovery": 0.0795660554735114, "runtime_s": 0.0004933489835821092}
{"c_residual_mg_l": -0.05617604316125835, "case": "TOT-158-damped", "damping_history": [0.45, 0.225, 0.12], "final_damping": 0.12, "iterations": 103, "observed_salt_rejection_pct": 98.0375527439302, "permeate_flow_m3h": 0.14185601716074026, "permeate_tds_mg_l": 1177.4683536418818, "q_residual_m3h": -6.355849230255117e-07, "recovery": 0.14185601716074026, "runtime_s": 0.004230113001540303}
```

All after cases converged with both true residuals inside the unchanged tolerances. The 240-iteration budget was sufficient; it was not raised.

## Output deltas (after minus before)

| Case | Quantity | Absolute delta | Relative delta |
|---|---:|---:|---:|
| TOT-73 BWRO | permeate flow, m3/h | 0.00003979495649120146 | 0.002295852102758244% |
| TOT-73 BWRO | permeate TDS, mg/L | 0.0007441075854437429 | 0.007707414320693526% |
| TOT-73 BWRO | recovery fraction | 0.0000034109962706585506 | 0.002295852102747569% |
| TOT-73 BWRO | salt rejection, percentage points | -0.00003720537928586509 | -0.00003738584897813395% |
| TOT-73 SWRO | permeate flow, m3/h | 0.00012070629716998127 | 0.010257216734135698% |
| TOT-73 SWRO | permeate TDS, mg/L | 0.027960400644730043 | 0.0394360857962407% |
| TOT-73 SWRO | recovery fraction | 0.000008160425724171305 | 0.01025721673414017% |
| TOT-73 SWRO | salt rejection, percentage points | -0.00008737625202570598 | -0.00008757027641698936% |
| TOT-158 damped | permeate flow, m3/h | -0.000004261582794290453 | -0.0030040705065826467% |
| TOT-158 damped | permeate TDS, mg/L | -0.37666092205358837 | -0.031978818723704214% |
| TOT-158 damped | recovery fraction | -0.000004261582794290453 | -0.0030040705065826467% |
| TOT-158 damped | salt rejection, percentage points | 0.0006277682034436793 | 0.0006403385291808267% |

## Governed-case disposition

| Source | Available/applicable at starting SHA | Layer A | Layer B | Evidence |
|---|---|---|---|---|
| TOT-18 Batch RO | Batch RO code is present but uses its independent immutable runtime, not `membrane_stage` | NOT ESTABLISHED | NOT ESTABLISHED | No applicable Option B case was identified; no inference from another engine. |
| TOT-3 / TOT-92 | No conventional-RO case or approved expected-output registry is present at the starting SHA | NOT ESTABLISHED | NOT ESTABLISHED | The separately existing TOT-3 branch corpus contains chemistry, FO, thermal, BNR, and WaterStream entries, but no RO entry. No TOT-92 case was found. |
| TOT-73 BWRO | Historical manifest object is available, but the manifest and detached approval are absent from the starting SHA and record `NOT_APPROVED` / null approval metadata | NOT ESTABLISHED | NOT ESTABLISHED | Inputs were run for comparative measurement only; the historical record cannot authorize a PASS/FAIL disposition. |
| TOT-73 SWRO | Same as TOT-73 BWRO | NOT ESTABLISHED | NOT ESTABLISHED | Inputs were run for comparative measurement only; the historical record cannot authorize a PASS/FAIL disposition. |

No benchmark, golden value, preregistration record, tolerance, engine equation, chemistry path, composition-residual criterion, or WaterStream schema was changed.

## Focused test evidence

```text
$ /home/paperclip/.venvs/tot57/bin/python -m pytest -q tests/test_conventional_ro_regression.py
............                                                             [100%]
12 passed in 10.69s
```

The attempted Batch RO availability check was not a valid runtime certification because the Board-selected starting SHA does not contain `addons/batch_ro/__init__.py` or `deploy/batch_ro_runtime_manifest.json`:

```text
$ /home/paperclip/.venvs/tot57/bin/python -m pytest -q tests/test_conventional_ro_regression.py tests/test_batch_ro_immutable_runtime.py tests/test_batch_ro_runtime_integration.py
............FFFFF..                                                      [100%]
ERROR: Batch RO runtime manifest is missing: deploy/batch_ro_runtime_manifest.json.
FileNotFoundError: addons/batch_ro/__init__.py
5 failed, 14 passed in 14.57s
```
