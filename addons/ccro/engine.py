"""Closed Circuit Reverse Osmosis (CCRO) add-on engine for Total RO Design.

This module is intentionally isolated from calculations.py. It reuses the existing
Total RO Design membrane/chemistry primitives without changing conventional RO or
ERD calculations.
"""
from __future__ import annotations

import math

from chemistry_analysis import analyze_water
from membrane_db import get_membrane
from water_chemistry import (
    composition_from_request, total_tds_mg_l, normalize_composition,
    mix_compositions,
)
from chemistry_analysis import mix_carbonate_streams
from compute_engine import raise_if_cancelled, set_compute_progress
from calculations import (
    _attach_acid_dosing, _attach_membrane, _bool, _float,
    _membrane_pressure_limit_bar, _normalize_membrane_recipe,
    _prepare_calculation_data, _pump_wire_power_kw, _stage_from_data, _vfd_eff,
    display, flow_to_m3h, pressure_to_bar,
)

# ---- Closed Circuit Reverse Osmosis (CCRO) ---------------------------------------
#
# Engineering basis:
# * single membrane stage with 100% concentrate recirculation during CC mode;
# * fresh high-pressure feed equals permeate production during CC mode so the
#   closed-loop liquid inventory is constant;
# * a low-recovery plug-flow (PF) step displaces one system volume to drain;
# * every CC recirculation is re-projected with the existing element-by-element
#   membrane engine and pressure is solved to hold the requested CC permeate flow;
# * the next-cycle feed chemistry is the flow-weighted mixture of the preceding
#   membrane concentrate and fresh make-up feed.  This mirrors the published
#   iterative standard-projection method while retaining Total RO Design's own
#   membrane transport, osmotic and full-ion chemistry implementation.
#
# The model is intentionally vendor-neutral. No universal CCRO pressure or
# recovery range is imposed; feasibility comes from the selected membrane/system
# pressure envelope plus osmotic, hydraulic, flux/polarization and chemistry limits.


def _ccro_fraction(value, default, *, percent_ok=True):
    """Return a bounded fraction from either fraction or percent-style input."""
    if value in (None, ""):
        value = default
    x = float(value)
    if percent_ok and x > 1.0:
        x /= 100.0
    return x


