"""Backward-compatible Suite pump facade.

The established VCMP API remains the default so existing Total RO Design cases
continue to select exactly the same pump family and preserve their numerical
behaviour.  The validated shared pump engine (VCMP + HHECP + PD) is exposed
through opt-in technology selection and explicit shared-engine helpers.
"""
from __future__ import annotations

from vcmp_pump import (
    DB_PATH,
    G,
    DEFAULT_REFERENCE_RPM_60,
    META,
    PUMPS,
    BY_SOURCE_ID,
    list_pumps,
    _poly4,
    head_m,
    raw_efficiency,
    adjusted_efficiency,
    _head_to_bar,
    _bar_to_head,
    _solve_speed_ratio,
    evaluate_pump,
    select_pump as _select_vcmp_impl,
    curve_points as _curve_points_vcmp_impl,
)
from hhecp_pump import (
    MODELS as HHECP_MODELS,
    BY_CODE as HHECP_BY_CODE,
    evaluate as evaluate_hhecp,
    select as select_hhecp,
)
from pd_pump import (
    PUMPS as PD_PUMPS,
    BY_MODEL as PD_BY_MODEL,
    evaluate as evaluate_pd,
    select as select_pd,
)
from shared_pump_engine import (
    select_pump as _select_shared_impl,
    curve_points as _curve_points_shared_impl,
    list_shared_pumps,
)


def _tag_vcmp_result(result):
    """Add shared-engine identity fields without changing legacy VCMP values."""
    if not isinstance(result, dict):
        return result
    options = result.get("options") or []
    for op in options:
        if not isinstance(op, dict):
            continue
        op.setdefault("technology", "VCMP")
        op.setdefault("model", f"{op.get('product_family', 'VCMP')} {op.get('stage_config', '')}".strip())
        op.setdefault("duty_units", 1)
        op.setdefault("installed_units", 1)
        if op.get("wire_kw") is not None:
            op.setdefault("wire_kw_per_pump", op.get("wire_kw"))
    selected = result.get("selected")
    if isinstance(selected, dict):
        selected.setdefault("technology", "VCMP")
        selected.setdefault("model", f"{selected.get('product_family', 'VCMP')} {selected.get('stage_config', '')}".strip())
        selected.setdefault("duty_units", 1)
        selected.setdefault("installed_units", 1)
        if selected.get("wire_kw") is not None:
            selected.setdefault("wire_kw_per_pump", selected.get("wire_kw"))
    return result


def select_vcmp(flow_m3h, required_dp_bar, density_kg_m3=998.0,
                motor_eff=0.95, vfd_eff=0.98,
                min_vfd_hz=40.0, max_vfd_hz=60.0,
                flow_margin=0.05, head_margin=0.05,
                reduced_impeller_penalty_pp=2.0,
                low_speed_derate_pp_per_10pct=0.0,
                reference_rpm_60=None, top_n=5):
    return _tag_vcmp_result(_select_vcmp_impl(
        flow_m3h, required_dp_bar, density_kg_m3,
        motor_eff, vfd_eff, min_vfd_hz, max_vfd_hz,
        flow_margin, head_margin, reduced_impeller_penalty_pp,
        low_speed_derate_pp_per_10pct, reference_rpm_60, top_n,
    ))


def select_shared_pump(flow_m3h, required_dp_bar, density_kg_m3=998.0,
                       motor_eff=0.95, vfd_eff=0.98,
                       min_vfd_hz=30.0, max_vfd_hz=60.0,
                       flow_margin=0.05, head_margin=0.05,
                       reduced_impeller_penalty_pp=2.0,
                       low_speed_derate_pp_per_10pct=0.0,
                       reference_rpm_60=None, top_n=5,
                       max_duty_units=10, available_inlet_bar=0.0,
                       technologies=None):
    return _select_shared_impl(
        flow_m3h, required_dp_bar, density_kg_m3,
        motor_eff, vfd_eff, min_vfd_hz, max_vfd_hz,
        flow_margin, head_margin, reduced_impeller_penalty_pp,
        low_speed_derate_pp_per_10pct, reference_rpm_60, top_n,
        max_duty_units, available_inlet_bar, technologies,
    )


def select_pump(flow_m3h, required_dp_bar, density_kg_m3=998.0,
                motor_eff=0.95, vfd_eff=0.98,
                min_vfd_hz=40.0, max_vfd_hz=60.0,
                flow_margin=0.05, head_margin=0.05,
                reduced_impeller_penalty_pp=2.0,
                low_speed_derate_pp_per_10pct=0.0,
                reference_rpm_60=None, top_n=5,
                max_duty_units=10, available_inlet_bar=0.0,
                technologies=None):
    """Select a pump while preserving the historical VCMP default.

    Existing callers that do not specify ``technologies`` use the validated
    legacy VCMP selection path.  New Suite callers can request one or more of
    ``vcmp``, ``hhecp`` and ``pd`` to invoke the shared selector deliberately.
    """
    if technologies is None:
        return select_vcmp(
            flow_m3h, required_dp_bar, density_kg_m3,
            motor_eff, vfd_eff, min_vfd_hz, max_vfd_hz,
            flow_margin, head_margin, reduced_impeller_penalty_pp,
            low_speed_derate_pp_per_10pct, reference_rpm_60, top_n,
        )
    return select_shared_pump(
        flow_m3h, required_dp_bar, density_kg_m3,
        motor_eff, vfd_eff, min_vfd_hz, max_vfd_hz,
        flow_margin, head_margin, reduced_impeller_penalty_pp,
        low_speed_derate_pp_per_10pct, reference_rpm_60, top_n,
        max_duty_units, available_inlet_bar, technologies,
    )


def curve_points(source_id, speed_ratio, density_kg_m3=998.0,
                 motor_eff=0.95, vfd_eff=0.98,
                 reduced_impeller_penalty_pp=2.0,
                 low_speed_derate_pp_per_10pct=0.0,
                 reference_rpm_60=None, samples=25):
    """Return the existing VCMP curve API or dispatch a shared pump model."""
    try:
        if isinstance(source_id, int) or str(source_id).isdigit():
            return _curve_points_vcmp_impl(
                int(source_id), speed_ratio, density_kg_m3, motor_eff, vfd_eff,
                reduced_impeller_penalty_pp, low_speed_derate_pp_per_10pct,
                reference_rpm_60, samples,
            )
    except (TypeError, ValueError, KeyError):
        pass
    return _curve_points_shared_impl(
        source_id, speed_ratio, density_kg_m3, motor_eff, vfd_eff,
        reduced_impeller_penalty_pp, low_speed_derate_pp_per_10pct,
        reference_rpm_60, samples,
    )
