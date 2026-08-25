# Total Water Balance — Validation & Reconciliation Audit Gate

Branch: `app/total-water-balance`

## Gate definition

Total Water Balance is developed as an **integration-late application**. A milestone is considered validated only when `Total Water Balance Validation CI` completes successfully against the exact branch-tip SHA being reported and the exact Shared WaterStream dependency pin below.

For push-triggered runs, the workflow also publishes:

```text
total-water-balance/shared-waterstream-v06
```

## Dependency pins

```text
engine/shared-waterstream @ e43bd4e1f86f657528e83dc9e185970443d30f4b
twds.water-stream schema  @ 0.6.0
engine/shared-water-chemistry reference @ 6fdbb11e025130162f749a7b77191e108f183d15
twds.water-state schema   @ 1
```

The Water Balance branch does not merge, vendor, copy or redefine those shared engines.

## Current application-engine scope

The active milestone contains:

- `total_water_balance/model.py` — serializable facility model, topology roles and owner-declared balance terms;
- `total_water_balance/graph.py` — graph validation, lineage, cycle/recycle detection and topological ordering;
- `total_water_balance/balance.py` — UnitOp/facility component, H2O and TOTH closure plus recovery/disposition diagnostics;
- `total_water_balance/recycle.py` — fail-closed pure-aqueous fixed-point recycle orchestration;
- `total_water_balance/adapters.py` — late specialist-app boundary protocol and static migration adapter;
- `total_water_balance/presentation.py` — UI-neutral dashboard, stream table and H2O Sankey payloads;
- `tests/test_total_water_balance_engine.py` — application-engine regression coverage;
- existing Shared WaterStream consumer-contract coverage.

## Ownership boundary

- Shared WaterStream owns stream transport state and generic conservative primitives.
- Shared Chemistry owns equilibrium/speciation.
- Specialist applications own unit-operation transformations.
- Total Water Balance owns facility/process-train topology, balance closure, recycle accounting and facility diagnostics.
- System Integration & Optimization owns complete train orchestration and optimization.

## Integration-late limitation

A green engine gate does **not** authorize production deployment. The following remain deliberately deferred until late Suite integration:

- Suite Core app registration/navigation;
- Project Library persistence implementation;
- final flowsheet editor and visual UI;
- report-provider wiring;
- direct specialist-app adapters;
- automated whole-Suite assembly;
- production deployment.

This prevents Total Water Balance from forcing premature changes into Core or advanced specialist applications.

## Reconciliation order

When this branch is reconciled later:

1. reconcile validated Suite Core/shared platform prerequisites;
2. reconcile Shared WaterStream at or beyond the validated pin and recheck compatibility if the SHA changes;
3. reconcile required Shared Chemistry adapter/facade prerequisites;
4. reconcile the validated Total Water Balance milestone;
5. add specialist adapters only through their owner branches when final integration begins.

Do not merge Total Water Balance as a substitute for its shared dependencies, and do not deploy it from a reconciliation-only task.
