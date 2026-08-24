# Shared WaterStream Contract v0.1

**Status:** architectural prototype / intentionally not frozen  
**Schema:** `twds.water-stream`  
**Version:** `0.1.0`  
**Owner branch:** `engine/shared-waterstream`

This package defines the experimental cross-application engineering stream contract for the Total Water Design Suite. It is deliberately independent from specialist process physics and from the Shared Water Chemistry implementation.

## Architectural boundary

Shared WaterStream owns immutable transport state, canonical component identifiers and legacy aliases, raw-analysis audit representation, TOTH/proton-condition transport, charge-residual invariants, tracked non-equilibrium quantities and declared mixing rules, namespaced specialist extensions and fail-closed transport policies, deterministic serialization/content hashes, lightweight provenance, and the initial MassLedger data contract.

Shared WaterStream does **not** solve pH or aqueous equilibrium; Pitzer/Debye-Hückel activity; carbonate/ammonia/phosphate speciation; osmotic pressure; membrane transport; precipitation; biological kinetics; dosing; or permanent flowsheet/recycle physics. Those remain specialist/shared-chemistry responsibilities.

## RawWaterAnalysis vs WaterStream

`RawWaterAnalysis` preserves laboratory/user input for audit: original name, value, unit, optional canonical component mapping, analytical charge imbalance, reconciliation decision, provenance and unknown future fields.

An unresolved `RawWaterAnalysis` cannot seed a simulation `WaterStream` through the provided factory. Reconciliation itself is intentionally external to this package.

`WaterStream` is a frozen reconciled simulation object. Its authoritative transported chemical state is:

- `component_totals_mol_s`: canonical extensive analytical/component totals;
- `toth_eq_s`: extensive proton-condition/TOTH rate;
- `diagnostics.residual_charge_eq_s`: numerical invariant residual only.

pH is absent from the schema. The deserializer explicitly rejects a top-level pH/hydrogen-activity field. Registry entries marked as derived equilibrium species, including bicarbonate, carbonate, ammonium and ammonia, are also rejected as authoritative `component_totals_mol_s`. A future chemistry adapter must reconstruct/translate those through the chemistry-owned analytical basis.

## Canonical component registry

The registry provides canonical identifiers, display names, charge/molar-mass metadata where meaningful, quantity type, transport role and aliases.

For example, `bicarbonate`, `HCO3`, `HCO3-` and `ion_bicarbonate` all resolve to the same registry identifier. That canonical entry is marked `DERIVED_ONLY`, preventing it from becoming a second persistent source of truth in `WaterStream`.

Existing RO naming is not rewritten in this milestone. Adapters are expected to translate legacy representations later.

## TOTH rule

Prototype algebra treats `toth_eq_s` as an extensive conserved quantity.

- conservative mixer: sum TOTH;
- splitter: scale TOTH by split fraction;
- conservative pass-through: preserve TOTH;
- reactive specialist unit: may change TOTH only through an explicit process transformation that can ultimately be represented in the MassLedger/reaction record.

This package never converts TOTH to pH.

## Charge residual

`StreamDiagnostics` carries `residual_charge_eq_s` and `charge_tolerance_eq_s`, and exposes `residual_charge_eq_h` as a convenience diagnostic.

A stream whose absolute residual exceeds its explicit tolerance fails construction/deserialization with `ChargeResidualError`. No balancing ion is silently invented.

## TrackedQuantity

`TrackedQuantity` carries value (or explicit unavailable state), unit, dimension/type, mixing rule, diagnostic reason and metadata.

Supported rules are `EXTENSIVE_SUM`, `FLOW_WEIGHTED` and `NOT_MIXABLE`.

Units are not silently converted in v0.1. Inputs with incompatible unit/dimension/rule fail. A `NOT_MIXABLE` quantity becomes explicitly unavailable after a mixer with a diagnostic reason; it is never averaged.

## Extension namespaces

Each extension carries an owner-declared `ExtensionSpec` and opaque payload.

Supported policies are `PASS_THROUGH`, `FLOW_PROPORTIONAL`, `OWNER_MUST_TRANSFORM`, `DROP_AT_BOUNDARY` and `NONTRANSPORTABLE`.

Transport fails closed. `PASS_THROUGH` requires identical state across mixer inputs unless the owner supplies a transformer. `FLOW_PROPORTIONAL` can automatically scale only top-level numeric fields explicitly declared by the namespace owner; otherwise an owner transformer is required. `OWNER_MUST_TRANSFORM` and `NONTRANSPORTABLE` raise when no valid handling exists.

## Deterministic serialization

All primary contracts preserve unknown/future fields where practical and use deterministic JSON with sorted keys, compact separators and finite numbers only. SHA-256 content hashes are available for future chemistry-state caching, regression fixtures and memoization.

Version `0.1.0` is experimental. A future incompatible prototype may change the schema before a proposed v1.0 freeze.

## MassLedger contract

`MassLedger` is data-only. Per component it can record component in, component out, generated, consumed, transferred to solid, transferred to gas, chemical dose added, accumulation and residual.

It also carries explicit `ReactionTransformation` records using reaction ID, from/to component IDs, molar extent and stoichiometric coefficient.

No kinetics, precipitation, dosing or biological calculations are implemented.

## Prototype mixer/splitter

`mix_water_streams` and `split_water_stream` exist only to stress the contract. They validate conservation, tracked-quantity behavior, extension transport, TOTH invariants and serialization. They are **not** the permanent Total Water Balance solver.

For this prototype mixer only, transported extensive states are summed exactly, temperature is flow-weighted, and output pressure is the minimum inlet pressure. The latter two are provisional transport conventions, not a claim that a production mixer should omit enthalpy/hydraulic calculations.

## Compatibility observations

The current Suite baseline still has `flowsheet.Stream` in Total RO Design with `flow_m3h`, `tds_mg_l`, `composition_mg_l`, `carbonate_state` and derived `ph`. No RO code is modified here.

The separate `engine/shared-water-chemistry` branch currently defines its own `WaterState` handoff with composition, pH, TA and CT. Shared WaterStream v0.1 does not merge or replace it. Reconciliation must later define the adapter between chemistry-owned analytical/equilibrium state and the WaterStream authoritative component-total + TOTH representation.

## v0.1 validation gate

The contract tests cover all 18 required invariant areas plus additional immutability, registry, unresolved-analysis and MassLedger checks. Randomized deterministic loops are used for commutativity/associativity without adding a Hypothesis dependency to the Suite.

## Known v0.1 questions to attack in the Water Balance spike

- Is mol/s the best canonical component-total basis for every application, or should some analytical families retain explicit mass/basis metadata?
- Should TOTH remain eq/s in the handoff or use another chemistry-owned proton-condition representation?
- What exact adapter should bridge Shared Chemistry `WaterState` TA/CT and Shared WaterStream TOTH without duplicating chemistry?
- Should zero-flow solid/sludge streams be represented by WaterStream extensions, a sibling material-stream contract, or a generalized phase-aware stream?
- Which tracked quantities need standard Suite definitions beyond COD/BOD/TOC/TSS, turbidity, UV254, UVT and SDI?
- Which extension policies should apply at mix, split, recycle and application boundaries by default?
- What tolerance model should replace the prototype absolute charge threshold for very large/small industrial streams?
