# Shared WaterStream Contract v0.2

**Status:** breaking architectural prototype / not frozen  
**Schema:** `twds.water-stream`  
**Version:** `0.2.0`  
**Owner branch:** `engine/shared-waterstream`

v0.2 is the direct response to the Total Water Balance v0.1 attack spike. It is intentionally breaking and remains unsuitable for a v1.0 freeze.

## Breaking changes

### H2O is authoritative inventory

`H2O` resolves to canonical component `h2o` and is transported in `component_totals_mol_s`. Aqueous streams must contain positive H2O inventory.

`flow_m3_s` is no longer serialized or independently assignable. For a certified aqueous stream it is derived from certified solution mass and density:

`flow_m3_s = solution_mass_kg_s / density_kg_m3`

The ChemistryCertificate also carries `solvent_water_kg_s`, which is checked against the H2O component and supplies the solvent mass basis required for molality.

`solution_mass_kg_s` is included in the certificate because ordinary solution density cannot be combined with solvent-water mass alone to calculate physical solution volume.

### Charge tolerance is not stream state

`charge_tolerance_eq_s` was removed from WaterStream. It may not be deserialized as a stream field.

Charge acceptance is evaluated by `ChargeValidationPolicy`, using:

`max(abs_tolerance_eq_s, relative_tolerance * charge_throughput_eq_s)`

The policy therefore does not mix, split, recycle or grow with the process stream.

### ChemistryCertificate

`ChemistryCertificate` contains at minimum:

- `state_hash`
- `residual_charge_eq_s`
- `ionic_strength_mol_kg`
- `solvent_water_kg_s`
- `density_kg_m3`
- `engine_version`

and additionally `solution_mass_kg_s` for the physical volume derivation above.

The certificate is valid only when `certificate.state_hash == stream.state_hash`. The state hash covers the chemistry-relevant transported state, not the certificate itself, so a certificate can bind without a circular hash.

Conservative splitting rebinds/scales a still-valid certificate because composition/intensive chemistry is unchanged. Mixing creates a new state with `chemistry_certificate=None` and an explicit diagnostic warning that recertification is required. Access to flow or ionic strength on that mixed stream raises `UncertifiedChemistryError` until Shared Chemistry recertifies it.

For fully charge-explicit fixed-ion states, the contract also performs a coarse structural consistency guard between the certified residual and the directly calculable fixed-ion charge residual. This is deliberately not the numerical acceptance tolerance. It exists to reject gross contradictions such as Na=8 mol/s, Cl=7 mol/s with a certificate claiming residual charge = 0.

## Additive changes

### Phase and mineral identity

`WaterStream.phase` is one of:

- `AQUEOUS`
- `SOLID`
- `GAS`
- `MIXED`

`mineral_identity` is allowed on SOLID or MIXED streams. Mineral names are not components. `calcite` remains invalid in the component registry; a calcite solids stream carries conserved component totals plus `mineral_identity="calcite"`.

### MassLedger TOTH closure

MassLedger now carries:

- `toth_in_eq_s`
- `toth_out_eq_s`
- `toth_delta_eq_s`
- derived `toth_residual_eq_s`

`MassLedger.assert_closed()` checks both component mass and TOTH closure. An unexplained TOTH change fails; an explicitly declared stoichiometric TOTH delta may close it.

### Explicit phase-outlet convention

A ledger entry records whether a component appears in an explicit SOLID or GAS outlet. If so, `transferred_to_solid_kg_s` or `transferred_to_gas_kg_s` respectively must be zero. This prevents phase transfer from being counted both as an explicit outlet and as an internal sink term.

### TrackedQuantity transport axis

Tracked quantities now have two independent behavioral dimensions:

1. mixing rule: `EXTENSIVE_SUM | FLOW_WEIGHTED | NOT_MIXABLE`
2. transport policy: `CONSERVED | OWNER_MUST_TRANSFORM | UNDEFINED_OUTSIDE_MIXER`

A splitter fails closed for `OWNER_MUST_TRANSFORM` unless an owner transformer is supplied. `UNDEFINED_OUTSIDE_MIXER` becomes explicitly unavailable outside the mixer. `NOT_MIXABLE` values such as SDI remain explicitly unavailable after mixing rather than being averaged.

## Not adopted

No tear-vector, numerical scaling vector, or equation-oriented convergence representation was added to Shared WaterStream. Those remain Total Water Balance / flowsheet-solver concerns.

## Regression reproductions from the v0.1 Water Balance spike

v0.2 tests include the exact failure patterns that drove this revision:

1. Na=8 mol/s, Cl=7 mol/s with certified residual charge 0 is rejected.
2. 1.0 m3/s inlet and 0.9 m3/s outlet with identical solutes fails MassLedger closure because H2O inventory no longer disappears outside the ledger.
3. An unexplained 0.25 eq/s TOTH change fails MassLedger closure.
4. Explicit solids output plus nonzero `transferred_to_solid_kg_s` for the same component raises a ledger convention error.
5. `OWNER_MUST_TRANSFORM` tracked state fails closed without its owner transformer.
6. SDI with `NOT_MIXABLE` remains explicitly unavailable after mixing.

## Prototype code organization

The package root (`import shared_waterstream`) now exports the v0.2 contract from `shared_waterstream/v02.py`.

The original v0.1 files remain in the branch unchanged as historical prototype evidence. Direct imports from the old `shared_waterstream.models`, `shared_waterstream.ledger`, or `shared_waterstream.operations` modules should therefore be treated as legacy v0.1 behavior. Cross-application v0.2 prototype consumers should import from the package root.

This temporary overlay is deliberate while v0.2 is being attacked. It should be consolidated before any future stable v1.0 proposal.
