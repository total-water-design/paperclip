"""Common-duty adapters for Total RO architecture comparison.

This module is orchestration only.  Native calculators remain authoritative;
the adapters copy their results and add stable comparison/envelope structure.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any, Callable

CONTRACT_SCHEMA = "TotalRODesign.ROComparisonResult.v1"
COMPARISON_SCHEMA = "TotalRODesign.ROComparison.v1"
SUPPORTED_ARCHITECTURES = {
    "single_stage_no_erd": "multistage",
    "single_stage_erd": "px",
    "conventional_multistage": "multistage",
    "ccro": "ccro",
}


def _number(mapping: dict[str, Any], *keys: str, default=None):
    for key in keys:
        try:
            value = float(mapping.get(key))
        except (TypeError, ValueError):
            continue
        if isfinite(value):
            return value
    return default


def _recovery_fraction(result: dict[str, Any]) -> float:
    value = _number(result, "recovery", "overall_recovery")
    if value is None:
        feed = _number(result, "feed_flow", "stage1_feed_flow")
        product = _number(result, "product_flow", "permeate_flow")
        value = product / feed if feed and product is not None else 0.0
    return value / 100.0 if abs(value) > 1.5 else value


def _stage_contract(result: dict[str, Any], stage: int) -> dict[str, Any]:
    prefix = f"stage{stage}_"
    return {
        "stage": stage,
        "feed_flow": _number(result, prefix + "feed_flow"),
        "permeate_flow": _number(result, prefix + "permeate_flow", f"product_flow_{stage}"),
        "concentrate_flow": _number(result, f"reject_flow_{stage}", prefix + "concentrate_flow"),
        "pressure_vessels": _number(result, prefix + "pressure_vessels", f"vessels_{stage}"),
        "elements_per_vessel": _number(result, prefix + "elements_per_vessel", f"elements_per_vessel_{stage}"),
        "total_elements": _number(result, prefix + "total_elements", f"total_elements_{stage}"),
        "element_profile": deepcopy(result.get(prefix + "element_profile") or []),
        "tail_element_chemistry": deepcopy(result.get(prefix + "tail_element_chemistry")),
        "maximum_element_flux": _number(result, prefix + "max_element_flux", prefix + "maximum_element_flux"),
        "minimum_element_flux": _number(result, prefix + "min_element_flux", prefix + "minimum_element_flux"),
        "maximum_element_dp": _number(result, prefix + "max_actual_dp_per_element", prefix + "dp_per_element"),
        "minimum_reject_flow_per_vessel": _number(result, prefix + "vessel_reject_flow"),
    }


def _ccro_cycle_source(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return accepted native cycle rows in deterministic cycle order."""
    rows = result.get("ccro_cycle_profile")
    if not isinstance(rows, list):
        return []
    return [deepcopy(row) for row in sorted(
        (row for row in rows if isinstance(row, dict)),
        key=lambda row: (_number(row, "cycle", default=0),),
    )]