def _ccro_stage_state(stage, stream):
    """Reconstruct the minimum carbonate-state payload required for mixing."""
    prefix = str(stream)
    try:
        return {
            "total_alkalinity_mol_kg": float(stage[f"{prefix}_total_alkalinity_mol_kg"]),
            "total_inorganic_carbon_mol_kg": float(stage[f"{prefix}_total_inorganic_carbon_mol_kg"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _ccro_membrane_pressure_limit_bar(data):
    mid = data.get("membrane_1")
    n = int(round(float(data.get("elements_per_vessel_1", 0) or 0)))
    if not mid or n <= 0:
        raise ValueError("Select the CCRO membrane and membranes per pressure vessel.")
    recipe = _normalize_membrane_recipe(mid, n, data.get("membrane_recipe_1"))
    temp = float(data.get("temperature_c", 25.0) or 25.0)
    return min(_membrane_pressure_limit_bar(get_membrane(x), temp) for x in recipe)


def _ccro_pressure_limit_bar(data):
    """Return the active CCRO pressure envelope.

    The membrane datasheet limit is always enforced.  When the engineer supplies
    an equipment/system pressure rating, the lower of the membrane and equipment
    limits controls.  No CCRO-specific fixed pressure ceiling is imposed.
    """
    membrane_limit = _ccro_membrane_pressure_limit_bar(data)
    raw = data.get("ccro_system_pressure_limit")
    if raw in (None, ""):
        return membrane_limit
    equipment_limit = pressure_to_bar(float(raw), data.get("pressure_unit", "bar"))
    if equipment_limit <= 0:
        raise ValueError("CCRO system/equipment pressure limit must be greater than zero when entered.")
    return min(membrane_limit, equipment_limit)


def _ccro_solve_stage_pressure(data, q_feed_m3h, q_perm_target_m3h, feed_tds_ppm,
                               feed_composition=None, feed_carbonate_state=None,
                               previous_pressure_bar=None):
    """Solve one CCRO membrane projection at constant permeate production.

    Trial evaluations use the same fast-carbonate path already used by the
    conventional inverse-pressure solver.  The converged pressure is then
    recalculated with complete element-by-element carbonate/species reporting.
    """
    qf = float(q_feed_m3h)
    qt = float(q_perm_target_m3h)
    if not (qf > 0 and qt > 0 and qt < qf):
        raise ValueError("CCRO membrane feed and permeate flows must satisfy 0 < permeate < membrane feed.")

    pu = data.get("pressure_unit", "bar")
    pp_raw = _float(data, "permeate_pressure_1", None)
    if pp_raw is None:
        pp_raw = _float(data, "permeate_pressure", 0.0)
    pp_bar = pressure_to_bar(float(pp_raw or 0.0), pu)
    pmax = _ccro_pressure_limit_bar(data)
    if pmax <= pp_bar + 0.05:
        raise ValueError("The selected membrane pressure limit is not above the permeate backpressure.")

    fast = dict(data)
    fast["_solver_fast"] = True

    evaluations = 0

    def evaluate(p_bar, detailed=False):
        nonlocal evaluations
        evaluations += 1
        src = data if detailed else fast
        try:
            return _stage_from_data(src, 1, qf, float(p_bar), float(feed_tds_ppm),
                                    feed_composition=feed_composition,
                                    feed_carbonate_state=feed_carbonate_state)
        except ValueError as exc:
            # At high salinity, low-pressure trial points can be outside the
            # membrane fixed-point's physical convergence envelope.  Such a
            # trial is not a CCRO integration failure; it is an invalid point
            # for pressure bracketing.  Preserve all other validation and
            # physical-limit errors for the caller.
            if "did not converge" in str(exc).lower():
                return None
            raise

    # A previous CC-cycle pressure is an excellent lower seed because loop
    # salinity normally rises monotonically.  Keep a small downward allowance
    # for non-ideal ion/selectivity effects and unusual user inputs.
    if previous_pressure_bar is None:
        lo = max(pp_bar + 0.01, 0.01)
    else:
        lo = max(pp_bar + 0.01, float(previous_pressure_bar) - 1.5)
    hi = min(pmax * 0.999, max(lo + 3.0, (float(previous_pressure_bar) + 5.0) if previous_pressure_bar is not None else lo + 12.0))

    slo = evaluate(lo, False)
    while slo is None and lo < pmax * 0.998:
        lo = min(pmax * 0.999, max(lo + 5.0, lo * 1.10))
        slo = evaluate(lo, False)
    if slo is None:
        raise ValueError(
            "CCRO could not find a convergent membrane pressure trial within the selected pressure limit. "
            "Increase membrane area / pressure vessels, reduce CC permeate flow, or select a membrane train with an appropriate pressure rating."
        )
    flo = float(slo["permeate_flow"]) - qt
    if flo >= 0:
        # Very low-flux setpoint.  A membrane cannot be operated below the
        # permeate-side pressure with this model, so the lower bound is the
        # physical solution to the requested precision.
        final = evaluate(lo, True)
        return lo, final, evaluations

    shi = evaluate(hi, False)
    while shi is None and hi < pmax * 0.998:
        hi = min(pmax * 0.999, max(hi + 5.0, hi * 1.10))
        shi = evaluate(hi, False)
    if shi is None:
        raise ValueError(
            "CCRO could not find a convergent upper membrane pressure trial within the selected pressure limit. "
            "Increase membrane area / pressure vessels, reduce CC permeate flow, or select a membrane train with an appropriate pressure rating."
        )
    fhi = float(shi["permeate_flow"]) - qt
    while fhi < 0 and hi < pmax * 0.998:
        hi = min(pmax * 0.999, max(hi + 5.0, hi * 1.10))
        shi = evaluate(hi, False)
        fhi = float(shi["permeate_flow"]) - qt

    if fhi < 0:
        qmax = float(shi.get("permeate_flow", 0.0))
        raise ValueError(
            f"CCRO permeate setpoint {qt:.3f} m³/h is outside the solvable range for the selected membrane area. "
            f"At the selected membrane pressure limit ({pmax:.2f} bar), projected permeate is {qmax:.3f} m³/h. "
            "The requested point is therefore osmotic-pressure / membrane-pressure-envelope limited. "
            "Increase membrane area / pressure vessels, reduce CC permeate flow, reduce target recovery, or select a membrane/equipment train with an appropriate pressure rating."
        )

    # Safeguarded bisection is preferred here over a derivative method because
    # each pressure evaluation contains element-level concentration-polarization
    # and salt-transport iterations.  Monotonicity is strong, while derivatives
    # can be noisy near high-recovery hydraulic limits.
    p = hi
    target_tol = max(1e-4, 2e-5 * qt)
    for _ in range(36):
        p = 0.5 * (lo + hi)
        sm = evaluate(p, False)
        if sm is None:
            # The convergence envelope can begin above the nominal lower
            # pressure bound. Treat this as a one-sided invalid trial and keep
            # the convergent upper bracket intact.
            lo = p
            continue
        fm = float(sm["permeate_flow"]) - qt
        if abs(fm) <= target_tol or (hi - lo) <= 2e-5 * max(1.0, p):
            break
        if fm >= 0:
            hi = p
        else:
            lo = p

    final = evaluate(p, True)
    # Full carbonate reporting can move flow by a tiny amount relative to the
    # fast inverse trials. One correction based on a local fast slope keeps the
    # reported duty tightly aligned with the requested constant permeate flow.
    ferr = float(final["permeate_flow"]) - qt
    if abs(ferr) > max(0.002 * qt, 5e-4):
        dp = min(0.25, max(0.03, 0.003 * max(p, 1.0)))
        p2 = min(pmax * 0.999, p + dp)
        if p2 > p + 1e-9:
            s2 = evaluate(p2, False)
            slope = (float(s2["permeate_flow"]) - float(final["permeate_flow"])) / (p2 - p)
            if slope > 1e-8:
                pc = max(pp_bar + 0.01, min(pmax * 0.999, p - ferr / slope))
                final2 = evaluate(pc, True)
                if abs(float(final2["permeate_flow"]) - qt) < abs(ferr):
                    p, final = pc, final2
    return float(p), final, evaluations


def _ccro_mix_states(data, concentrate_stage, fresh_comp, fresh_state, q_concentrate, q_fresh):
    """Build the next closed-circuit membrane-feed state."""
    water_mode = str(data.get("water_mode", "tds")).lower()
    if water_mode == "full":
        conc_comp = concentrate_stage.get("concentrate_composition_mg_l")
        conc_state = _ccro_stage_state(concentrate_stage, "concentrate")
        if conc_comp and conc_state and fresh_comp and fresh_state:
            mixed = mix_carbonate_streams([
                {"flow": float(q_concentrate), "composition": conc_comp, "state": conc_state},
                {"flow": float(q_fresh), "composition": fresh_comp, "state": fresh_state},
            ], float(data.get("temperature_c", 25.0) or 25.0))
            return total_tds_mg_l(mixed["composition"]), normalize_composition(mixed["composition"]), mixed
        mixed_comp = mix_compositions(conc_comp or fresh_comp, q_concentrate, fresh_comp, q_fresh)
        return total_tds_mg_l(mixed_comp), mixed_comp, fresh_state
    cconc = float(concentrate_stage.get("concentrate_tds_ppm", 0.0) or 0.0)
    cfresh = float(data.get("feed_tds", data.get("analysis_tds", 0.0)) or 0.0)
    qtot = max(1e-12, float(q_concentrate) + float(q_fresh))
    return (cconc * float(q_concentrate) + cfresh * float(q_fresh)) / qtot, None, None


def _ccro_interpolate_loop_state(data, old_tds, old_comp, old_state, new_tds, new_comp, new_state, fraction):
    f = max(0.0, min(1.0, float(fraction)))
    if f >= 1.0 - 1e-12:
        return new_tds, new_comp, new_state
    if f <= 1e-12:
        return old_tds, old_comp, old_state
    if str(data.get("water_mode", "tds")).lower() == "full" and old_comp and new_comp:
        if old_state and new_state:
            try:
                mixed = mix_carbonate_streams([
                    {"flow": 1.0 - f, "composition": old_comp, "state": old_state},
                    {"flow": f, "composition": new_comp, "state": new_state},
                ], float(data.get("temperature_c", 25.0) or 25.0))
                return total_tds_mg_l(mixed["composition"]), normalize_composition(mixed["composition"]), mixed
            except (KeyError, ValueError, ZeroDivisionError):
                pass
        comp = mix_compositions(old_comp, 1.0 - f, new_comp, f)
        return total_tds_mg_l(comp), comp, old_state
    return old_tds + f * (new_tds - old_tds), None, None


def _ccro_scaling_snapshot(stage, temperature_c):
    """Return thermodynamic mineral-saturation screening for a CCRO stage.

    This is intentionally a solubility screen, not an antiscalant performance
    guarantee.  A concentration-saturation value >=100% means the calculated
    bulk concentrate is thermodynamically supersaturated for that mineral.
    Allowable operation above saturation depends on pretreatment, antiscalant,
    residence time, nucleation kinetics and provider-specific operating limits.
    """
    comp = stage.get("concentrate_composition_mg_l")
    if not comp:
        return None
    ph = stage.get("concentrate_ph", stage.get("feed_ph", 7.0))
    try:
        chem = analyze_water(
            comp,
            float(temperature_c),
            float(ph if ph is not None else 7.0),
            reported_tds=float(stage.get("concentrate_tds_ppm", 0.0) or 0.0),
        )
    except Exception as exc:
        return {"error": str(exc), "minerals": []}
    minerals = list(chem.get("minerals") or [])
    # Use the practical RO scaling phases for the recovery screen.  Quartz and
    # chalcedony are excluded because amorphous silica is the conservative
    # membrane-system silica-solubility basis; multiple carbonate polymorphs are
    # represented by calcite to avoid double-counting the same carbonate risk.
    practical_names = {
        "Calcite", "Gypsum", "Barite", "Celestite", "Fluorite",
        "Silica (amorph.)", "Hydroxyapatite", "Ferrihydrite",
    }
    practical = [m for m in minerals if m.get("name") in practical_names]
    finite = []
    for mineral in practical:
        try:
            sat = float(mineral.get("concentration_saturation_pct"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(sat):
            finite.append((sat, mineral))
    if not finite:
        return {"minerals": minerals, "practical_minerals": practical, "highest_saturation_pct": None, "limiting_mineral": None}
    sat, limiting = max(finite, key=lambda x: x[0])
    return {
        "minerals": minerals,
        "practical_minerals": practical,
        "highest_saturation_pct": float(sat),
        "limiting_mineral": limiting.get("name"),
        "limiting_formula": limiting.get("formula"),
        "thermodynamically_supersaturated": bool(sat >= 100.0),
    }



def _ccro_graph_number(mapping, *keys):
    for key in keys:
        value = mapping.get(key)
        if value in (None, ""):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            return number
    return None


def _ccro_compact_graph_profile(stage, cycle, cycle_fraction, sequence_recovery, feed_pressure_bar):
    """Retain only the element data required by interactive/report graphs.

    The detailed membrane projection is already required for every CCRO cycle.
    This function copies a compact graph surface from that solved state; it does
    not rerun the membrane or chemistry solver and intentionally excludes ionic
    compositions, carbonate states, convergence histories and other bulky data.
    """
    elements = []
    for index, element in enumerate(stage.get("element_results") or [], start=1):
        membrane_id = element.get("membrane_id") or element.get("membrane") or element.get("membrane_model")
        membrane_model = element.get("membrane_model") or (str(membrane_id).split("|")[1] if membrane_id and "|" in str(membrane_id) else membrane_id)
        elements.append({
            "element": int(element.get("element") or index),
            "flux_lmh": _ccro_graph_number(element, "flux_lmh", "element_flux_lmh"),
            "polarization_factor": _ccro_graph_number(element, "polarization_factor", "cp_factor"),
            "polarization_factor_monovalent": _ccro_graph_number(element, "polarization_factor_monovalent", "polarization_factor", "cp_factor"),
            "polarization_factor_divalent": _ccro_graph_number(element, "polarization_factor_divalent", "polarization_factor", "cp_factor"),
            "feed_pressure_bar": _ccro_graph_number(element, "feed_pressure_bar", "pressure_in_bar", "feed_pressure"),
            "reject_pressure_bar": _ccro_graph_number(element, "reject_pressure_bar", "concentrate_pressure_bar", "pressure_out_bar", "reject_pressure"),
            "membrane_surface_osmotic_bar": _ccro_graph_number(element, "membrane_surface_osmotic_bar", "surface_osmotic_bar", "membrane_osmotic_bar"),
            "feed_osmotic_bar": _ccro_graph_number(element, "feed_osmotic_bar", "bulk_feed_osmotic_bar", "osmotic_pressure_bar"),
            "ndp_bar": _ccro_graph_number(element, "ndp_bar", "net_driving_pressure_bar"),
            "dp_bar": _ccro_graph_number(element, "dp_bar", "pressure_drop_bar", "element_dp_bar"),
            "feed_tds_ppm": _ccro_graph_number(element, "feed_tds_ppm", "feed_tds_mg_l"),
            "reject_tds_ppm": _ccro_graph_number(element, "reject_tds_ppm", "concentrate_tds_ppm", "concentrate_tds_mg_l"),
            "permeate_tds_ppm": _ccro_graph_number(element, "permeate_tds_ppm", "permeate_tds_mg_l"),
            "membrane_id": membrane_id,
            "membrane_model": membrane_model,
        })
    return {
        "cycle": int(cycle),
        "cycle_fraction": float(cycle_fraction),
        "sequence_equivalent_recovery": float(sequence_recovery),
        "feed_pressure_bar": float(feed_pressure_bar),
        "reject_pressure_bar": float(stage.get("concentrate_pressure_bar", stage.get("reject_pressure_bar", 0.0)) or 0.0),
        "element_profile": elements,
    }

def _ccro_composite_permeate(data, streams):
    valid = [x for x in streams if float(x.get("volume_m3", 0.0) or 0.0) > 0]
    if not valid:
        return None, None, None
    total_v = sum(float(x["volume_m3"]) for x in valid)
    water_mode = str(data.get("water_mode", "tds")).lower()
    if water_mode == "full" and all(x.get("composition") for x in valid):
        comp = normalize_composition(valid[0]["composition"])
        vol = float(valid[0]["volume_m3"])
        for x in valid[1:]:
            v = float(x["volume_m3"])
            comp = mix_compositions(comp, vol, x["composition"], v)
            vol += v
        state = None
        if all(x.get("state") for x in valid):
            try:
                state = mix_carbonate_streams([
                    {"flow": float(x["volume_m3"]), "composition": x["composition"], "state": x["state"]}
                    for x in valid
                ], float(data.get("temperature_c", 25.0) or 25.0))
                comp = normalize_composition(state["composition"])
            except (KeyError, ValueError, ZeroDivisionError):
                state = None
        return total_tds_mg_l(comp), comp, state
    tds = sum(float(x["volume_m3"]) * float(x.get("tds_mg_l", 0.0) or 0.0) for x in valid) / max(total_v, 1e-12)
    return tds, None, None


def _ccro_base(data):
    fu, pu = data.get("flow_unit", "m3/h"), data.get("pressure_unit", "bar")
    d = data
    water_mode = str(d.get("water_mode", "tds")).lower()
    vessels = int(round(float(d.get("vessels_1", 0) or 0)))
    epv = int(round(float(d.get("elements_per_vessel_1", 0) or 0)))
    if vessels <= 0:
        raise ValueError("CCRO requires at least one pressure vessel.")
    if not (1 <= epv <= 8):
        raise ValueError("CCRO membranes per pressure vessel must be an integer from 1 to 8.")

    r_avg = _ccro_fraction(d.get("ccro_target_average_recovery"), 0.90)
    if not (0.01 <= r_avg < 0.999):
        raise ValueError("CCRO target average recovery must be between 1% and 99.9%.")
    pf_ratio = float(d.get("ccro_pf_feed_ratio", 1.20) or 1.20)
    if pf_ratio > 10.0:
        pf_ratio /= 100.0
    if pf_ratio <= 0:
        raise ValueError("CCRO PF feed ratio must be greater than zero.")
    r_pf = _ccro_fraction(d.get("ccro_pf_recovery"), 0.20)
    if not (0.01 < r_pf < 0.95):
        raise ValueError("CCRO PF recovery must be between 1% and 95%.")

    q_cc = flow_to_m3h(float(d.get("ccro_closed_circuit_permeate_flow", 0) or 0), fu)
    if q_cc <= 0:
        raise ValueError("Enter the CCRO closed-circuit permeate flow per train.")
    recycle_per_pv = flow_to_m3h(float(d.get("ccro_concentrate_recycle_per_vessel", 0) or 0), fu)
    if recycle_per_pv <= 0:
        raise ValueError("Enter a positive CCRO concentrate recycle flow per pressure vessel.")
    q_recirc = recycle_per_pv * vessels
    q_membrane_cc = q_cc + q_recirc

    raw_system_volume = d.get("ccro_system_volume_m3")
    normalized_volume = raw_system_volume in (None, "") or float(raw_system_volume or 0) <= 0
    system_volume = 1.0 if normalized_volume else float(raw_system_volume)
    if system_volume <= 0:
        raise ValueError("CCRO system volume must be greater than zero.")
    loop_extra_dp = max(0.0, pressure_to_bar(float(d.get("ccro_loop_extra_dp", 0.0) or 0.0), pu))

    fresh_tds = float(d.get("feed_tds", d.get("analysis_tds", 0.0)) or 0.0)
    fresh_comp = composition_from_request(d) if water_mode == "full" else None
    if fresh_comp is not None:
        fresh_tds = total_tds_mg_l(fresh_comp)
    fresh_state = d.get("_feed_carbonate_state") if water_mode == "full" else None

    # Plug-flow projection. Brine discharged during PF is exactly one system
    # volume, so the PF duration is determined by the PF concentrate rate.
    q_pf_feed = pf_ratio * q_cc
    q_pf_perm_target = r_pf * q_pf_feed
    p_pf, pf_stage, pf_evals = _ccro_solve_stage_pressure(
        d, q_pf_feed, q_pf_perm_target, fresh_tds, fresh_comp, fresh_state, None
    )
    q_pf_perm = float(pf_stage["permeate_flow"])
    q_pf_conc = float(pf_stage["reject_flow"])
    if q_pf_conc <= 0:
        raise ValueError("CCRO PF projection produced no concentrate flow to flush the system volume.")
    pf_duration_h = system_volume / q_pf_conc
    pf_perm_volume = q_pf_perm * pf_duration_h
    pf_feed_volume = q_pf_feed * pf_duration_h

    # One sequence rejects one system volume during PF. Therefore the required
    # total permeate volume for a requested sequence-average recovery is exact:
    # R = Vp / (Vp + Vsystem).
    target_perm_volume = system_volume * r_avg / max(1.0 - r_avg, 1e-12)
    cc_perm_required = target_perm_volume - pf_perm_volume
    if cc_perm_required <= 0:
        raise ValueError(
            "The selected average recovery is already met during the PF cycle. Increase average recovery or reduce PF recovery/feed ratio."
        )

    one_cycle_h = system_volume / q_recirc
    one_cycle_perm_volume = q_cc * one_cycle_h
    cc_cycles_required = cc_perm_required / max(one_cycle_perm_volume, 1e-12)
    if cc_cycles_required <= 0:
        raise ValueError("CCRO closed-circuit sequence duration is zero for the requested inputs.")
    full_cycles = int(math.floor(cc_cycles_required + 1e-12))
    last_fraction = cc_cycles_required - full_cycles
    if last_fraction < 1e-9:
        last_fraction = 0.0
    simulated_cycles = full_cycles + (1 if last_fraction > 0 else 0)
    if simulated_cycles > 120:
        raise ValueError(
            f"CCRO requires {cc_cycles_required:.1f} recirculation cycles at this duty. "
            "Increase per-cycle recovery / permeate flow, reduce recycle flow, or review the requested average recovery."
        )

    pump_eff = max(1e-6, float(d.get("pump_eff", 0.85) or 0.85))
    motor_eff = max(1e-6, float(d.get("motor_eff", 0.97) or 0.97))
    vfd_eff = max(1e-6, _vfd_eff(d, "vfd_eff", "pump_no_vfd"))
    circ_eff = max(1e-6, float(d.get("ccro_circulation_pump_eff", d.get("circ_pump_eff", 0.82)) or 0.82))
    circ_motor_eff = max(1e-6, float(d.get("ccro_circulation_motor_eff", d.get("circ_motor_eff", 0.96)) or 0.96))
    circ_vfd_eff = 1.0 if _bool(d, "ccro_circulation_no_vfd", False) else max(1e-6, float(d.get("ccro_circulation_vfd_eff", d.get("circ_vfd_eff", 0.97)) or 0.97))
    suction_bar = pressure_to_bar(float(d.get("suction_pressure", 0.0) or 0.0), pu)

    pf_hpp_kw = _pump_wire_power_kw(q_pf_feed, max(0.0, p_pf - suction_bar), pump_eff, motor_eff, vfd_eff)
    pf_hpp_kwh = pf_hpp_kw * pf_duration_h

    # Composite permeate starts with PF production.
    permeate_streams = [{
        "volume_m3": pf_perm_volume,
        "tds_mg_l": float(pf_stage.get("permeate_tds_ppm", 0.0) or 0.0),
        "composition": pf_stage.get("permeate_composition_mg_l"),
        "state": _ccro_stage_state(pf_stage, "permeate"),
    }]

    loop_tds = fresh_tds
    loop_comp = normalize_composition(fresh_comp) if fresh_comp is not None else None
    loop_state = fresh_state
    previous_pressure = p_pf
    cycle_profile = []
    cycle_graph_profiles = []
    cc_hpp_kwh = 0.0
    cc_recirc_kwh = 0.0
    cc_elapsed_h = 0.0
    cc_perm_volume = 0.0
    pressure_evals = int(pf_evals)
    last_stage = None
    first_stage = None
    first_pressure = None
    final_pressure = p_pf
    peak_hpp_kw = pf_hpp_kw
    peak_recirc_kw = 0.0
    membrane_pressure_limit_bar = _ccro_membrane_pressure_limit_bar(d)
    system_pressure_limit_bar = _ccro_pressure_limit_bar(d)
    minimum_element_ndp_bar = float("inf")
    first_scaling_onset_cycle = None
    first_scaling_onset_recovery = None
    first_scaling_onset_mineral = None
    highest_mineral_saturation_pct = None
    limiting_mineral = None
    limiting_formula = None
    scaling_analysis_error = None

    # Establish the raw/feed saturation baseline first. A feed can already be
    # thermodynamically supersaturated before any RO recovery; in that case the
    # result must say so rather than pretending saturation begins inside CCRO.
    feed_scaling = None
    if water_mode == "full" and fresh_comp:
        feed_stage_for_scaling = {
            "concentrate_composition_mg_l": fresh_comp,
            "concentrate_ph": (fresh_state or {}).get("ph", d.get("feed_ph", 7.0)) if isinstance(fresh_state, dict) else d.get("feed_ph", 7.0),
            "concentrate_tds_ppm": fresh_tds,
        }
        feed_scaling = _ccro_scaling_snapshot(feed_stage_for_scaling, float(d.get("temperature_c", 25.0) or 25.0))
        if feed_scaling:
            scaling_analysis_error = feed_scaling.get("error") or scaling_analysis_error
            sat = feed_scaling.get("highest_saturation_pct")
            if sat is not None:
                highest_mineral_saturation_pct = float(sat)
                limiting_mineral = feed_scaling.get("limiting_mineral")
                limiting_formula = feed_scaling.get("limiting_formula")
                if float(sat) >= 100.0:
                    first_scaling_onset_cycle = -1
                    first_scaling_onset_recovery = 0.0
                    first_scaling_onset_mineral = limiting_mineral

    # PF chemistry is part of the sequence and can itself become the first
    # supersaturated point when the incoming feed is below saturation.
    pf_scaling = _ccro_scaling_snapshot(pf_stage, float(d.get("temperature_c", 25.0) or 25.0)) if water_mode == "full" else None
    if pf_scaling:
        scaling_analysis_error = pf_scaling.get("error") or scaling_analysis_error
        sat = pf_scaling.get("highest_saturation_pct")
        if sat is not None:
            highest_mineral_saturation_pct = float(sat)
            limiting_mineral = pf_scaling.get("limiting_mineral")
            limiting_formula = pf_scaling.get("limiting_formula")
            if float(sat) >= 100.0 and first_scaling_onset_cycle is None:
                first_scaling_onset_cycle = 0
                first_scaling_onset_recovery = pf_perm_volume / max(pf_perm_volume + system_volume, 1e-12)
                first_scaling_onset_mineral = limiting_mineral

    for idx in range(1, simulated_cycles + 1):
        fraction = 1.0
        if idx == simulated_cycles and last_fraction > 0:
            fraction = last_fraction
        raise_if_cancelled()
        p_cc, stage, evals = _ccro_solve_stage_pressure(
            d, q_membrane_cc, q_cc, loop_tds, loop_comp, loop_state, previous_pressure
        )
        pressure_evals += int(evals)
        if first_stage is None:
            first_stage = stage
            first_pressure = p_cc
        last_stage = stage
        final_pressure = p_cc

        q_perm_actual = float(stage["permeate_flow"])
        q_conc_actual = float(stage["reject_flow"])
        # Constant-volume CC operation replaces the permeate leaving the loop
        # with the same fresh-feed volume. The pressure solve makes q_conc equal
        # the specified recirculation flow to numerical tolerance.
        dt_h = one_cycle_h * fraction
        vp = q_perm_actual * dt_h
        cc_elapsed_h += dt_h
        cc_perm_volume += vp

        hpp_kw = _pump_wire_power_kw(q_perm_actual, max(0.0, p_cc - suction_bar), pump_eff, motor_eff, vfd_eff)
        recirc_dp = max(0.0, float(stage.get("stage_dp_bar", 0.0) or 0.0) + loop_extra_dp)
        recirc_kw = _pump_wire_power_kw(q_recirc, recirc_dp, circ_eff, circ_motor_eff, circ_vfd_eff)
        cc_hpp_kwh += hpp_kw * dt_h
        cc_recirc_kwh += recirc_kw * dt_h
        peak_hpp_kw = max(peak_hpp_kw, hpp_kw)
        peak_recirc_kw = max(peak_recirc_kw, recirc_kw)

        perm_state = _ccro_stage_state(stage, "permeate")
        permeate_streams.append({
            "volume_m3": vp,
            "tds_mg_l": float(stage.get("permeate_tds_ppm", 0.0) or 0.0),
            "composition": stage.get("permeate_composition_mg_l"),
            "state": perm_state,
        })

        next_tds, next_comp, next_state = _ccro_mix_states(
            d, stage, fresh_comp, fresh_state, q_conc_actual, q_perm_actual
        )
        applied_tds, applied_comp, applied_state = _ccro_interpolate_loop_state(
            d, loop_tds, loop_comp, loop_state, next_tds, next_comp, next_state, fraction
        )

        equivalent_perm = pf_perm_volume + cc_perm_volume
        equivalent_recovery = equivalent_perm / max(equivalent_perm + system_volume, 1e-12)
        element_ndps = [float(e.get("ndp_bar")) for e in (stage.get("element_results") or []) if e.get("ndp_bar") is not None]
        if element_ndps:
            minimum_element_ndp_bar = min(minimum_element_ndp_bar, min(element_ndps))

        scaling = _ccro_scaling_snapshot(stage, float(d.get("temperature_c", 25.0) or 25.0)) if water_mode == "full" else None
        cycle_highest_sat = None
        cycle_limiting_mineral = None
        if scaling:
            scaling_analysis_error = scaling.get("error") or scaling_analysis_error
            cycle_highest_sat = scaling.get("highest_saturation_pct")
            cycle_limiting_mineral = scaling.get("limiting_mineral")
            if cycle_highest_sat is not None and (highest_mineral_saturation_pct is None or float(cycle_highest_sat) > float(highest_mineral_saturation_pct)):
                highest_mineral_saturation_pct = float(cycle_highest_sat)
                limiting_mineral = cycle_limiting_mineral
                limiting_formula = scaling.get("limiting_formula")
            if cycle_highest_sat is not None and float(cycle_highest_sat) >= 100.0 and first_scaling_onset_cycle is None:
                first_scaling_onset_cycle = idx
                first_scaling_onset_recovery = equivalent_recovery
                first_scaling_onset_mineral = cycle_limiting_mineral

        cycle_graph_profiles.append(_ccro_compact_graph_profile(
            stage, idx, fraction, equivalent_recovery, p_cc
        ))

        cycle_profile.append({
            "cycle": idx,
            "cycle_fraction": fraction,
            "duration_min": dt_h * 60.0,
            "feed_tds_mg_l": float(loop_tds),
            "feed_pressure_bar": float(p_cc),
            "reject_pressure_bar": float(stage.get("reject_pressure_bar", p_cc)),
            "permeate_tds_mg_l": float(stage.get("permeate_tds_ppm", 0.0) or 0.0),
            "concentrate_tds_mg_l": float(stage.get("concentrate_tds_ppm", 0.0) or 0.0),
            "cycle_recovery": float(stage.get("recovery", 0.0) or 0.0),
            "flux_lmh": float(stage.get("flux_lmh", 0.0) or 0.0),
            "polarization_factor": float(stage.get("avg_polarization_factor", 0.0) or 0.0),
            "stage_dp_bar": float(stage.get("stage_dp_bar", 0.0) or 0.0),
            "hpp_kw": float(hpp_kw),
            "recirculation_kw": float(recirc_kw),
            "cumulative_cc_permeate_m3": float(cc_perm_volume),
            "sequence_equivalent_recovery": float(equivalent_recovery),
            "feed_osmotic_bar": float(stage.get("feed_osmotic_bar", 0.0) or 0.0),
            "concentrate_osmotic_bar": float(stage.get("concentrate_osmotic_bar", 0.0) or 0.0),
            "minimum_element_ndp_bar": (min(element_ndps) if element_ndps else None),
            "highest_mineral_saturation_pct": cycle_highest_sat,
            "limiting_mineral": cycle_limiting_mineral,
        })
        loop_tds, loop_comp, loop_state = applied_tds, applied_comp, applied_state
        previous_pressure = p_cc
        set_compute_progress(total=max(simulated_cycles, 1), completed=idx, phase=f"CCRO cycle {idx}/{simulated_cycles}")

    if last_stage is None or first_stage is None:
        raise ValueError("CCRO requires at least one closed-circuit recirculation after PF.")

    # Numerical pressure tolerance can shift volume by a tiny amount. Scale only
    # the sequence accounting to the exact user setpoint while preserving the
    # rigorously projected cycle chemistry and pump powers.
    total_perm_volume_calc = pf_perm_volume + cc_perm_volume
    total_perm_volume = target_perm_volume
    total_sequence_h = pf_duration_h + cc_elapsed_h
    average_product_flow = total_perm_volume / max(total_sequence_h, 1e-12)
    total_source_feed_volume = total_perm_volume + system_volume
    average_feed_flow = total_source_feed_volume / max(total_sequence_h, 1e-12)
    actual_recovery = total_perm_volume / max(total_source_feed_volume, 1e-12)

    composite_tds, composite_comp, composite_state = _ccro_composite_permeate(d, permeate_streams)

    pret_recovery = max(1e-6, min(1.0, float(d.get("pretreatment_recovery", 1.0) or 1.0)))
    pret_pressure = max(0.0, pressure_to_bar(float(d.get("pretreatment_discharge_pressure", 0.0) or 0.0), pu))
    pret_pump_eff = max(1e-6, float(d.get("pretreatment_pump_eff", 0.82) or 0.82))
    pret_motor_eff = max(1e-6, float(d.get("pretreatment_motor_eff", 0.95) or 0.95))
    pret_vfd_eff = max(1e-6, _vfd_eff(d, "pretreatment_vfd_eff", "pretreatment_no_vfd"))
    raw_feed_volume = total_source_feed_volume / pret_recovery
    pretreatment_kwh = raw_feed_volume * pret_pressure / 36.0 / max(pret_pump_eff * pret_motor_eff * pret_vfd_eff, 1e-12)

    ro_kwh = pf_hpp_kwh + cc_hpp_kwh + cc_recirc_kwh
    ro_sec = ro_kwh / max(total_perm_volume, 1e-12)
    pret_sec = pretreatment_kwh / max(total_perm_volume, 1e-12)
    total_sec = ro_sec + pret_sec
    avg_ro_kw = ro_kwh / max(total_sequence_h, 1e-12)
    avg_pret_kw = pretreatment_kwh / max(total_sequence_h, 1e-12)

    pressure_margin_bar = system_pressure_limit_bar - final_pressure
    pressure_utilization_pct = 100.0 * final_pressure / max(system_pressure_limit_bar, 1e-12)
    minimum_element_ndp_bar = None if not math.isfinite(minimum_element_ndp_bar) else minimum_element_ndp_bar

    if first_scaling_onset_recovery is not None and first_scaling_onset_recovery <= actual_recovery + 1e-12:
        recovery_limiter = "Water chemistry / mineral scaling review"
        if first_scaling_onset_recovery <= 1e-12:
            recovery_limiter_detail = (
                "The incoming water is already thermodynamically supersaturated"
                + (f" with respect to {first_scaling_onset_mineral}" if first_scaling_onset_mineral else " for at least one practical RO scaling mineral")
                + "; CCRO concentration increases that scaling burden. Pretreatment/antiscalant-specific allowable supersaturation is not modeled as a universal limit."
            )
        else:
            recovery_limiter_detail = (
                f"Thermodynamic supersaturation first appears at approximately {100.0*first_scaling_onset_recovery:.2f}% sequence recovery"
                + (f" ({first_scaling_onset_mineral})" if first_scaling_onset_mineral else "")
                + ". Pretreatment/antiscalant-specific allowable supersaturation is not modeled as a universal limit."
            )
    elif pressure_utilization_pct >= 95.0:
        recovery_limiter = "Osmotic pressure / membrane pressure envelope"
        recovery_limiter_detail = (
            f"Required peak pressure is {final_pressure:.2f} bar ({pressure_utilization_pct:.1f}% of the active membrane/equipment limit of {system_pressure_limit_bar:.2f} bar)."
        )
    else:
        recovery_limiter = "Target reached within modeled constraints"
        recovery_limiter_detail = "No universal CCRO recovery cap is applied; continue engineering review of chemistry, pressure, flux, polarization and hydraulics."

    warnings = []
    if not (1.10 <= pf_ratio <= 1.50):
        warnings.append("PF feed ratio is outside the public 1.10–1.50 reference starting range; verify the sequence hydraulics for the selected CCRO configuration.")
    if not (0.10 <= r_pf <= 0.30):
        warnings.append("PF recovery is outside the public 10–30% reference starting range; verify the sequence hydraulics for the selected CCRO configuration.")
    if not (4.54 <= recycle_per_pv <= 7.95):
        warnings.append("Concentrate recycle per pressure vessel is outside the public 4.54–7.95 m³/h/PV reference starting range; verify crossflow, pressure drop and membrane-vessel hydraulics.")
    if cc_elapsed_h * 60.0 < 5.0 and not normalized_volume:
        warnings.append("Closed-circuit sequence duration is below 5 minutes; review system volume/spacer allowance, flux and recycle flow.")
    if cc_cycles_required < 1.0:
        warnings.append("Less than one complete CC recirculation is required; the duty is approaching conventional single-pass RO rather than a practical CCRO sequence.")
    if normalized_volume:
        warnings.append("CCRO system volume was not entered. A normalized 1.0 m³ basis was used: recovery, cycles and SEC remain normalized, but absolute sequence duration/batch volume must not be used for equipment sizing.")
    if pressure_utilization_pct >= 90.0:
        warnings.append(f"Peak CC pressure uses {pressure_utilization_pct:.1f}% of the active pressure envelope ({system_pressure_limit_bar:.2f} bar); verify membrane, pressure-vessel, pump, piping and valve ratings with the actual equipment selected.")
    if water_mode != "full":
        warnings.append("CCRO scaling/solubility limits cannot be evaluated from TDS-only water input. Use Full water chemistry before treating the requested recovery as chemically feasible.")
    elif scaling_analysis_error:
        warnings.append(f"CCRO mineral-saturation screening could not be completed for every sequence point: {scaling_analysis_error}")
    elif first_scaling_onset_recovery is not None:
        if first_scaling_onset_recovery <= 1e-12:
            warnings.append(
                "The incoming water is already thermodynamically supersaturated"
                + (f" with respect to {first_scaling_onset_mineral}." if first_scaling_onset_mineral else " for at least one practical RO scaling mineral.")
                + " CCRO will increase the concentration factor; verify pretreatment, antiscalant/acid strategy, residence time and precipitation kinetics before accepting the target recovery."
            )
        else:
            warnings.append(
                f"Thermodynamic mineral supersaturation begins at approximately {100.0*first_scaling_onset_recovery:.2f}% sequence recovery"
                + (f"; limiting mineral: {first_scaling_onset_mineral}." if first_scaling_onset_mineral else ".")
                + " This is a solubility warning, not an antiscalant guarantee; allowable supersaturation depends on pretreatment, dose, residence time and scaling kinetics."
            )
    if loop_extra_dp <= 1e-12:
        warnings.append("No additional closed-loop piping/valve pressure loss was entered; circulation-pump SEC currently includes membrane-stage pressure drop only.")

    result = {
        "process_type": "CCRO",
        "ccro": True,
        "erd_type": "Closed Circuit Reverse Osmosis",
        "stage_count": 1,
        "membrane_coupling": True,
        "ccro_model_basis": "Cyclic single-stage membrane projection with 100% concentrate recirculation and plug-flow flush",
        "ccro_target_average_recovery": r_avg,
        "recovery": actual_recovery,
        "feed_flow": average_feed_flow,
        "product_flow": average_product_flow,
        "product_m3d": average_product_flow * 24.0,
        "reject_flow_1": system_volume / max(total_sequence_h, 1e-12),
        "reject_flow_final": system_volume / max(total_sequence_h, 1e-12),
        "membrane_pressure_1": final_pressure,
        "reject_pressure_1": float(last_stage.get("reject_pressure_bar", final_pressure)),
        "ccro_closed_circuit_permeate_flow": q_cc,
        "ccro_cc_membrane_feed_flow": q_membrane_cc,
        "ccro_concentrate_recycle_per_vessel": recycle_per_pv,
        "ccro_recirculation_flow": q_recirc,
        "ccro_pf_feed_ratio": pf_ratio,
        "ccro_pf_recovery": float(pf_stage.get("recovery", r_pf)),
        "ccro_pf_feed_flow": q_pf_feed,
        "ccro_pf_permeate_flow": q_pf_perm,
        "ccro_pf_concentrate_flow": q_pf_conc,
        "ccro_pf_pressure_bar": p_pf,
        "ccro_first_cycle_pressure_bar": first_pressure,
        "ccro_final_cycle_pressure_bar": final_pressure,
        "ccro_pressure_rise_bar": final_pressure - float(first_pressure or final_pressure),
        "ccro_system_volume_m3": system_volume,
        "ccro_system_volume_normalized": normalized_volume,
        "ccro_one_cycle_duration_min": one_cycle_h * 60.0,
        "ccro_pf_sequence_duration_min": pf_duration_h * 60.0,
        "ccro_cc_sequence_duration_min": cc_elapsed_h * 60.0,
        "ccro_complete_sequence_duration_min": total_sequence_h * 60.0,
        "ccro_cc_cycles": cc_cycles_required,
        "ccro_total_cycles": 1.0 + cc_cycles_required,
        "ccro_full_cc_cycles": full_cycles,
        "ccro_final_cycle_fraction": last_fraction,
        "ccro_permeate_volume_per_batch_m3": total_perm_volume,
        "ccro_pf_permeate_volume_m3": pf_perm_volume,
        "ccro_cc_permeate_volume_m3": cc_perm_volume,
        "ccro_brine_flush_volume_m3": system_volume,
        "ccro_initial_feed_tds_mg_l": fresh_tds,
        "ccro_final_loop_feed_tds_mg_l": float(loop_tds),
        "ccro_final_membrane_concentrate_tds_mg_l": float(last_stage.get("concentrate_tds_ppm", 0.0) or 0.0),
        "ccro_composite_permeate_tds_mg_l": composite_tds,
        "ccro_cycle_profile": cycle_profile,
        "ccro_cycle_graph_profiles": cycle_graph_profiles,
        "ccro_pressure_solve_evaluations": pressure_evals,
        "ccro_hpp_peak_kw": peak_hpp_kw,
        "ccro_recirculation_peak_kw": peak_recirc_kw,
        "ccro_pf_hpp_kw": pf_hpp_kw,
        "ccro_ro_energy_per_batch_kwh": ro_kwh,
        "ccro_pretreatment_energy_per_batch_kwh": pretreatment_kwh,
        "hpp_flow": max(q_pf_feed, q_cc),
        "hpp_dp": max(0.0, final_pressure - suction_bar),
        "hpp_kw": peak_hpp_kw,
        "circ_flow": q_recirc,
        "circ_dp": max(0.0, float(last_stage.get("stage_dp_bar", 0.0) or 0.0) + loop_extra_dp),
        "circ_kw": peak_recirc_kw,
        "electric_kw": avg_ro_kw,
        "pretreatment_kw": avg_pret_kw,
        "ro_sec": ro_sec,
        "pump_sec": ro_sec,
        "pretreatment_sec": pret_sec,
        "total_sec": total_sec,
        "ccro_membrane_pressure_limit_bar": membrane_pressure_limit_bar,
        "ccro_system_pressure_limit_bar": system_pressure_limit_bar,
        "ccro_pressure_margin_bar": pressure_margin_bar,
        "ccro_pressure_utilization_pct": pressure_utilization_pct,
        "ccro_minimum_element_ndp_bar": minimum_element_ndp_bar,
        "ccro_final_feed_osmotic_bar": float(last_stage.get("feed_osmotic_bar", 0.0) or 0.0),
        "ccro_final_concentrate_osmotic_bar": float(last_stage.get("concentrate_osmotic_bar", 0.0) or 0.0),
        "ccro_initial_highest_mineral_saturation_pct": (feed_scaling or {}).get("highest_saturation_pct") if feed_scaling else None,
        "ccro_initial_limiting_mineral": (feed_scaling or {}).get("limiting_mineral") if feed_scaling else None,
        "ccro_first_scaling_onset_cycle": first_scaling_onset_cycle,
        "ccro_first_scaling_onset_recovery": first_scaling_onset_recovery,
        "ccro_first_scaling_onset_mineral": first_scaling_onset_mineral,
        "ccro_highest_mineral_saturation_pct": highest_mineral_saturation_pct,
        "ccro_limiting_mineral": limiting_mineral,
        "ccro_limiting_mineral_formula": limiting_formula,
        "ccro_recovery_limiter": recovery_limiter,
        "ccro_recovery_limiter_detail": recovery_limiter_detail,
        "ccro_scaling_screen_basis": "Bulk-concentrate thermodynamic mineral saturation; antiscalant kinetics/provider limits are not universalized",
        "ccro_warnings": warnings,
        "ccro_public_reference_ranges": {
            "pf_feed_ratio_reference_starting_range": "1.10–1.50",
            "pf_recovery_reference_starting_range": "10–30%",
            "concentrate_recycle_reference_m3h_per_pv": "4.54–7.95",
            "minimum_cc_duration_review_min": 5.0,
            "recovery_limit": "No universal CCRO recovery cap; constrained by chemistry, osmotic/pressure envelope, membrane flux/polarization and hydraulics",
            "pressure_limit": "Selected membrane/equipment rating, not a CCRO-specific fixed pressure",
        },
    }
    _attach_membrane(result, last_stage, "stage1_")
    result["stage1_feed_tds_ppm"] = float(last_stage.get("feed_tds_ppm", loop_tds))
    result["stage1_permeate_tds_ppm"] = float(last_stage.get("permeate_tds_ppm", 0.0) or 0.0)
    result["stage1_concentrate_tds_ppm"] = float(last_stage.get("concentrate_tds_ppm", 0.0) or 0.0)
    result["stage1_recovery"] = float(last_stage.get("recovery", 0.0) or 0.0)
    result["stage1_feed_pressure_bar"] = final_pressure
    result["stage1_concentrate_pressure_bar"] = float(last_stage.get("reject_pressure_bar", final_pressure))
    result["stage1_feed_flow"] = q_membrane_cc
    result["stage1_permeate_flow"] = float(last_stage.get("permeate_flow", q_cc))
    result["stage1_concentrate_flow"] = float(last_stage.get("reject_flow", q_recirc))
    result["stage1_dp_bar"] = float(last_stage.get("stage_dp_bar", 0.0) or 0.0)
    result["total_pressure_vessels"] = vessels
    result["total_membrane_elements"] = vessels * epv
    result["total_membrane_area_m2"] = float(last_stage.get("membrane_total_area_m2", 0.0) or 0.0)
    if composite_comp is not None:
        result["composite_permeate_composition_mg_l"] = composite_comp
        result["stage1_composite_permeate_composition_mg_l"] = composite_comp
    if composite_state is not None:
        result["composite_permeate_ph"] = composite_state.get("ph")
        result["composite_permeate_alkalinity_mg_l_as_hco3"] = composite_state.get("total_alkalinity_mg_l_as_hco3")
        result["composite_permeate_total_alkalinity_mol_kg"] = composite_state.get("total_alkalinity_mol_kg")
        result["composite_permeate_total_inorganic_carbon_mol_kg"] = composite_state.get("total_inorganic_carbon_mol_kg")
    if loop_comp is not None:
        result["ccro_final_loop_composition_mg_l"] = loop_comp
    if loop_state is not None:
        result["ccro_final_loop_ph"] = loop_state.get("ph")
        result["ccro_final_loop_alkalinity_mg_l_as_hco3"] = loop_state.get("total_alkalinity_mg_l_as_hco3")

    # Generic UI/report fields use the requested display units, while detailed
    # cycle-profile arrays deliberately remain in m³/h and bar for unambiguous
    # engineering plotting and export.
    out = display(result, fu, pu)
    return out


def ccro(data):
    data = dict(data or {})
    data["membrane_coupling"] = "on"
    prepared = _prepare_calculation_data(data)
    return _attach_acid_dosing(_ccro_base(prepared), prepared)
