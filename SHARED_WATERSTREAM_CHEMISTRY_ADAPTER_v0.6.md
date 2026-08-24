# Shared WaterStream ↔ Shared Water Chemistry Adapter Interface — v0.6

**WaterStream owner:** `engine/shared-waterstream`  
**WaterStream schema:** `twds.water-stream` / `0.6.0`  
**Shared Chemistry reference milestone:** `engine/shared-water-chemistry@6fdbb11e025130162f749a7b77191e108f183d15`  
**Referenced chemistry facade:** `shared_water_chemistry.WaterState`, schema `twds.water-state` version `1`

This document is the normative interface specification for the next Shared Water Chemistry milestone. It defines what WaterStream guarantees and what the chemistry-owned adapter may consume. It does **not** implement equilibrium chemistry.

## 1. Ownership boundary

### Shared WaterStream owns authoritative transport/process state

WaterStream guarantees the following authoritative quantities for a pure aqueous handoff:

| WaterStream quantity | Meaning | Unit / basis | Authority |
|---|---|---|---|
| `component_totals_mol_s` | Canonical analytical/component-family total rates | mol/s | conserved transport state |
| `component_totals_mol_s['h2o']` | Solvent-water molecular rate | mol/s H2O | conserved transport state |
| `solvent_water_kg_s_from_components` | Solvent-water mass rate from H2O and fixed H2O molar mass | kg/s H2O | deterministic conversion from authoritative H2O |
| `aqueous_volume_flow_m3_s` / `flow_m3_s` | Pure-aqueous hydraulic volume flow | m3/s | authoritative process/hydraulic state; available before chemistry |
| `temperature_c` | Stream temperature | °C | authoritative process state |
| `pressure_bar` | Stream pressure | bar | authoritative process state |
| `toth_eq_s` | Total alkalinity/proton-condition rate on the Shared Water Chemistry TA convention; positive is positive acid-neutralizing capacity | eq/s | conserved analytical state |
| `total_inorganic_carbon` component | Total inorganic carbon analytical-family rate | mol C/s | conserved analytical state |
| `chemistry_policy` | Reserved chemistry-boundary policy namespace | canonical JSON object | hash-participating transport policy |
| `phase` / `phase_inventory` | Material phase declaration and identified phase inventory | extensive component basis | authoritative phase bookkeeping |
| `provenance` | Ordered source/application/process records | metadata | authoritative provenance |
| `schema`, `version`, `state_hash` | Contract identity and chemistry-relevant state identity | identifiers | authoritative contract/provenance |

WaterStream stores Python binary64 values and serializes them without UI/display rounding. Canonical JSON is deterministic. State identity includes temperature, pressure, components, TOTH/TA, aqueous flow, phase inventory, and chemistry policy.

### Shared Water Chemistry owns derived aqueous equilibrium state

Shared Chemistry owns, among other derived values:

- pH / hydrogen activity;
- ionic strength;
- activity coefficients;
- carbonate speciation;
- weak-acid/base speciation;
- equilibrium species concentrations;
- saturation indices / mineral equilibrium diagnostics;
- other equilibrium solver outputs.

These values MUST NOT be copied into `WaterStream.component_totals_mol_s` as if they were conserved quantities.

## 2. Supported production handoff domain

The first production adapter is defined for **pure `AQUEOUS` WaterStream v0.6**.

The adapter MUST fail closed for a non-aqueous or `MIXED` WaterStream unless a later chemistry milestone defines an explicit multiphase chemistry handoff.

Production handoff requires WaterStream provenance. `chemistry_handoff_report()` enforces this by default.

## 3. WaterStream → WaterState construction

The chemistry-owned adapter constructs `shared_water_chemistry.WaterState` as follows.

### 3.1 Analytical composition (`WaterState.composition_mg_l`)

For directly compatible non-speciating analytical bases, convert an extensive WaterStream total to mg/L by:

`mg/L = component_mol_s × analytical_molar_mass_g_mol / aqueous_volume_flow_m3_s`

The numerical identity is valid because `g/m3 == mg/L`.

The controlled direct mapping is:

| WaterStream canonical total | WaterState composition key | WaterStream analytical mass basis |
|---|---|---|
| `sodium` | `sodium` | Na |
| `potassium` | `potassium` | K |
| `magnesium` | `magnesium` | Mg |
| `calcium` | `calcium` | Ca |
| `strontium` | `strontium` | Sr |
| `barium` | `barium` | Ba |
| `fluoride` | `fluoride` | F |
| `chloride` | `chloride` | Cl |
| `sulfate` | `sulfate` | SO4 |
| `nitrate` | `nitrate` | NO3 |
| `bromide` | `bromide` | Br |
| `total_boron` | `boron` | elemental B |
| `total_silica` | `silica` | SiO2 |

