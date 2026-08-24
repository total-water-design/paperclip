# Shared WaterStream v0.5 — Validated Freeze Candidate

**Status:** validation audit passed; ready for deliberate v1.0 freeze decision.  
**Schema version:** `0.5.0`  
**Owner branch:** `engine/shared-waterstream`

v0.5 responds to the fourth Total Water Balance attack spike and makes the validation boundary explicit and finite. It remains schema v0.5 until a separate deliberate v1.0 freeze commit.

## 1. Consolidated current implementation

The package-level current contract is implemented in one module:

`shared_waterstream/v05.py`

`import shared_waterstream` exports the v0.5 module only. Archived v0.1-v0.4 runtime modules and archived executable WaterStream suites have been removed from the active branch after their still-valid invariants were ported to v0.5. Prior versions remain recoverable from Git history and historical architecture documents remain as evidence.

## 2. Certificate trust boundary

`state_hash` proves which transported state a `ChemistryCertificate` claims to describe. It does **not** prove that all chemistry values in the certificate are scientifically correct.

WaterStream independently verifies at certificate attachment:

- `state_hash` matches the stream state;
- `solvent_water_kg_s` matches the authoritative H2O component inventory;
- `residual_charge_eq_s` matches charge independently recomputed from charge-explicit transported components.

`ionic_strength_mol_kg`, `density_kg_m3`, and `solution_mass_kg_s` remain trusted outputs of Shared Water Chemistry because WaterStream cannot verify them without repeating the chemistry calculation.

`assert_issuer_conformant()` reports this residual trust surface explicitly as `trusted_not_independently_verified` and additionally requires deterministic identical-input results, warm/cold agreement within declared tolerance, nonempty engine provenance, and issuer/certificate engine-version agreement.

## 3. Cache isolation

`ChemistryCertificateCache` is keyed by `(state_hash, engine_version)`. Different chemistry engines cannot reuse each other's cached certificate for the same transported state.

## 4. Chemistry policy

`chemistry_policy` is fully hash-participating, including unknown nested values. Generic mixing refuses incompatible chemistry policies rather than selecting one silently.

## 5. Selective split and TOTH

A generic selective split has no scientifically defensible rule for partitioning nonzero TOTH when analytical components move at different fractions.

Therefore v0.5 fails closed: per-component selective split with nonzero TOTH raises `SelectiveSplitError` and requires owner unit-operation physics to assign daughter TOTH explicitly. No H2O-, TIC-, or other surrogate partition is inferred.

## 6. Phase inventory

`phase_inventory` must close to stream component totals. Over- and under-stated inventories are rejected. If a component occurs in more than one phase item, generic selective split refuses to partition it and delegates separation physics to the owner.

## 7. UnitOp conformance

`assert_unitop_fail_closed()` independently reconstructs material closure from returned outlets. It covers owner-transform policies, conserved tracked state, H2O/component closure, TOTH closure, selective-split certificate behavior, and explicit phase-outlet double-count rules.

## 8. Executed validation evidence

The current contract has two authoritative suites:

- `tests/test_shared_waterstream_v05_audit.py` — 25 current audit tests;
- `tests/test_shared_waterstream_v05_legacy_invariants.py` — all 21 still-valid historical invariants executed against the current package root.

Post-cleanup GitHub Actions run `32618084928` concluded **success** from a clean checkout after archived runtime modules and executable suites had been removed:

- **25/25** audit tests passed in **0.037 s**;
- **21/21** historical-invariant ports passed in **0.018 s**;
- **46/46 current tests passed**, 0 failed.

Final attack workflow run `32618195506` again ran the cleaned current suites and concluded **success**:

- **25/25** audit tests passed in **0.018 s**;
- **21/21** historical-invariant ports passed in **0.009 s**;
- the Water Balance final attack returned `findings=[]` and `freeze_gate_attack_result="PASS"`.

The candidate has targeted mutation evidence for round-trip serialization, H2O closure, TOTH closure, mixing commutativity, mixing associativity, idempotence, engine-isolated caching, engine provenance, selective nonzero-TOTH refusal, and independent UnitOp H2O/TOTH closure paths. Deliberate defects made the corresponding tests go RED.

## 9. Final Water Balance attack disposition

The final attack produced no architecture findings. It reported only correct refusals and the explicitly documented chemistry trust boundary:

- false residual charge rejected;
- false solvent-water inventory rejected;
- blank engine provenance rejected;
- incompatible chemistry policies rejected;
- inconsistent phase inventories rejected;
- shared-component phase separation delegated to owner physics;
- nonzero-TOTH selective split delegated to owner physics;
- ionic strength, density and solution mass remain issuer-trusted because WaterStream does not re-solve chemistry.

## 10. Tear vector and scaling

Tear-variable definition, acceleration, scaling and recycle-solver policy remain owned by Total Water Balance. They are not part of Shared WaterStream.

## 11. A3 — WaterStream v1.0 freeze gate

1. **Current invariant coverage:** satisfied.
2. **Overlay/runtime cleanup:** satisfied and post-cleanup tested.
3. **Finding-free final attack:** satisfied.

**Validation audit result: PASS.**

Application adoption is not a freeze prerequisite. The next action, if authorized, is a separate deliberate v1.0 schema freeze commit.