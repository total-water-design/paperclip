# Shared WaterStream Validation Audit Gate

Status: **VALIDATION AUDIT PASSED — v0.5 freeze candidate**

Current public candidate: `shared_waterstream` v0.5 (`shared_waterstream/v05.py`).

This gate replaces the earlier adoption-based freeze criterion. Application adoption is intentionally not required: specialist applications remain independently owned and may adopt the contract on their own schedules.

## A3 — Freeze WaterStream v1.0

All three checkable pre-freeze conditions are satisfied.

### 1. Current-version invariant coverage — SATISFIED

All 21 still-valid invariants inherited from v0.2/v0.3 are exercised directly against the current package root by `tests/test_shared_waterstream_v05_legacy_invariants.py`.

The 25-test current audit suite additionally covers deterministic/lossless serialization, H2O and TOTH ledger closure, explicit phase-outlet accounting, mixing commutativity/associativity, idempotence, certificate trust boundaries, engine-isolated caching, chemistry-policy hashing, mixed/non-volumetric refusal, selective-split certificate behavior, shared-phase-component refusal, nonzero-TOTH selective-split refusal, and UnitOp conformance.

### 2. Overlay consolidation — SATISFIED AND EXECUTED

The active package root exports only the self-contained `shared_waterstream.v05` implementation. Archived v0.1-v0.4 runtime modules and archived executable WaterStream suites were removed from the active branch after their still-valid invariants were ported to v0.5. Their history remains available in Git and historical architecture documents remain as evidence.

After cleanup, GitHub Actions run `32618084928` executed the current suites from a clean checkout and concluded **success**:

- v0.5 audit suite: **25/25 passed** in **0.037 s**;
- 21 still-valid historical invariants directly against v0.5: **21/21 passed** in **0.018 s**;
- total current-version post-cleanup evidence: **46/46 passed**, 0 failed.

### 3. Final adversarial spike — SATISFIED

The final Water Balance attack was executed from `app/total-water-balance` against exact cleaned candidate `engine/shared-waterstream@3bed2344bcc8137b71563f9c5c81781b5829e03b` by GitHub Actions run `32618195506`.

The run concluded **success** and enforced:

- `findings == []`;
- `freeze_gate_attack_result == "PASS"`;
- the attack-reported candidate SHA exactly matched the Shared WaterStream base SHA.

The attack reported only explicit correct refusals and the documented chemistry trust boundary:

- false residual charge rejected;
- false solvent-water inventory rejected;
- blank chemistry engine provenance rejected;
- incompatible chemistry policies rejected;
- over- and under-claimed phase inventories rejected;
- shared-component phase partition delegated to owner physics;
- nonzero-TOTH selective split delegated to owner physics;
- ionic strength, density and solution mass remain explicitly issuer-trusted because WaterStream does not re-solve chemistry.

No silent inference, stale-state acceptance, cache/provenance ambiguity, conservation gap, or unsupported plausible numeric result was found.

## Trust boundary

`state_hash` proves which stream state a `ChemistryCertificate` claims to describe. It does **not** independently prove every chemistry value inside the certificate.

WaterStream independently verifies certificate state identity, solvent-water inventory, and fixed-charge residual where recomputable. Ionic strength, density and solution mass remain trusted chemistry-engine outputs because verifying them would duplicate the chemistry solve. `assert_issuer_conformant()` makes this residual trust surface explicit and checks determinism, warm-start equivalence, provenance, engine identity and independently recomputable fields.

## Fourth-spike disposition

- **V — cross-engine cache reuse:** closed in v0.5 by cache isolation on `(state_hash, engine_version)`.
- **W — blank chemistry provenance:** closed in v0.5; blank/mismatched engine provenance is rejected and chemistry-policy mismatch fails closed.
- **Y — selective nonzero-TOTH partition:** closed in v0.5 by refusing generic selective partition of nonzero TOTH.
- **T/U — residual certificate trust surface:** explicitly documented and guarded by issuer conformance.
- **X — phase inventory closure:** over/under claims and shared-component phase partition are refused.

## Mutation evidence

The current candidate has targeted mutation evidence for round-trip serialization, H2O closure, TOTH closure, mixing commutativity, mixing associativity, idempotence, engine-isolated caching, engine provenance, selective nonzero-TOTH refusal, and independent UnitOp H2O/TOTH closure paths. Deliberate defects made the corresponding tests go RED.

## Audit conclusion

**Shared WaterStream v0.5 passes the validation audit.**

The next step is the deliberate semantic freeze to schema v1.0. That freeze is a product/architecture commitment rather than additional defect discovery and should be recorded as a separate explicit freeze commit.

A passing compile step was not used as a substitute for test execution.