def inspect_ccro_hydraulic_envelope(
    result: dict[str, Any], constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect every accepted CCRO cycle instant, including interior cycles.

    Constraint keys are optional and use native units: ``pressure_bar`` and
    ``stage_dp_bar`` are upper limits, ``minimum_ndp_bar`` is a lower limit,
    ``flux_lmh`` and ``polarization_factor`` are upper limits.  Ties resolve in
    this documented order, then by cycle number.
    """
    limits = dict(constraints or {})
    rows = []
    violations = []
    priority = ("pressure", "stage_dp", "minimum_ndp", "flux", "polarization")
    for ordinal, source in enumerate(_ccro_cycle_source(result), 1):
        cycle = int(_number(source, "cycle", default=ordinal))
        values = {
            "pressure": _number(source, "feed_pressure_bar"),
            "stage_dp": _number(source, "stage_dp_bar"),
            "minimum_ndp": _number(source, "minimum_element_ndp_bar"),
            "flux": _number(source, "flux_lmh"),
            "polarization": _number(source, "polarization_factor"),
        }
        checks = []
        if values["pressure"] is not None and limits.get("pressure_bar") is not None:
            checks.append(("pressure", values["pressure"], float(limits["pressure_bar"]), values["pressure"] > float(limits["pressure_bar"])))
        if values["stage_dp"] is not None and limits.get("stage_dp_bar") is not None:
            checks.append(("stage_dp", values["stage_dp"], float(limits["stage_dp_bar"]), values["stage_dp"] > float(limits["stage_dp_bar"])))
        if values["minimum_ndp"] is not None and limits.get("minimum_ndp_bar") is not None:
            checks.append(("minimum_ndp", values["minimum_ndp"], float(limits["minimum_ndp_bar"]), values["minimum_ndp"] < float(limits["minimum_ndp_bar"])))
        if values["flux"] is not None and limits.get("flux_lmh") is not None:
            checks.append(("flux", values["flux"], float(limits["flux_lmh"]), values["flux"] > float(limits["flux_lmh"])))
        if values["polarization"] is not None and limits.get("polarization_factor") is not None:
            checks.append(("polarization", values["polarization"], float(limits["polarization_factor"]), values["polarization"] > float(limits["polarization_factor"])))
        failed = {name: (value, limit) for name, value, limit, bad in checks if bad}
        governing = next((name for name in priority if name in failed), None)
        row = {"ordinal": ordinal, "cycle": cycle, "time_min": sum(_number(x, "duration_min", default=0.0) for x in _ccro_cycle_source(result)[:ordinal]), "values": values, "limits": limits, "governing_constraint": governing}
        rows.append(row)
        if governing:
            value, limit = failed[governing]
            violations.append({"constraint": governing, "critical_value": value, "limit": limit, "cycle": cycle, "time_min": row["time_min"], "recovery": _number(source, "sequence_equivalent_recovery")})
    first = violations[0] if violations else None
    return {"schema": "TotalRODesign.HydraulicEnvelope.v1", "status": "infeasible" if first else "feasible", "rows": rows, "violations": violations, "first_governing_constraint": first, "cycle_source": "native_result.ccro_cycle_profile", "order": "ascending native cycle identity"}


def adapt_hydraulic_envelope(result: dict[str, Any], constraints: dict[str, Any] | None = None) -> dict[str, Any]:
    """Stable alias used by report and comparison consumers."""
    return inspect_ccro_hydraulic_envelope(result, constraints)


def adapt_steady_state_result(architecture: str, result: dict[str, Any], duty: dict[str, Any], *, limiting_constraints: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if architecture not in SUPPORTED_ARCHITECTURES:
        raise ValueError(f"Unsupported steady-state architecture: {architecture}")
    stages = max(1, min(4, int(_number(result, "stage_count", default=1))))
    product = _number(result, "product_flow", "permeate_flow", "composite_permeate_flow")
    feed = _number(result, "feed_flow", "stage1_feed_flow")
    recovered = _number(result, "erd_recovered_power_kw", "recovered_power_kw", "px_recovered_kw", "px_recovered_power", default=0.0) or 0.0
    erd_sec = _number(result, "erd_sec_benefit", "erd_sec_savings")
    if erd_sec is None and product and recovered:
        erd_sec = recovered / product
    ro_sec = _number(result, "ro_sec", "ro_gross_sec", "gross_sec")
    envelope = inspect_ccro_hydraulic_envelope(result, duty.get("hydraulic_constraints")) if architecture == "ccro" else None
    return {"schema": CONTRACT_SCHEMA, "architecture": architecture, "native_mode": SUPPORTED_ARCHITECTURES[architecture], "status": "feasible" if not envelope or envelope["status"] == "feasible" else "infeasible", "common_duty": deepcopy(duty), "performance": {"net_product_flow": product, "feed_flow": feed, "concentrate_flow": _number(result, f"reject_flow_{stages}", "reject_flow_final", "final_concentrate_flow"), "recovery_fraction": _recovery_fraction(result), "product_tds": _number(result, "composite_permeate_tds_ppm", "permeate_tds_ppm")}, "energy": {"ro_net_sec_kwh_m3": ro_sec, "total_sec_kwh_m3": _number(result, "total_sec", "total_plant_sec", "specific_energy"), "erd_recovered_power_kw": recovered, "erd_sec_benefit_kwh_m3": erd_sec or 0.0, "erd_benefit_basis": "native SEC field" if erd_sec is not None else ("recovered hydraulic power / net product flow" if recovered else "no ERD benefit"), "ro_sec_without_erd_kwh_m3": (ro_sec + (erd_sec or 0.0)) if ro_sec is not None else None}, "stages": [_stage_contract(result, stage) for stage in range(1, stages + 1)], "cycle_source": "native_result.ccro_cycle_profile" if architecture == "ccro" else None, "cycle_profiles": _ccro_cycle_source(result) if architecture == "ccro" else [], "approved_graph_series": ["feed_pressure_bar", "feed_osmotic_bar", "minimum_element_ndp_bar", "flux_lmh", "polarization_factor"] if architecture == "ccro" else [], "units": {"pressure": "bar", "flux": "LMH", "tds": "mg/L", "energy": "kWh/m³"}, "hydraulic_envelope": envelope, "limiting_constraints": deepcopy(limiting_constraints or []), "native_result": deepcopy(result)}


def adapt_ccro_result(result: dict[str, Any], duty: dict[str, Any], *, limiting_constraints: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return adapt_steady_state_result("ccro", result, duty, limiting_constraints=limiting_constraints)


def maximize_feasible_recovery(architecture: str, duty: dict[str, Any], design: dict[str, Any], calculators: dict[str, Callable[[dict[str, Any]], dict[str, Any]]], *, iterations: int = 12) -> dict[str, Any]:
    mode = SUPPORTED_ARCHITECTURES.get(architecture)
    if mode is None:
        raise ValueError(f"Unsupported steady-state architecture: {architecture}")
    product = float(duty.get("net_product_flow") or 0.0)
    if not isfinite(product) or product <= 0:
        raise ValueError("common_duty.net_product_flow must be positive.")
    low = float(duty.get("minimum_recovery_fraction", 0.05)); high = float(duty.get("maximum_recovery_fraction", 0.95))
    if not (0 < low < high < 1):
        raise ValueError("Recovery search bounds must satisfy 0 < minimum < maximum < 1.")
    calculator = calculators[mode]; best = None; constraints = []
    for _ in range(max(1, iterations)):
        recovery = (low + high) / 2.0; payload = deepcopy(design)
        payload.update({"solve_basis": "recovery", "target_recovery": 100.0 * recovery, "feed_flow": product / recovery})
        if architecture == "single_stage_no_erd": payload.update({"stage_count": 1, "energy_recovery_mode": "without"})
        elif architecture == "single_stage_erd": payload.update({"stage_count": 1, "energy_recovery_mode": "with"})
        elif architecture == "ccro": payload["ccro_target_average_recovery"] = 100.0 * recovery
        try:
            native = calculator(payload); actual = _number(native, "product_flow", "permeate_flow")
            if actual is None or abs(actual - product) > max(0.01, product * 0.003): raise ValueError(f"net product duty missed: requested {product:g}, calculated {actual}")
            adapted = adapt_ccro_result(native, duty) if architecture == "ccro" else adapt_steady_state_result(architecture, native, duty)
            if adapted["status"] != "feasible": raise ValueError("hydraulic envelope constraint violated")
            best = native; low = recovery
        except (KeyError, ValueError, ZeroDivisionError) as exc:
            constraints = [{"type": "native_solver_limit", "message": str(exc), "trial_recovery_fraction": recovery}]; high = recovery
    if best is None:
        return {"schema": CONTRACT_SCHEMA, "architecture": architecture, "native_mode": mode, "status": "infeasible", "common_duty": deepcopy(duty), "limiting_constraints": constraints}
    if not constraints: constraints = [{"type": "configured_recovery_ceiling", "message": "Configured maximum recovery bound reached.", "trial_recovery_fraction": high}]
    return adapt_ccro_result(best, duty, limiting_constraints=constraints) if architecture == "ccro" else adapt_steady_state_result(architecture, best, duty, limiting_constraints=constraints)


def compare_steady_state(payload: dict[str, Any], calculators: dict[str, Callable]) -> dict[str, Any]:
    duty = payload.get("common_duty") or {}; architectures = payload.get("architectures") or {}
    if not isinstance(architectures, dict) or not architectures: raise ValueError("At least one architecture design is required.")
    ordered = sorted(architectures.items(), key=lambda pair: pair[0])
    return {"schema": COMPARISON_SCHEMA, "common_duty": deepcopy(duty), "results": [maximize_feasible_recovery(name, duty, design or {}, calculators) for name, design in ordered]}
