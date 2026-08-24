# Shared WaterStream Contract v0.4

**Status:** breaking architectural prototype / not frozen  
**Schema:** `twds.water-stream`  
**Version:** `0.4.0`  
**Owner branch:** `engine/shared-waterstream`

v0.4 is the direct response to the third Total Water Balance attack spike at `app/total-water-balance @ 85d1f4195e7c955c83f893683d7c8281d2029c28`.

## Trust boundary

A `state_hash` proves which serialized chemistry-relevant state a certificate **claims** to describe. It does **not** prove that every chemistry value inside the certificate is scientifically correct.

The contract independently verifies only quantities that are directly recomputable from the transported stream state:

- `residual_charge_eq_s` against the canonical charged-component inventory;
- `solvent_water_kg_s` against the authoritative H2O component total;
- `state_hash` against the complete hash-participating stream state.

Other certificate values, including ionic strength, density and solution mass, remain trusted outputs of the Shared Chemistry issuer. Their correctness is therefore guarded through issuer conformance rather than inferred from the hash.

A certificate with a correct `state_hash` but stale independently-recomputable charge or solvent-water values is rejected when attached to a `WaterStream`.

## Issuer conformance

Every `ChemistryCertificateIssuer` is expected to expose:

- `engine_version`;
- `declared_tolerance`;
- `issue(stream, warm_start=...)`.

`assert_issuer_conformant()` checks:

1. cold and warm-started results agree within the issuer's declared absolute tolerance;
2. repeated cold issues from identical inputs serialize bit-for-bit identically;
3. residual charge passes the independent stream recomputation check;
4. solvent-water mass passes the independent H2O check.

Warm starts may change computational cost and iteration count. They must not change the accepted answer beyond the declared tolerance.

## Chemistry policy namespace

`WaterStream.chemistry_policy` is a reserved immutable namespace that always participates in `state_hash`.

All nested values, including values unknown to the current schema version, are serialized into the hash. This allows future chemistry-affecting policy such as redox mode, gas boundary, phase-equilibrium policy or other solver boundary conditions to invalidate the certificate cache immediately without waiting for promotion into a first-class field.

Ordinary unknown top-level fields remain preserved for forward compatibility but are not presumed chemistry-relevant. Chemistry-affecting policy must be placed in `chemistry_policy`.

## Selective split fail-closed rule

The v0.3 per-component selective split is retained, but v0.4 refuses a selective split whenever a component being partitioned appears in more than one `phase_inventory` item.

Example: calcium appearing in both calcite and gypsum cannot be partitioned correctly by one canonical `calcium` fraction. The contract now raises `SelectiveSplitError` and directs the caller to an owner unit-operation transform.

The contract deliberately does **not** add `(phase, identity, component)` separation efficiencies. Size-, density-, settling-, flotation- and hydrodynamics-based separation belongs to the owning Pretreatment, Bio or ZLD process model.

Uniform scalar splitting remains valid. Certificate rebinding remains allowed only when all of the following are true:

- the split is scalar/uniform;
- `composition_preserving=True` was explicitly supplied;
- the parent phase is `AQUEOUS`;
- the parent has a valid chemistry certificate.

All other splits invalidate chemistry.

## UnitOp conformance

`assert_unitop_fail_closed()` now tests more than owner-managed state.

The suite verifies:

- `OWNER_MUST_TRANSFORM` tracked quantities fail closed without a transformer;
- `OWNER_MUST_TRANSFORM` extensions fail closed without a transformer;
- `CONSERVED` tracked quantities are not silently dropped or reclassified;
- actual output streams independently close component mass, including H2O;
- actual output streams close TOTH unless an explicit `toth_delta_eq_s` is reported;
- selective split does not rebound a chemistry certificate;
- explicit solid outlet plus `transferred_to_solid` double-counting remains forbidden.

Where a UnitOp supplies its own `MassLedger`, the conformance suite checks that ledger and also rebuilds an independent ledger from the actual stream outputs so a fabricated ledger cannot hide material loss.

## Historical prototypes

The package root now exposes the v0.4 stream/certificate/trust/transport surface. Historical v0.1/v0.2/v0.3 modules remain available only through explicit versioned imports for regression and architecture archaeology.

Some stable value-object definitions inherited unchanged from v0.3 remain implementation dependencies of the v0.4 module; they are intentionally imported by v0.4 rather than surfaced implicitly from the package root.

## Not adopted

Tear vectors, residual scaling and equation-oriented convergence state remain Total Water Balance solver responsibilities. They are not part of the Shared WaterStream contract.

## Required v0.4 regressions

The branch includes the exact third-spike reproducers:

1. an issuer whose warm-start answer shifts ionic strength by `2e-12` fails issuer conformance when its declared tolerance is `1e-12`;
2. a certificate with the correct daughter `state_hash` but stale parent residual charge is rejected at attachment;
3. a UnitOp that loses 10% H2O and silently changes TOTH by `0.25 eq/s` fails UnitOp conformance;
4. a selective split of calcium shared by calcite and gypsum raises instead of inventing a phase partition;
5. streams differing only inside `chemistry_policy` produce different state hashes and separate cache entries.

v0.4 remains an attackable prototype. No v1.0 freeze is proposed.
