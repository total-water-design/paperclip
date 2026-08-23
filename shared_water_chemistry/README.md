# Shared Water Chemistry Engine

Branch owner: `engine/shared-water-chemistry`

This package defines the canonical water-chemistry handoff used by Total Water
Design Suite applications. It does **not** duplicate the existing chemistry
equations. The current validated implementations remain in:

- `water_chemistry.py` — analytical composition, charge balance, ionic strength,
  osmotic state, membrane composition helpers.
- `chemistry_analysis.py` — equilibrium constants, activity models, scaling and
  saturation analysis.
- `advanced_chemistry.py` — coupled weak-species chemistry, charge-balanced
  downstream states, and high-precision pH solves.

`shared_water_chemistry` is the stable facade applications should integrate
against as they are migrated.

## Ownership rule

Common aqueous chemistry belongs here:

- canonical analytical ion/component definitions;
- pH / H+ activity;
- alkalinity and inorganic-carbon bookkeeping;
- carbonate and common weak-acid/base equilibrium;
- charge balance and ionic strength;
- activity-coefficient infrastructure;
- common saturation/speciation calculations;
- exact cross-application handoff schema.

Application-specific process models stay with the application. Examples include
membrane rejection/polarization in Total RO Design, biological kinetics in Total
Bio Design, and crystallizer/evaporator process logic in Total ZLD Design.

## Handoff rule

Apps exchange a `WaterState`; they do not exchange a rounded display pH as the
sole chemistry definition.

The canonical payload carries:

- analytical composition in the Suite's established mg/L basis;
- temperature and pressure;
- full-precision pH when available;
- total alkalinity (mol/kg-water);
- total inorganic carbon (mol/kg-water);
- provenance and optional equilibrium diagnostics.

When composition, temperature, TA, or CT changes in a downstream unit process,
the receiving application must recompute equilibrium. If TA and CT are both
available, `equilibrate()` deliberately solves pH from those conserved totals.

UI and reports may round pH for presentation. Handoffs must not.

## Migration order

1. Establish this contract and tests.
2. Migrate Total RO Design to consume/emit `WaterState`.
3. Migrate Total Pretreatment Design.
4. Migrate Total Bio Design.
5. Migrate Total ZLD Design.
6. Migrate Total Water Design flowsheet orchestration.
7. After all consumers use the facade, consider moving legacy root chemistry
   implementation modules into this package in a separate, fully tested refactor.

Do not perform step 7 during an application feature merge.
