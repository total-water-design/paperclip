# Total Water Balance — Development Status

Branch: `app/total-water-balance`

Strategy: **integration-late, engine-first**.

Total Water Balance is expected to be one of the last TWDS applications connected to the production Suite. Its core engineering logic is therefore being developed now as an isolated package with no required Suite Core or specialist-app changes. Production registration, persistence, report-provider wiring, navigation and final UI are intentionally deferred.

## Implemented application core

The package `total_water_balance` now provides:

- immutable/serializable facility model using canonical Shared WaterStream v0.6 objects;
- process nodes and typed stream edges;
- external-feed/product/waste/reuse and internal/recycle topology roles;
- graph validation, lineage tracing and strongly-connected-component recycle detection;
- facility-level authoritative component closure on mol/s extensive state;
- H2O closure and residual reporting;
- TOTH/total-alkalinity equivalent closure;
- owner-declared generation, consumption, chemical-dose and accumulation terms;
- UnitOp-level closure reports and facility-wide closure reports;
- diagnostics that identify the largest UnitOp residual associated with a failed facility component;
- plant feed, product, waste, reuse and overall recovery accounting;
- external H2O disposition for a future “Where did the water go?” view;
- fail-closed generic fixed-point recycle convergence for pure-aqueous tear streams;
- explicit refusal of generic recycle convergence when tracked quantities/extensions or non-aqueous physics require owner logic;
- specialist-app result/adapter protocol that does not require specialist adoption yet;
- stream-table, dashboard and H2O-basis Sankey payloads for the future UI;
- deterministic model serialization and model hashing.

## Intentionally deferred

The following are not required for this milestone and should remain deferred until the Suite is closer to final integration:

- Suite Core registration/navigation;
- Project Library persistence implementation;
- report-provider integration and final PDF reports;
- final visual flowsheet editor;
- drag/drop unit-operation authoring;
- final Sankey/animated flowsheet rendering;
- direct adapters inside RO, Bio, Pretreatment, Post-Treatment or ZLD owner branches;
- automated whole-Suite flowsheet assembly;
- system-level optimization (owned by Total Water Design System Integration & Optimization);
- production deployment.

## Late integration contract

Specialist applications will eventually provide a small boundary result containing:

- input WaterStreams;
- output WaterStreams;
- owner-declared generation/consumption/dose/accumulation terms;
- warnings;
- provenance/metadata.

They do not need to replace their internal calculations or adopt Total Water Balance runtime code.

## Safety boundary

Total Water Balance does not:

- own or redefine the canonical WaterStream schema;
- solve aqueous chemistry;
- average pH;
- infer selective phase partitioning;
- invent missing component mass;
- perform membrane, biological, pretreatment, post-treatment or ZLD physics;
- hide non-converged recycle loops behind plausible numbers.

Unsupported transformations remain fail-closed.