This mapping is published in `WATERSTATE_DIRECT_COMPOSITION_MAP`.

Do **not** place any of the following into WaterState composition as a replacement for the authoritative carbon/proton basis:

- `total_inorganic_carbon`;
- `bicarbonate`;
- `carbonate`;
- pH or hydrogen activity.

`bicarbonate` and `carbonate` remain derived species and are forbidden as WaterStream authoritative components.

### 3.2 Total alkalinity / proton condition

Set:

`WaterState.total_alkalinity_mol_kg = WaterStream.toth_eq_s / WaterStream.solvent_water_kg_s_from_components`

The WaterStream v0.6 definition of `toth_eq_s` is deliberately narrowed to the same total-alkalinity convention consumed by the validated Shared Chemistry facade.

The adapter MUST NOT infer TA from pH.

### 3.3 Total inorganic carbon

Set:

`WaterState.total_inorganic_carbon_mol_kg = WaterStream.component_totals_mol_s['total_inorganic_carbon'] / WaterStream.solvent_water_kg_s_from_components`

Absent TIC is zero on the WaterStream analytical-total basis. The adapter must preserve zero explicitly where required by the chemistry call.

### 3.4 pH

Set:

`WaterState.ph = None`

WaterStream does not transport authoritative pH. The validated chemistry facade explicitly prefers `TA + CT -> pH` after process changes, which is the intended production basis.

### 3.5 Temperature and pressure

Set directly:

- `WaterState.temperature_c = WaterStream.temperature_c`
- `WaterState.pressure_bar = WaterStream.pressure_bar`

No UI rounding is permitted.

### 3.6 Provenance

Use the latest applicable WaterStream provenance record:

- `WaterState.source_application = WaterStream.latest_provenance.application`
- `WaterState.source_process = WaterStream.latest_provenance.process`

Recommended WaterState metadata:

```text
waterstream_schema     = twds.water-stream
waterstream_version    = 0.6.0
waterstream_state_hash = <WaterStream.state_hash>
```

### 3.7 Equilibrium field

Before chemistry has run:

`WaterState.equilibrium = {}`

The adapter must not manufacture an equilibrium payload from WaterStream transport state.

## 4. Analytical families not yet represented by the current WaterState facade

WaterStream v0.6 preserves the following authoritative analytical families:

- `total_ammonia`;
- `total_phosphate`;
- `total_iron`;
- `total_manganese`.

At chemistry milestone `6fdbb11e...`, the stable WaterState facade does not provide an unambiguous analytical-family representation for these totals. They MUST NOT be silently dropped or converted to one equilibrium species.

Therefore the first production adapter MUST fail closed when any of these totals is nonzero, until the Shared Water Chemistry owner deliberately defines the mapping or extends WaterState. `chemistry_handoff_report()` exposes the nonzero set as `chemistry_owned_analytical_families_present`.

This is a controlled adapter limitation, not a WaterStream data-loss condition.

## 5. Shared Chemistry → WaterStream return path

The intended architecture is:

**WaterStream → chemistry-owned adapter → WaterState → Shared Chemistry → equilibrated WaterState + ChemistryCertificate → consuming application**

### 5.1 Equilibrated WaterState remains chemistry-owned derived state

The consuming application may use the equilibrated WaterState for:

- pH;
- species distribution;
- ionic strength;
- saturation indices;
- activity data;
- chemistry diagnostics.

Those values are not promoted into WaterStream conserved totals merely because chemistry computed them.

### 5.2 ChemistryCertificate attachment

Shared Chemistry may issue a WaterStream v0.6 `ChemistryCertificate` bound to the unchanged WaterStream `state_hash` containing:

- `state_hash`;
- `residual_charge_eq_s`;
- `ionic_strength_mol_kg`;
- `solvent_water_kg_s`;
- `density_kg_m3`;
- `engine_version`;
- `solution_mass_kg_s`;
- optional metadata/provenance.

WaterStream independently checks state-hash binding, solvent-water consistency, and charge residual where recomputable. Ionic strength, density, and solution mass remain trusted chemistry-engine outputs; WaterStream does not re-solve chemistry to verify them.

A certificate is a derived cache/provenance object. It does not mutate conserved stream state.

### 5.3 Process changes after chemistry

If acid/base dosing, degassing, precipitation, reaction, membrane separation, biological reaction, or another UnitOp changes conserved analytical totals, the owning UnitOp must create a **new WaterStream** with explicit new:

- component totals;
- TOTH/TA rate;
- aqueous volume flow where applicable;
- phase inventory/policy/provenance.

Shared Chemistry then re-equilibrates that new state. A ChemistryCertificate alone cannot represent a conserved-state change.

