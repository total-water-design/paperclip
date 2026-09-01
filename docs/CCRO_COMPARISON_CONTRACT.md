# CCRO common-comparison and whole-cycle envelope contract

This is the CCRO-owned implementation handoff for `TotalRODesign.ROComparisonResult.v1`.

## Decisions

- Canonical per-cycle source: `native_result.ccro_cycle_profile`, emitted by
  `addons/ccro/engine.py`. `ro_comparison._ccro_cycle_source()` copies and
  deterministically orders those accepted native rows; it does not reconstruct
  or reinterpret solver states. `ccro_cycle_graph_profiles` remains the
  element-position graph source only.
- Cycle identity and order: native integer `cycle`, ascending; ties retain
  source order through the stable sort. Envelope `ordinal` is the deterministic
  1-based inspection step and `time_min` is the cumulative native
  `duration_min` through that cycle. Every cycle row is inspected, including
  interior rows.
- Approved graph series: `feed_pressure_bar`, `feed_osmotic_bar`,
  `minimum_element_ndp_bar`, `flux_lmh`, and `polarization_factor`. No new
  equation, smoothing, interpolation, or solver result is introduced.
- Canonical units: pressure `bar`, flux `LMH`, dissolved solids `mg/L`, and
  energy `kWh/m³`. The native result remains available verbatim under
  `native_result`.
- One persisted selected-cycle property: the existing UI case property
  `ccroSelectedGraphCycle`. The report snapshot carries its immutable copy as
  `report_selection.ccro_cycle` and the matching `selected_graph_profile`.
- Deterministic default: select the final available graph profile when the
  persisted property is absent or does not match an available cycle.
- Missing/legacy/incomplete fallback: `static/addons/ccro/ccro_addon.js` first
  uses complete `ccro_cycle_graph_profiles`; for legacy results it exposes one
  final-cycle profile from `stage1_element_profile` and marks the view as
  legacy. With no usable element profile, graph selection is unavailable and
  report readiness must not claim a selected-cycle graph is present.
- Live-view/report/PDF parity: the live selector reads stored native result
  profiles without recalculation. `buildEngineeringReportSnapshot()` deep-copies
  the same result, selected profile, selection property, units, and optional
  envelope; `ccro_report.js` renders that snapshot for both the standalone
  report and browser Print/Save PDF. The standalone renderer therefore uses the
  same cycle identity, graph series, values, and units as the live view.

## Hydraulic envelope

`inspect_ccro_hydraulic_envelope()` evaluates each accepted native cycle instant
against supplied native-unit limits. It returns the complete rows, all
violations, and the first governing constraint with constraint name, critical
value, limit, cycle, cumulative time, and native sequence-equivalent recovery.
Tie-breaking is deterministic: pressure, stage pressure drop, minimum NDP,
flux, then polarization. An interior violation makes the envelope infeasible
even when the first and last cycles pass.

## Scope guard

The adapter does not alter CCRO equations, membrane/CP calculations, solver
behavior, tolerances, constraints, golden values, or native result semantics.
