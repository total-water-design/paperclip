"""Scenario-aware pump-duty adapter for Total RO Design economic summaries.

The RO calculation engines expose heterogeneous result fields by technology.
This adapter normalizes those solved fields for CAPEX only. It never changes
engineering calculations and never adds an aggregate electrical duty on top of
components already included in that aggregate.
"""
from __future__ import annotations


def _n(value):
    if value in (None, ""):
        return 0.0
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def _first_positive(result, *keys):
    for key in keys:
        value = _n((result or {}).get(key))
        if value > 0:
            return value
    return 0.0


def _is_ccro(result):
    return any(str(key).startswith("ccro_") for key in (result or {}))


def _bank_units(result):
    """Return reliable selected HPP bank units when propagated by shared pump engine."""
    options = (result or {}).get("pump_database_top_options") or []
    if not isinstance(options, list) or not options:
        return 1
    selected = options[0] if isinstance(options[0], dict) else {}
    units = selected.get("installed_units", selected.get("duty_units", 1))
    try:
        return max(1, int(round(float(units or 1))))
    except (TypeError, ValueError):
        return 1


def _append_bank(duties, kind, total_kw, units=1):
    total_kw = _n(total_kw)
    units = max(1, int(units or 1))
    if total_kw <= 0:
        return
    per_unit_kw = total_kw / units
    for _ in range(units):
        duties.append((kind, per_unit_kw))


def scenario_aware_pump_duties(result, capacity_m3d):
    """Normalize pump duties without double counting aggregate electrical power.

    The returned shape intentionally matches ro_economic_summary_v1._pump_duties:
    ``[(service_name, wire_kw), ...]``. Multiple tuples of one service represent
    multiple physical pumps in a parallel bank, while their kW values sum to the
    solved total bank duty.
    """
    result = result or {}
    duties = []

    if _first_positive(result, "dweer_hpp_electric_kw") > 0:
        _append_bank(duties, "high_pressure_pump", result.get("dweer_hpp_electric_kw"), _bank_units(result))
        _append_bank(duties, "dweer_booster", result.get("dweer_booster_electric_kw"))
        _append_bank(duties, "dweer_lp_increment", result.get("dweer_lp_increment_electric_kw"))
        _append_bank(duties, "interstage_booster", result.get("dweer_inherited_interstage_booster_kw"))
        return duties

    if _first_positive(result, "pelton_motor_electric_kw") > 0:
        _append_bank(duties, "high_pressure_pump", result.get("pelton_motor_electric_kw"), _bank_units(result))
        _append_bank(duties, "interstage_booster", result.get("pelton_inherited_interstage_booster_kw"))
        return duties

    if _is_ccro(result):
        _append_bank(duties, "high_pressure_pump", result.get("hpp_kw"), _bank_units(result))
        _append_bank(duties, "circulation_booster", result.get("circ_kw"))
        if duties:
            return duties

    hpp_kw = _first_positive(result, "hpp_kw", "high_pressure_pump_kw", "feed_pump_electric_kw")
    aggregate_kw = _first_positive(result, "electric_kw")
    booster_kw = _first_positive(result, "interstage_booster_kw", "interstage_pump_kw", "booster_kw")
    circ_kw = _first_positive(result, "circ_kw", "circulation_booster_kw", "circulation_pump_kw", "px_booster_kw")

    if hpp_kw > 0:
        _append_bank(duties, "high_pressure_pump", hpp_kw, _bank_units(result))
        if booster_kw > 0 and circ_kw > 0 and booster_kw + 1e-9 >= circ_kw:
            _append_bank(duties, "interstage_booster", booster_kw - circ_kw)
            _append_bank(duties, "circulation_booster", circ_kw)
        elif booster_kw > 0:
            _append_bank(duties, "interstage_booster", booster_kw)
        elif circ_kw > 0:
            _append_bank(duties, "circulation_booster", circ_kw)
        return duties

    if aggregate_kw > 0:
        _append_bank(duties, "high_pressure_pump", aggregate_kw, _bank_units(result))
        if booster_kw > 0:
            _append_bank(duties, "interstage_booster", booster_kw)
        if circ_kw > 0:
            _append_bank(duties, "circulation_booster", circ_kw)
        return duties

    ro_sec = _first_positive(result, "ro_sec", "ro_gross_sec", "gross_sec")
    fallback_kw = ro_sec * max(0.0, float(capacity_m3d or 0.0)) / 24.0
    _append_bank(duties, "ro_pumping", fallback_kw)
    return duties


def install_ro_economic_pump_adapter(module):
    """Install the adapter into the RO economic producer before route registration."""
    module._pump_duties = scenario_aware_pump_duties
    return module