## 6. Mixing guarantee

For supported pure-aqueous mixing, WaterStream v0.6:

- sums H2O inventory;
- sums all authoritative component mol/s totals;
- sums `toth_eq_s` (TA equivalents/s);
- sums authoritative aqueous volume flow;
- flow-weights temperature;
- preserves/validates chemistry policy;
- invalidates the chemistry certificate;
- requires chemistry to re-equilibrate the mixed state.

Mixing therefore provides all authoritative quantities necessary to reconstruct WaterState without first possessing a ChemistryCertificate.

## 7. Splitting guarantee

### Uniform scalar composition-preserving split

WaterStream v0.6 scales by the same fraction:

- H2O;
- all component mol/s totals;
- TOTH/TA equivalents/s;
- aqueous volume flow.

The intensive TA and CT mol/kg-water basis is therefore unchanged. For an aqueous, explicitly composition-preserving scalar split, the existing certificate may be rebound/scaled to the daughter state.

### Selective split

A selective per-component split is not assumed to preserve hydraulic volume or alkalinity.

For a pure-aqueous selective split:

- daughter aqueous flows are required explicitly from the owning UnitOp;
- daughter flows must be positive and conserve the parent volume flow;
- nonzero TOTH/TA refuses generic selective splitting because no universal partition rule exists;
- ChemistryCertificate is invalidated;
- shared components present in multiple phase-inventory items remain owner-physics transforms.

WaterStream does not infer daughter volume from H2O fraction and does not infer daughter TA from water/TIC/component fraction.

## 8. Precision and serialization guarantees

WaterStream v0.6 guarantees:

- no UI/display rounding in transport serialization;
- deterministic canonical JSON;
- deterministic `state_hash` for identical chemistry-relevant state;
- full Python binary64 values survive canonical JSON round-trip under the supported serializer;
- component, H2O, TA/TOTH, TIC, temperature, pressure, and aqueous-flow values are not intentionally rounded;
- derived conversions to mg/L or mol/kg-water use normal IEEE-754 arithmetic and are validated at machine precision rather than decimal-string exactness.

## 9. Compatibility/version behavior

`twds.water-stream` v0.6 is a deliberate breaking revision from v0.5 because:

1. pure-aqueous hydraulic flow is now an authoritative required field;
2. `toth_eq_s` is now explicitly the Shared Chemistry total-alkalinity convention.

`WaterStream.from_dict()` accepts v0.6 only. Legacy v0.5 payloads use `migrate_v05_payload()`; see `SHARED_WATERSTREAM_v0.6_MIGRATION.md`.

No v0.5 ChemistryCertificate survives migration because the schema/state identity changed.

## 10. Adapter conformance requirements for Shared Water Chemistry

A production chemistry adapter built against WaterStream v0.6 should test at minimum:

1. WaterStream `state_hash` copied into WaterState metadata/provenance;
2. direct composition mg/L mapping on the published bases;
3. TA = TOTH eq/s ÷ solvent-water kg/s;
4. CT = TIC mol/s ÷ solvent-water kg/s;
5. pH is `None` before equilibration;
6. exact chemistry facade accepts TA+CT and solves pH;
7. WaterState handoff round-trip does not round values;
8. nonzero unmapped analytical families fail closed;
9. equilibrated derived species are not written into WaterStream authoritative totals;
10. returned certificate is bound to the original WaterStream state hash and carries nonblank engine provenance.

## 11. Normative statement for the Shared Water Chemistry owner

> **These are the authoritative quantities WaterStream v0.6 guarantees:** canonical analytical/component-family totals in mol/s; solvent H2O in mol/s (and deterministically kg/s); pure-aqueous hydraulic flow in m3/s; temperature in °C; pressure in bar; total alkalinity/proton condition as `toth_eq_s` in equivalents/s on the Shared Water Chemistry TA convention; total inorganic carbon as conserved mol C/s; chemistry policy; phase inventory; provenance; schema/version/state identity. These values survive supported serialization, mixing, and splitting without intentional rounding and with conservation/fail-closed rules defined above. Shared Water Chemistry may use those quantities to reconstruct/re-equilibrate aqueous chemistry. pH, speciation, ionic strength, activity, saturation state, and other equilibrium results remain chemistry-owned derived state and must not be converted into false WaterStream conserved quantities.**

## 12. Explicitly excluded from this milestone

- implementation of the production adapter inside WaterStream;
- modification of Shared Water Chemistry equations or `WaterState`;
- non-aqueous/multiphase chemistry equilibrium handoff;
- analytical-family mapping for total ammonia/phosphate/iron/manganese until the chemistry owner defines it;
- RO, Bio, Pretreatment, ZLD, or other application-specific calculations;
- tear-vector/recycle-solver policy.
