# Shared WaterStream Contract v0.3

**Status:** breaking architectural prototype / not frozen  
**Schema:** `twds.water-stream`  
**Version:** `0.3.0`  
**Owner branch:** `engine/shared-waterstream`

v0.3 responds directly to the second Total Water Balance attack spike at `app/total-water-balance@76769c0d7935e8e26691bdc5057c76cc549b4656`. It remains a prototype and is not a v1.0 freeze candidate.

## Breaking changes

### Selective split

`split_water_stream()` now requires `composition_preserving` explicitly; there is no default. The split specification may be either scalar daughter fractions for a uniform split or per-component daughter fractions for a selective split.

A ChemistryCertificate is rebound only when all three conditions are true:

1. the split uses uniform scalar fractions;
2. `composition_preserving is True`; and
3. the parent phase is `AQUEOUS`.

Selective splits never rebind a certificate. MIXED, SOLID and GAS splits never rebind a certificate. The Water Balance reproducer requiring 80% water and 20% calcium is represented directly instead of collapsing to a uniform 70/30 split.

### Non-volumetric flow

`flow_m3_s` is available only for certified `AQUEOUS` streams. `SOLID`, `GAS` and `MIXED` streams raise `NonVolumetricFlowError`; they never return a silent numeric zero.

### Mixed-phase thermal behavior

The generic mixer calculates temperature only when every inlet is `AQUEOUS`. If any non-aqueous phase is present, it raises `MixedPhaseThermalError` unless an owner process explicitly supplies `output_temperature_c` from its thermal/enthalpy model. This prevents solids from silently receiving zero thermal weight.

## Additive changes

### Structured phase inventory

The scalar `mineral_identity` field is removed. `phase_inventory` contains `PhaseInventoryItem` records with phase, optional identity such as `calcite`, component totals assigned to that phase, and optional metadata. The phase inventory must close back to the stream's authoritative component totals.

Mixing a calcite solids stream with an aqueous stream therefore produces a `MIXED` stream that retains a `SOLID/calcite` inventory item instead of losing mineral identity.

### Chemistry certificate issuer and cache interface

`ChemistryCertificateIssuer` defines the Shared Water Chemistry production boundary:

`issue(stream, *, warm_start=previous_certificate) -> ChemistryCertificate`

`ChemistryCertificateCache` is keyed strictly by `state_hash`. `certify_stream()` checks the cache first, otherwise calls the issuer and forwards an optional previous certificate as a warm-start seed. Equilibrium physics and cache persistence remain owned by Shared Water Chemistry.

### UnitOp conformance suite

`shared_waterstream.conformance.assert_unitop_fail_closed()` publishes mandatory cross-application fail-closed tests. A specialist UnitOp adapter must raise when it receives either an `OWNER_MUST_TRANSFORM` tracked quantity without a tracked transformer or an `OWNER_MUST_TRANSFORM` extension without an extension transformer.

### Overlay consolidation

The package root now exports v0.3 definitions from `shared_waterstream.v03`. `FrozenDict`, registry classes, extension types, provenance and raw-analysis types are all defined in v0.3 instead of implicitly leaking from v0.1 modules.

Historical v0.1 and v0.2 modules remain only for explicit historical/migration tests. Consumers that intentionally need them must import their versioned modules directly, such as `shared_waterstream.v02` or `shared_waterstream.models`.

## Regression reproductions

The v0.3 tests include the second Water Balance spike's exact failure patterns:

1. an uneven MIXED split with 80% H2O/Na/Cl and 20% Ca/TIC goes to the requested component partition and does not rebind a certificate;
2. `SOLID.flow_m3_s` and `GAS.flow_m3_s` raise instead of returning `0.0`;
3. mixed-phase temperature with a solid inlet raises unless an owner-computed output temperature is supplied;
4. mixing `SOLID/calcite` with `AQUEOUS` preserves calcite in the phase inventory;
5. uniform AQUEOUS split rebinds only with explicit `composition_preserving=True`;
6. the certificate cache is keyed by `state_hash` and issuer calls receive a warm-start certificate when supplied;
7. the UnitOp conformance suite detects tracked-quantity and extension fail-open implementations.

The v0.2 H2O ledger and TOTH closure protections remain in v0.3.

## Not adopted

No tear vector, residual scaling vector, Wegstein/Broyden state vector or equation-oriented solver representation is added to Shared WaterStream. Those remain Total Water Balance responsibilities.

## Still prototype-only

v0.3 has not been validated against full Shared Water Chemistry equilibration, biological state, real pretreatment separators, real ZLD crystallizer thermodynamics or production-scale recycle networks. Those attacks are required before any v1.0 proposal.
