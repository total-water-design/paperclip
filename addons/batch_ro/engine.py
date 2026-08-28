"""Transient Batch RO engineering model for Total RO Design / TWDS.

The model is intentionally additive to the existing Total RO Design membrane
projection.  It reuses the same membrane database, solution-diffusion transport,
temperature corrections, hydraulic pressure-drop model, full-ion osmotic engine,
and carbonate/scaling chemistry used by conventional RO.

The Batch RO layer adds the time-varying system inventory and cycle physics:

* fully-batch feed: no fresh feed is mixed into the concentrating inventory;
* pressure is re-solved as concentration rises to hold the requested active
  permeate production (or operating flux);
* tank, membrane-channel and external/piping liquid volumes are explicit;
* productive time, reset/purge time and effective flux/productivity are explicit;
* HPP, high-pressure recirculation, pressure-exchanger/booster, refill and
  pretreatment energy are integrated over the cycle;
* salt passage is accumulated into a composite permeate and removed from the
  batch inventory species-by-species;
* in Full Water Analysis mode, total alkalinity and total inorganic carbon are
  conserved through the batch and re-equilibrated after each permeate increment;
* mineral saturation is screened along the recovery path using the shared
  Total RO chemistry engine.

This is an engineering transient/quasi-steady membrane model: each recovery
increment is a converged steady membrane pass at the current batch state while
the closed batch inventory evolves in time.  It is not a CFD model of axial
mixing inside external piping.  The explicit external-volume inputs therefore
capture real inventory, duty-cycle and reset consequences without inventing a
correlation for unvalidated pipe-mixing behavior.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from calculations import (
    _attach_membrane,
    _membrane_pressure_limit_bar,
    flow_from_m3h,
    flow_to_m3h,
    membrane_stage,
    pressure_from_bar,
    pressure_to_bar,
)
from chemistry_analysis import (
    analytical_alkalinity_mol_kg,
    analyze_water,
    solve_carbonate_state,
)
from membrane_db import get_membrane
from water_chemistry import (
    SPECIES,
    composition_from_request,
    normalize_composition,
    osmotic_state_from_composition,
    solution_specific_gravity,
    total_tds_mg_l,
)

KWH_PER_M3_BAR = 1.0 / 36.0
MIN_VOLUME = 1e-9
MIN_FLOW = 1e-9
CARBONATE_KEYS = {"bicarbonate", "carbonate"}
CONFIGURATIONS = {"atmospheric_px", "high_pressure_tank", "dual_compartment"}


def _f(data: Mapping[str, Any], key: str, default: float | None = None) -> float | None:
    value = data.get(key, default)
    if value in (None, ""):
        return default
    return float(value)


def _b(data: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _fraction(value: float | None, default: float) -> float:
    if value is None:
        value = default
    value = float(value)
    if value > 1.5:  # tolerate users/API clients supplying percentages
        value /= 100.0
    return value


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(max(float(value), lo), hi)


def _wire_power_kw(flow_m3h: float, dp_bar: float, pump_eff: float, motor_eff: float, vfd_eff: float) -> float:
    hydraulic_kw = max(0.0, float(flow_m3h)) * max(0.0, float(dp_bar)) / 36.0
    return hydraulic_kw / max(float(pump_eff) * float(motor_eff) * float(vfd_eff), 1e-12)


def _water_kg_per_m3(comp: Mapping[str, float], temp_c: float) -> float:
    c = normalize_composition(comp)
    tds = total_tds_mg_l(c)
    solution_kg_m3 = solution_specific_gravity(tds, temp_c) * 1000.0
    dissolved_kg_m3 = tds / 1000.0
    return max(650.0, solution_kg_m3 - dissolved_kg_m3)


def _recipe_ids(data: Mapping[str, Any], membrane_id: str, elements_per_vessel: int) -> list[str]:
    recipe = data.get("membrane_recipe_1")
    if recipe in (None, ""):
        return [membrane_id] * elements_per_vessel
    if isinstance(recipe, str):
        raw = recipe.strip()
        if raw.startswith("["):
            import json
            try:
                recipe = json.loads(raw)
            except Exception:
                recipe = [x.strip() for x in raw.split(",") if x.strip()]
        else:
            recipe = [x.strip() for x in raw.split(",") if x.strip()]
    if not isinstance(recipe, (list, tuple)):
        raise ValueError("Batch RO membrane recipe must be a list of membrane IDs.")
    ids = [str(x or membrane_id) for x in recipe]
    if len(ids) != elements_per_vessel:
        raise ValueError(
            f"Batch RO membrane recipe has {len(ids)} positions but the vessel has {elements_per_vessel} elements."
        )
    for mid in ids:
        get_membrane(mid)
    return ids


def _membrane_geometry(data: Mapping[str, Any], membrane_id: str, vessels: int, elements_per_vessel: int) -> dict:
    recipe = _recipe_ids(data, membrane_id, elements_per_vessel)
    records = [get_membrane(mid) for mid in recipe]
    channel_height_m = max(0.0001, float(_f(data, "batch_channel_height_mm", 0.71))) / 1000.0
    porosity = _clamp(float(_f(data, "batch_channel_porosity", 0.90)), 0.20, 0.99)
    default_length = max(0.1, float(_f(data, "batch_element_length_m", 1.016)))
    volumes_per_position = []
    recirc_per_vessel_candidates = []
    inlet_velocity = max(0.01, float(_f(data, "batch_inlet_velocity_m_s", 0.18)))
    for record in records:
        area = float(record["area_m2"])
        length = float(record.get("length_m") or default_length)
        # Swaminathan/Lienhard batch-inventory basis: phi * A * d_ch / 2.
        element_liquid_m3 = porosity * area * channel_height_m / 2.0
        volumes_per_position.append(element_liquid_m3)
        # Equivalent feed-channel width A/(2L), then superficial channel velocity.
        channel_width_m = area / max(2.0 * length, 1e-12)
        q_m3h = inlet_velocity * channel_width_m * channel_height_m * porosity * 3600.0
        recirc_per_vessel_candidates.append(q_m3h)
    element_volume_m3 = sum(volumes_per_position) * vessels
    membrane_area_m2 = sum(float(r["area_m2"]) for r in records) * vessels
    recirc_default_m3h_per_vessel = max(recirc_per_vessel_candidates[0], 0.1)
    return {
        "recipe": recipe,
        "records": records,
        "channel_height_mm": channel_height_m * 1000.0,
        "channel_porosity": porosity,
        "inlet_velocity_m_s": inlet_velocity,
        "element_volume_m3": element_volume_m3,
        "membrane_area_m2": membrane_area_m2,
        "recirc_default_m3h_per_vessel": recirc_default_m3h_per_vessel,
    }


def _initial_full_state(data: Mapping[str, Any], temp_c: float) -> tuple[dict, dict]:
    analytical = composition_from_request(data)
    if total_tds_mg_l(analytical) <= 0:
        raise ValueError("Full Water Analysis mode requires a non-zero ionic composition for Batch RO.")
    ph = float(_f(data, "feed_ph", 7.6))
    ta = analytical_alkalinity_mol_kg(analytical, temp_c)
    state = solve_carbonate_state(
        analytical,
        temp_c,
        ph=ph,
        total_alkalinity_mol_kg=ta,
    )
    return analytical, state


def _prepared_carbonate_state(state: Mapping[str, Any]) -> dict:
    return {
        "composition": normalize_composition(state["composition"]),
        "ph": float(state["ph"]),
        "total_alkalinity_mol_kg": float(state["total_alkalinity_mol_kg"]),
        "total_inorganic_carbon_mol_kg": float(state["total_inorganic_carbon_mol_kg"]),
        "total_alkalinity_mg_l_as_hco3": float(state.get("total_alkalinity_mg_l_as_hco3", 0.0)),
        "_prepared_feed_state": True,
    }


def _state_from_extensive_carbon(
    noncarbonate_mass_g: Mapping[str, float],
    volume_m3: float,
    ta_total_mol: float,
    ct_total_mol: float,
    temp_c: float,
    seed_ph: float,
) -> dict:
    volume_m3 = max(float(volume_m3), MIN_VOLUME)
    base = {k: 0.0 for k in SPECIES}
    for k in SPECIES:
        if k in CARBONATE_KEYS:
            continue
        base[k] = max(0.0, float(noncarbonate_mass_g.get(k, 0.0))) / volume_m3
    base["bicarbonate"] = 0.0
    base["carbonate"] = 0.0
    water_kg = _water_kg_per_m3(base, temp_c) * volume_m3
    ta = float(ta_total_mol) / max(water_kg, 1e-12)
    ct = max(0.0, float(ct_total_mol)) / max(water_kg, 1e-12)
    return solve_carbonate_state(
        base,
        temp_c,
        ph=float(seed_ph),
        total_alkalinity_mol_kg=ta,
        total_inorganic_carbon_mol_kg=ct,
    )


def _blend_carbonate_state(primary: Mapping[str, Any], secondary: Mapping[str, Any] | None, fraction: float, temp_c: float) -> dict:
    if not secondary or fraction <= 1e-12:
        return dict(primary)
    f = _clamp(fraction, 0.0, 0.50)
    a = normalize_composition(primary["composition"])
    b = normalize_composition(secondary["composition"])
    base = {k: (1.0 - f) * a[k] + f * b[k] for k in SPECIES}
    ta = (1.0 - f) * float(primary["total_alkalinity_mol_kg"]) + f * float(secondary["total_alkalinity_mol_kg"])
    ct = (1.0 - f) * float(primary["total_inorganic_carbon_mol_kg"]) + f * float(secondary["total_inorganic_carbon_mol_kg"])
    ph_seed = (1.0 - f) * float(primary["ph"]) + f * float(secondary["ph"])
    base["bicarbonate"] = 0.0
    base["carbonate"] = 0.0
    return solve_carbonate_state(base, temp_c, ph=ph_seed, total_alkalinity_mol_kg=ta, total_inorganic_carbon_mol_kg=ct)


def _analytical_for_scaling(state: Mapping[str, Any]) -> dict:
    c = normalize_composition(state["composition"])
    c["bicarbonate"] = float(state.get("total_alkalinity_mg_l_as_hco3", 0.0))
    c["carbonate"] = 0.0
    return c


def _scaling_screen(state: Mapping[str, Any], temp_c: float) -> dict:
    try:
        report = analyze_water(_analytical_for_scaling(state), temp_c, float(state["ph"]))
    except Exception as exc:
        return {"available": False, "warning": str(exc), "max_pct": None, "mineral": None}
    minerals = report.get("minerals") or []
    finite = []
    for mineral in minerals:
        try:
            pct = float(mineral.get("concentration_saturation_pct"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(pct):
            finite.append((pct, str(mineral.get("name") or "")))
    if not finite:
        return {"available": True, "max_pct": None, "mineral": None, "report": report}
    pct, mineral = max(finite, key=lambda x: x[0])
    return {"available": True, "max_pct": pct, "mineral": mineral, "report": report}


def _stage_solve_at_pressure(
    pressure_bar: float,
    *,
    data: Mapping[str, Any],
    q_feed_m3h: float,
    membrane_id: str,
    vessels: int,
    elements_per_vessel: int,
    feed_tds: float,
    temp_c: float,
    feed_state: Mapping[str, Any] | None,
    full_water: bool,
    resolve_carbonate_streams: bool,
) -> dict:
    return membrane_stage(
        q_feed_m3h,
        pressure_bar,
        membrane_id,
        vessels,
        elements_per_vessel,
        feed_tds,
        permeate_pressure_bar=float(data["_batch_permeate_pressure_bar"]),
        temperature_c=temp_c,
        feed_ionic_strength=None,
        feed_composition=(feed_state["composition"] if full_water else None),
        feed_ph=(float(feed_state["ph"]) if full_water else float(_f(data, "feed_ph", 7.6))),
        water_mode=("full" if full_water else "tds"),
        fouling_factor=float(_f(data, "fouling_factor", 1.0)),
        salt_passage_factor=float(_f(data, "salt_passage_factor", 1.0)),
        feed_carbonate_state=(_prepared_carbonate_state(feed_state) if full_water else None),
        resolve_carbonate_streams=resolve_carbonate_streams,
        membrane_recipe=data.get("membrane_recipe_1"),
    )


def _solve_pressure_for_permeate(
    target_qp_m3h: float,
    *,
    data: Mapping[str, Any],
    q_feed_m3h: float,
    membrane_id: str,
    vessels: int,
    elements_per_vessel: int,
    feed_tds: float,
    temp_c: float,
    feed_state: Mapping[str, Any] | None,
    full_water: bool,
    pressure_limit_bar: float,
    previous_pressure_bar: float | None,
) -> tuple[dict | None, dict]:
    target = max(float(target_qp_m3h), MIN_FLOW)
    permeate_pressure = float(data["_batch_permeate_pressure_bar"])
    # The lower bracket deliberately begins near the hydraulic suction/permeate
    # floor. The membrane model itself determines whether any positive flux is possible.
    low = max(permeate_pressure + 0.05, float(data["_batch_suction_pressure_bar"]))
    high = float(pressure_limit_bar)

    cache: dict[float, dict] = {}

    def evaluate(p: float) -> dict:
        key = round(float(p), 7)
        if key not in cache:
            cache[key] = _stage_solve_at_pressure(
                p,
                data=data,
                q_feed_m3h=q_feed_m3h,
                membrane_id=membrane_id,
                vessels=vessels,
                elements_per_vessel=elements_per_vessel,
                feed_tds=feed_tds,
                temp_c=temp_c,
                feed_state=feed_state,
                full_water=full_water,
                resolve_carbonate_streams=False,
            )
        return cache[key]

    def evaluate_trial(p: float) -> dict | None:
        try:
            return evaluate(p)
        except ValueError as exc:
            if "did not converge" in str(exc).casefold():
                return None
            raise

    # Establish the governed pressure ceiling first.
    try:
        shi = evaluate_trial(high)
    except ValueError as exc:
        return None, {
            "reason": "membrane_solve",
            "detail": str(exc),
            "pressure_limit_bar": pressure_limit_bar,
        }

    if shi is None:
        return None, {
            "reason": "membrane_solve",
            "detail": (
                f"Membrane calculation did not converge at the active "
                f"pressure limit of {pressure_limit_bar:.2f} bar."
            ),
            "pressure_limit_bar": pressure_limit_bar,
        }

    fhi = float(shi["permeate_flow"]) - target
    if fhi < -max(0.002 * target, 1e-5):
        return None, {
            "reason": "pressure_limit",
            "detail": (
                f"Active permeate target {target_qp_m3h:.3f} m³/h cannot be maintained at the active "
                f"pressure limit of {pressure_limit_bar:.2f} bar."
            ),
            "pressure_limit_bar": pressure_limit_bar,
            "max_permeate_flow_m3h": float(shi["permeate_flow"]),
        }

    try:
        slo = evaluate_trial(low)
    except ValueError as exc:
        return None, {
            "reason": "membrane_solve",
            "detail": str(exc),
            "pressure_limit_bar": pressure_limit_bar,
        }

    if slo is None:
        invalid = low
        valid = high
        valid_stage = shi

        for _ in range(24):
            trial = 0.5 * (invalid + valid)
            stage = evaluate_trial(trial)

            if stage is None:
                invalid = trial
            else:
                valid = trial
                valid_stage = stage

            if valid - invalid <= 0.01:
                break

        low = valid
        slo = valid_stage

    flo = float(slo["permeate_flow"]) - target

    if flo >= 0:
        p = low
    else:
        # Warm pressure is used only as an interior trial; the final bracket remains safeguarded.
        if previous_pressure_bar is not None and low < previous_pressure_bar < high:
            warm = evaluate_trial(previous_pressure_bar)
            if warm is not None:
                fw = float(warm["permeate_flow"]) - target
                if fw >= 0:
                    high = previous_pressure_bar
                else:
                    low = previous_pressure_bar
        for _ in range(38):
            mid = 0.5 * (low + high)
            smid = evaluate_trial(mid)
            if smid is None:
                low = mid
                continue
            fm = float(smid["permeate_flow"]) - target
            if abs(fm) <= max(0.0015 * target, 2e-5) or (high - low) <= 0.002:
                low = high = mid
                break
            if fm >= 0:
                high = mid
            else:
                low = mid
        p = 0.5 * (low + high)

    # Recalculate the accepted duty with carbonate/speciation reporting enabled.
    try:
        final_stage = _stage_solve_at_pressure(
            p,
            data=data,
            q_feed_m3h=q_feed_m3h,
            membrane_id=membrane_id,
            vessels=vessels,
            elements_per_vessel=elements_per_vessel,
            feed_tds=feed_tds,
            temp_c=temp_c,
            feed_state=feed_state,
            full_water=full_water,
            resolve_carbonate_streams=True,
        )
    except ValueError as exc:
        return None, {"reason": "membrane_solve", "detail": str(exc), "pressure_limit_bar": pressure_limit_bar}
    return final_stage, {"reason": "ok", "pressure_bar": p}


def _configuration_label(config: str) -> str:
    return {
        "atmospheric_px": "Atmospheric batch tank + isobaric pressure exchanger",
        "high_pressure_tank": "Variable-volume high-pressure batch tank",
        "dual_compartment": "Alternating dual-compartment / moving-divider batch",
    }[config]


def calculate_batch_ro(data: Mapping[str, Any]) -> dict:
    """Calculate a complete Batch RO productive/reset cycle."""
    raw = dict(data or {})
    flow_unit = str(raw.get("flow_unit", "m3/h"))
    pressure_unit = str(raw.get("pressure_unit", "bar"))
    config = str(raw.get("batch_configuration", "atmospheric_px") or "atmospheric_px").strip().lower()
    if config not in CONFIGURATIONS:
        raise ValueError(f"Unknown Batch RO configuration: {config}")

    target_recovery_pct = float(_f(raw, "batch_target_recovery", 50.0))
    if not (1.0 <= target_recovery_pct < 97.0):
        raise ValueError("Batch RO target recovery must be between 1% and 97%.")
    target_recovery = target_recovery_pct / 100.0
    temp_c = float(_f(raw, "temperature_c", 25.0))
    vessels = int(float(_f(raw, "vessels_1", 0)))
    elements_per_vessel = int(float(_f(raw, "elements_per_vessel_1", 0)))
    if vessels <= 0:
        raise ValueError("Batch RO requires at least one pressure vessel.")
    if not (1 <= elements_per_vessel <= 8):
        raise ValueError("Batch RO requires 1–8 membrane elements per pressure vessel.")
    membrane_id = str(raw.get("membrane_1") or "").strip()
    if not membrane_id:
        raise ValueError("Select a Batch RO membrane.")

    geometry = _membrane_geometry(raw, membrane_id, vessels, elements_per_vessel)
    membrane_area_m2 = geometry["membrane_area_m2"]
    element_volume_m3 = geometry["element_volume_m3"]
    if membrane_area_m2 <= 0 or element_volume_m3 <= 0:
        raise ValueError("Selected membrane geometry does not provide a usable area/liquid-volume basis.")

    piping_volume_m3 = _f(raw, "batch_piping_volume_m3", None)
    if piping_volume_m3 is None:
        piping_volume_m3 = element_volume_m3 * max(0.0, float(_f(raw, "batch_piping_volume_pct_elements", 12.0))) / 100.0
    piping_volume_m3 = max(0.0, float(piping_volume_m3))
    final_tank_volume_m3 = _f(raw, "batch_final_tank_volume_m3", None)
    if final_tank_volume_m3 is None:
        final_tank_volume_m3 = element_volume_m3 * max(0.0, float(_f(raw, "batch_final_tank_volume_pct_elements", 0.0))) / 100.0
    final_tank_volume_m3 = max(0.0, float(final_tank_volume_m3))
    fixed_inventory_m3 = element_volume_m3 + piping_volume_m3

    requested_permeate_cycle = _f(raw, "batch_permeate_per_cycle_m3", None)
    if requested_permeate_cycle is not None and requested_permeate_cycle > 0:
        initial_inventory_m3 = float(requested_permeate_cycle) / target_recovery
        final_inventory_m3 = initial_inventory_m3 * (1.0 - target_recovery)
        if final_inventory_m3 + 1e-9 < fixed_inventory_m3:
            min_product = target_recovery * fixed_inventory_m3 / max(1.0 - target_recovery, 1e-12)
            raise ValueError(
                f"Requested batch volume is too small for the membrane+piping liquid inventory. "
                f"At {target_recovery_pct:.1f}% recovery, permeate/cycle must be at least {min_product:.3f} m³."
            )
        final_tank_volume_m3 = final_inventory_m3 - fixed_inventory_m3
    else:
        final_inventory_m3 = fixed_inventory_m3 + final_tank_volume_m3
        initial_inventory_m3 = final_inventory_m3 / max(1.0 - target_recovery, 1e-12)
        requested_permeate_cycle = initial_inventory_m3 * target_recovery
    initial_tank_volume_m3 = initial_inventory_m3 - fixed_inventory_m3
    if initial_tank_volume_m3 <= 0:
        raise ValueError("Calculated initial batch tank volume is not positive; increase batch recovery/inventory or review external volumes.")

    recirc_override = _f(raw, "batch_recirculation_flow_per_vessel", None)
    if recirc_override is None:
        recirc_per_vessel_m3h = geometry["recirc_default_m3h_per_vessel"]
    else:
        recirc_per_vessel_m3h = flow_to_m3h(float(recirc_override), flow_unit)
    if recirc_per_vessel_m3h <= 0:
        raise ValueError("Batch RO recirculation flow per vessel must be positive.")
    q_recirculation_m3h = recirc_per_vessel_m3h * vessels

    reset_time_s = max(0.0, float(_f(raw, "batch_reset_time_s", 10.0)))
    productive_downtime_s = 0.0 if config == "dual_compartment" else reset_time_s
    target_avg_input = _f(raw, "batch_average_product_flow", None)
    operating_flux_input = _f(raw, "batch_operating_flux_lmh", None)
    product_per_cycle_m3 = float(requested_permeate_cycle)
    if target_avg_input not in (None, 0):
        target_average_product_m3h = flow_to_m3h(float(target_avg_input), flow_unit)
        gross_cycle_h = product_per_cycle_m3 / max(target_average_product_m3h, MIN_FLOW)
        productive_h = gross_cycle_h - productive_downtime_s / 3600.0
        if productive_h <= 0:
            raise ValueError(
                "Requested average product flow is incompatible with the batch size and reset time. "
                "Increase batch inventory, reduce reset time, or reduce average production."
            )
        active_permeate_m3h = product_per_cycle_m3 / productive_h
    else:
        active_flux_lmh = float(operating_flux_input if operating_flux_input not in (None, 0) else 14.5)
        if active_flux_lmh <= 0:
            raise ValueError("Batch RO operating flux must be positive.")
        active_permeate_m3h = active_flux_lmh * membrane_area_m2 / 1000.0
        productive_h = product_per_cycle_m3 / max(active_permeate_m3h, MIN_FLOW)
        gross_cycle_h = productive_h + productive_downtime_s / 3600.0
        target_average_product_m3h = product_per_cycle_m3 / max(gross_cycle_h, 1e-12)
    active_flux_lmh = active_permeate_m3h * 1000.0 / membrane_area_m2
    if active_permeate_m3h >= q_recirculation_m3h * 0.90:
        raise ValueError(
            "Requested Batch RO active permeate rate is too large relative to recirculation flow. "
            "Increase recirculation/vessels or lower average product flow."
        )

    suction_pressure_bar = pressure_to_bar(float(_f(raw, "suction_pressure", 2.0)), pressure_unit)
    permeate_pressure_bar = pressure_to_bar(float(_f(raw, "permeate_pressure_1", 0.0)), pressure_unit)
    raw["_batch_suction_pressure_bar"] = suction_pressure_bar
    raw["_batch_permeate_pressure_bar"] = permeate_pressure_bar
    membrane_pressure_limit = min(
        _membrane_pressure_limit_bar(r, temp_c) for r in geometry["records"]
    )
    system_limit_input = _f(raw, "batch_system_pressure_limit", None)
    system_pressure_limit = pressure_to_bar(float(system_limit_input), pressure_unit) if system_limit_input not in (None, 0) else membrane_pressure_limit
    pressure_limit_bar = min(membrane_pressure_limit, system_pressure_limit)
    if pressure_limit_bar <= suction_pressure_bar:
        raise ValueError("Batch RO active pressure limit must exceed the high-pressure pump suction pressure.")

    full_requested = str(raw.get("water_mode", "full") or "full").strip().lower() == "full"
    entered_comp = composition_from_request(raw)
    full_water = full_requested and total_tds_mg_l(entered_comp) > 0
    if full_water:
        _, batch_state = _initial_full_state(raw, temp_c)
        bulk_comp = normalize_composition(batch_state["composition"])
        noncarbonate_mass_g = {k: bulk_comp[k] * initial_inventory_m3 for k in SPECIES if k not in CARBONATE_KEYS}
        initial_water_kg = _water_kg_per_m3(bulk_comp, temp_c) * initial_inventory_m3
        ta_total_mol = float(batch_state["total_alkalinity_mol_kg"]) * initial_water_kg
        ct_total_mol = float(batch_state["total_inorganic_carbon_mol_kg"]) * initial_water_kg
        tds_only_salt_g = None
        bulk_tds = total_tds_mg_l(bulk_comp)
    else:
        feed_tds = _f(raw, "feed_tds", None)
        if feed_tds is None:
            feed_tds = _f(raw, "analysis_tds", None)
        if feed_tds is None:
            feed_tds = total_tds_mg_l(entered_comp)
        bulk_tds = max(0.0, float(feed_tds or 0.0))
        if bulk_tds <= 0:
            raise ValueError("Batch RO requires feed TDS or a Full Water Analysis composition.")
        tds_only_salt_g = bulk_tds * initial_inventory_m3
        batch_state = None
        noncarbonate_mass_g = None
        ta_total_mol = ct_total_mol = None

    hpp_eff = _fraction(_f(raw, "pump_eff", 0.85), 0.85)
    hpp_motor = _fraction(_f(raw, "motor_eff", 0.97), 0.97)
    hpp_vfd = 1.0 if _b(raw, "pump_no_vfd", False) else _fraction(_f(raw, "vfd_eff", 0.97), 0.97)
    circ_eff = _fraction(_f(raw, "batch_circulation_pump_eff", 0.82), 0.82)
    circ_motor = _fraction(_f(raw, "batch_circulation_motor_eff", 0.96), 0.96)
    circ_vfd = 1.0 if _b(raw, "batch_circulation_no_vfd", False) else _fraction(_f(raw, "batch_circulation_vfd_eff", 0.97), 0.97)
    booster_eff = _fraction(_f(raw, "batch_booster_pump_eff", 0.82), 0.82)
    booster_motor = _fraction(_f(raw, "batch_booster_motor_eff", 0.96), 0.96)
    booster_vfd = 1.0 if _b(raw, "batch_booster_no_vfd", False) else _fraction(_f(raw, "batch_booster_vfd_eff", 0.97), 0.97)
    px_eff = _clamp(_fraction(_f(raw, "batch_px_efficiency", 0.96), 0.96), 0.50, 0.9999)
    px_mixing = _clamp(_fraction(_f(raw, "batch_px_mixing", 0.06), 0.06), 0.0, 0.30)
    px_leakage = _clamp(_fraction(_f(raw, "batch_px_leakage", 0.0), 0.0), 0.0, 0.20)
    px_hp_dp_bar = pressure_to_bar(float(_f(raw, "batch_px_hp_dp", 0.6)), pressure_unit)
    px_lp_dp_bar = pressure_to_bar(float(_f(raw, "batch_px_lp_dp", 0.6)), pressure_unit)
    loop_extra_dp_bar = pressure_to_bar(float(_f(raw, "batch_loop_extra_dp", 0.3)), pressure_unit)
    refill_dp_bar = pressure_to_bar(float(_f(raw, "batch_refill_dp", 1.5)), pressure_unit)
    refill_eff = _fraction(_f(raw, "batch_refill_pump_eff", 0.80), 0.80)
    refill_motor = _fraction(_f(raw, "batch_refill_motor_eff", 0.94), 0.94)
    max_flux_lmh = max(1.0, float(_f(raw, "batch_max_flux_lmh", 55.0)))
    stop_on_saturation = _b(raw, "batch_stop_on_saturation", False)
    saturation_limit_pct = max(1.0, float(_f(raw, "batch_saturation_limit_pct", 100.0)))

    steps = int(float(_f(raw, "batch_time_steps", 28)))
    steps = min(max(steps, 8), 80)
    dV_nominal = product_per_cycle_m3 / steps
    volume = initial_inventory_m3
    permeate_volume = 0.0
    time_h = 0.0
    energy_hpp_kwh = energy_circ_kwh = energy_booster_kwh = 0.0
    energy_px_transfer_loss_kwh = 0.0
    composite_perm_tds_mass = 0.0
    composite_perm_species_g = {k: 0.0 for k in SPECIES}
    composite_perm_ta_mol = composite_perm_ct_mol = 0.0
    previous_pressure = None
    last_stage = None
    last_concentrate_state = None
    last_concentrate_tds = None
    profile = []
    warnings: list[str] = []
    limiter = "Target recovery reached"
    limiter_detail = "The requested batch recovery was completed within the configured engineering envelope."
    max_pressure = 0.0
    min_ndp = float("inf")
    peak_flux = 0.0
    peak_cp = 0.0
    max_scaling_pct = None
    limiting_mineral = None
    first_scaling_recovery = None
    first_scaling_mineral = None
    mass_balance_initial_salt_g = bulk_tds * initial_inventory_m3

    chemistry_stride = max(1, int(math.ceil(steps / 12.0)))

    for idx in range(steps):
        remaining_target = product_per_cycle_m3 - permeate_volume
        if remaining_target <= 1e-10:
            break
        dV = min(dV_nominal, remaining_target)
        recovery_before = permeate_volume / initial_inventory_m3

        if full_water:
            effective_state = _blend_carbonate_state(
                batch_state,
                last_concentrate_state,
                px_mixing if config == "atmospheric_px" else 0.0,
                temp_c,
            )
            effective_comp = normalize_composition(effective_state["composition"])
            effective_tds = total_tds_mg_l(effective_comp)
        else:
            effective_state = None
            effective_tds = bulk_tds
            if config == "atmospheric_px" and last_concentrate_tds is not None:
                effective_tds = (1.0 - px_mixing) * bulk_tds + px_mixing * float(last_concentrate_tds)

        stage, status = _solve_pressure_for_permeate(
            active_permeate_m3h,
            data=raw,
            q_feed_m3h=q_recirculation_m3h,
            membrane_id=membrane_id,
            vessels=vessels,
            elements_per_vessel=elements_per_vessel,
            feed_tds=effective_tds,
            temp_c=temp_c,
            feed_state=effective_state,
            full_water=full_water,
            pressure_limit_bar=pressure_limit_bar,
            previous_pressure_bar=previous_pressure,
        )
        if stage is None:
            limiter = "Pressure / membrane productivity limit"
            limiter_detail = str(status.get("detail") or "The requested active permeate rate can no longer be maintained.")
            break
        pressure_bar = float(status["pressure_bar"])
        previous_pressure = pressure_bar
        last_stage = stage
        actual_qp = max(float(stage["permeate_flow"]), MIN_FLOW)
        dt_h = dV / actual_qp
        time_h += dt_h
        max_pressure = max(max_pressure, pressure_bar)
        min_ndp = min(min_ndp, float(stage.get("ndp_bar", 0.0)))
        peak_flux = max(peak_flux, float(stage.get("flux_lmh", 0.0)))
        peak_cp = max(peak_cp, float(stage.get("avg_polarization_factor", 1.0)))

        hpp_flow = actual_qp * (1.0 + (px_leakage if config == "atmospheric_px" else 0.0))
        hpp_kw = _wire_power_kw(hpp_flow, max(0.0, pressure_bar - suction_pressure_bar), hpp_eff, hpp_motor, hpp_vfd)
        circ_dp = max(0.0, float(stage.get("stage_dp_bar", 0.0)) + loop_extra_dp_bar)
        circ_kw = _wire_power_kw(q_recirculation_m3h, circ_dp, circ_eff, circ_motor, circ_vfd)
        booster_kw = 0.0
        px_loss_kw = 0.0
        if config == "atmospheric_px":
            px_flow = max(0.0, q_recirculation_m3h - actual_qp)
            transfer_head_loss = max(0.0, (1.0 - px_eff) * max(pressure_bar - suction_pressure_bar, 0.0))
            transfer_head_loss += px_hp_dp_bar + px_lp_dp_bar
            booster_kw = _wire_power_kw(px_flow, transfer_head_loss, booster_eff, booster_motor, booster_vfd)
            px_loss_kw = px_flow * max(0.0, (1.0 - px_eff) * (pressure_bar - suction_pressure_bar)) / 36.0
        energy_hpp_kwh += hpp_kw * dt_h
        energy_circ_kwh += circ_kw * dt_h
        energy_booster_kwh += booster_kw * dt_h
        energy_px_transfer_loss_kwh += px_loss_kw * dt_h

        perm_tds = float(stage.get("permeate_tds_ppm", 0.0))
        composite_perm_tds_mass += perm_tds * dV
        if full_water:
            perm_comp = normalize_composition(stage.get("permeate_composition_mg_l") or {})
            for k in SPECIES:
                composite_perm_species_g[k] += perm_comp[k] * dV
            perm_water_kg = _water_kg_per_m3(perm_comp, temp_c) * dV
            perm_ta = float(stage.get("permeate_total_alkalinity_mol_kg", 0.0))
            perm_ct = float(stage.get("permeate_total_inorganic_carbon_mol_kg", 0.0))
            composite_perm_ta_mol += perm_ta * perm_water_kg
            composite_perm_ct_mol += perm_ct * perm_water_kg
            for k in SPECIES:
                if k in CARBONATE_KEYS:
                    continue
                noncarbonate_mass_g[k] = max(0.0, noncarbonate_mass_g[k] - perm_comp[k] * dV)
            ta_total_mol -= perm_ta * perm_water_kg
            ct_total_mol = max(0.0, ct_total_mol - perm_ct * perm_water_kg)
        else:
            tds_only_salt_g = max(0.0, tds_only_salt_g - perm_tds * dV)

        volume = max(MIN_VOLUME, volume - dV)
        permeate_volume += dV
        recovery = permeate_volume / initial_inventory_m3
        tank_volume = max(0.0, volume - fixed_inventory_m3)

        if full_water:
            batch_state = _state_from_extensive_carbon(
                noncarbonate_mass_g,
                volume,
                ta_total_mol,
                ct_total_mol,
                temp_c,
                float(batch_state["ph"]),
            )
            bulk_comp = normalize_composition(batch_state["composition"])
            bulk_tds = total_tds_mg_l(bulk_comp)
            conc_state = {
                "composition": normalize_composition(stage.get("concentrate_composition_mg_l") or bulk_comp),
                "ph": float(stage.get("concentrate_ph", batch_state["ph"])),
                "total_alkalinity_mol_kg": float(stage.get("concentrate_total_alkalinity_mol_kg", batch_state["total_alkalinity_mol_kg"])),
                "total_inorganic_carbon_mol_kg": float(stage.get("concentrate_total_inorganic_carbon_mol_kg", batch_state["total_inorganic_carbon_mol_kg"])),
                "total_alkalinity_mg_l_as_hco3": float(stage.get("concentrate_alkalinity_mg_l_as_hco3", batch_state.get("total_alkalinity_mg_l_as_hco3", 0.0))),
            }
            last_concentrate_state = conc_state
            last_concentrate_tds = total_tds_mg_l(conc_state["composition"])
        else:
            bulk_tds = tds_only_salt_g / volume
            last_concentrate_tds = float(stage.get("concentrate_tds_ppm", bulk_tds))

        scaling = {"max_pct": None, "mineral": None}
        if full_water and (idx % chemistry_stride == 0 or idx == steps - 1 or recovery >= target_recovery - 1e-8):
            scaling = _scaling_screen(batch_state, temp_c)
            sat = scaling.get("max_pct")
            if sat is not None and math.isfinite(float(sat)):
                sat = float(sat)
                if max_scaling_pct is None or sat > max_scaling_pct:
                    max_scaling_pct = sat
                    limiting_mineral = scaling.get("mineral")
                if sat >= saturation_limit_pct and first_scaling_recovery is None:
                    first_scaling_recovery = recovery
                    first_scaling_mineral = scaling.get("mineral")
                if stop_on_saturation and sat >= saturation_limit_pct:
                    limiter = "Mineral saturation limit"
                    limiter_detail = f"{scaling.get('mineral') or 'A mineral'} reached {sat:.1f}% of the configured concentration-saturation limit."

        profile.append({
            "step": idx + 1,
            "time_min": time_h * 60.0,
            "recovery": recovery,
            "inventory_m3": volume,
            "tank_volume_m3": tank_volume,
            "feed_tds_mg_l": effective_tds,
            "bulk_tds_mg_l": bulk_tds,
            "feed_osmotic_bar": float(stage.get("feed_osmotic_bar", 0.0)),
            "concentrate_osmotic_bar": float(stage.get("concentrate_osmotic_bar", 0.0)),
            "feed_pressure_bar": pressure_bar,
            "reject_pressure_bar": float(stage.get("reject_pressure_bar", pressure_bar)),
            "stage_dp_bar": float(stage.get("stage_dp_bar", 0.0)),
            "ndp_bar": float(stage.get("ndp_bar", 0.0)),
            "permeate_tds_mg_l": perm_tds,
            "concentrate_tds_mg_l": float(stage.get("concentrate_tds_ppm", bulk_tds)),
            "flux_lmh": float(stage.get("flux_lmh", 0.0)),
            "per_pass_recovery": float(stage.get("recovery", 0.0)),
            "polarization_factor": float(stage.get("avg_polarization_factor", 1.0)),
            "highest_mineral_saturation_pct": scaling.get("max_pct"),
            "limiting_mineral": scaling.get("mineral"),
            "hpp_kw": hpp_kw,
            "recirculation_kw": circ_kw,
            "booster_kw": booster_kw,
            "px_transfer_loss_kw": px_loss_kw,
        })
        if stop_on_saturation and limiter == "Mineral saturation limit":
            break
        if tank_volume + 1e-8 < final_tank_volume_m3:
            limiter = "Minimum tank volume"
            limiter_detail = "The calculated tank liquid volume reached the configured end-of-cycle minimum."
            break

    if permeate_volume <= 0 or last_stage is None:
        raise ValueError(limiter_detail)

    achieved_recovery = permeate_volume / initial_inventory_m3
    productive_time_s = time_h * 3600.0
    effective_reset_s = productive_downtime_s
    cycle_time_s = productive_time_s + effective_reset_s
    duty_factor = productive_time_s / max(cycle_time_s, 1e-12)
    average_product_m3h = permeate_volume / max(cycle_time_s / 3600.0, 1e-12)
    effective_flux_lmh = active_flux_lmh * duty_factor

    # Reset/refill energy is cycle energy, not instantaneous productive power.
    refill_volume_m3 = initial_inventory_m3 if config != "dual_compartment" else max(0.0, permeate_volume)
    reset_energy_kwh = refill_volume_m3 * max(refill_dp_bar, 0.0) * KWH_PER_M3_BAR / max(refill_eff * refill_motor, 1e-12)
    if config == "dual_compartment":
        # Purge/refill overlaps production but still consumes low-pressure work.
        reset_energy_kwh *= 1.0
    ro_cycle_energy_kwh = energy_hpp_kwh + energy_circ_kwh + energy_booster_kwh + reset_energy_kwh
    ro_sec = ro_cycle_energy_kwh / permeate_volume

    pretreat_p = pressure_to_bar(float(_f(raw, "pretreatment_discharge_pressure", 6.0)), pressure_unit)
    pretreat_rec = _clamp(_fraction(_f(raw, "pretreatment_recovery", 0.85), 0.85), 0.01, 1.0)
    pretreat_eff = _fraction(_f(raw, "pretreatment_pump_eff", 0.82), 0.82)
    pretreat_motor = _fraction(_f(raw, "pretreatment_motor_eff", 0.95), 0.95)
    pretreat_vfd = 1.0 if _b(raw, "pretreatment_no_vfd", False) else _fraction(_f(raw, "pretreatment_vfd_eff", 0.97), 0.97)
    pretreatment_sec = max(0.0, pretreat_p) / 36.0 / max(pretreat_rec * pretreat_eff * pretreat_motor * pretreat_vfd, 1e-12)
    total_sec = ro_sec + pretreatment_sec

    final_tds = bulk_tds
    composite_perm_tds = composite_perm_tds_mass / permeate_volume
    final_comp = normalize_composition(batch_state["composition"]) if full_water else None
    composite_perm_comp = None
    composite_perm_ph = None
    if full_water:
        composite_perm_comp = {k: composite_perm_species_g[k] / permeate_volume for k in SPECIES}
        # Reconstruct the flow-weighted composite permeate carbonate state from
        # extensive TA/CT to avoid averaging pH directly.
        perm_water_kg = _water_kg_per_m3(composite_perm_comp, temp_c) * permeate_volume
        composite_ta = composite_perm_ta_mol / max(perm_water_kg, 1e-12)
        composite_ct = composite_perm_ct_mol / max(perm_water_kg, 1e-12)
        base = dict(composite_perm_comp)
        base["bicarbonate"] = 0.0
        base["carbonate"] = 0.0
        try:
            composite_state = solve_carbonate_state(base, temp_c, total_alkalinity_mol_kg=composite_ta, total_inorganic_carbon_mol_kg=composite_ct)
            composite_perm_comp = normalize_composition(composite_state["composition"])
            composite_perm_ph = float(composite_state["ph"])
            composite_perm_tds = total_tds_mg_l(composite_perm_comp)
        except Exception:
            composite_state = None

    final_scaling = _scaling_screen(batch_state, temp_c) if full_water else {"max_pct": None, "mineral": None}
    if full_water and final_scaling.get("max_pct") is not None:
        sat = float(final_scaling["max_pct"])
        if max_scaling_pct is None or sat > max_scaling_pct:
            max_scaling_pct = sat
            limiting_mineral = final_scaling.get("mineral")

    final_salt_g = final_tds * (initial_inventory_m3 - permeate_volume)
    permeate_salt_g = composite_perm_tds * permeate_volume
    salt_balance_residual_pct = 100.0 * (mass_balance_initial_salt_g - final_salt_g - permeate_salt_g) / max(mass_balance_initial_salt_g, 1e-12)

    external_pct_elements = 100.0 * (piping_volume_m3 + final_tank_volume_m3) / element_volume_m3
    reset_fraction = effective_reset_s / max(cycle_time_s, 1e-12)
    pressure_utilization = 100.0 * max_pressure / max(pressure_limit_bar, 1e-12)
    dp_utilization = 100.0 * float(last_stage.get("dp_limit_fraction", 0.0))

    if external_pct_elements > 20.0:
        warnings.append(
            f"End-of-cycle external liquid volume is {external_pct_elements:.1f}% of membrane-channel volume; low external volume is preferred for Batch RO energy performance."
        )
    if final_tank_volume_m3 > 0.02 * element_volume_m3:
        warnings.append("A non-zero end-of-cycle tank heel is configured; this increases the minimum retained batch inventory.")
    if reset_fraction > 0.15 and config != "dual_compartment":
        warnings.append(f"Reset/purge downtime is {100*reset_fraction:.1f}% of the full cycle and materially reduces effective flux/productivity.")
    if active_flux_lmh > max_flux_lmh:
        warnings.append(f"Required active flux is {active_flux_lmh:.1f} LMH, above the configured {max_flux_lmh:.1f} LMH review limit.")
    if pressure_utilization > 90.0:
        warnings.append(f"Peak Batch RO pressure uses {pressure_utilization:.1f}% of the active membrane/equipment pressure envelope.")
    if dp_utilization > 100.0:
        warnings.append("Calculated membrane-element pressure drop exceeds at least one selected membrane datasheet limit.")
    if max_scaling_pct is not None and max_scaling_pct >= saturation_limit_pct:
        warnings.append(
            f"Bulk Batch RO chemistry reaches {max_scaling_pct:.1f}% concentration saturation for {limiting_mineral or 'the limiting mineral'}; review pretreatment/antiscalant and kinetic residence time separately."
        )
    if abs(salt_balance_residual_pct) > 0.25:
        warnings.append(f"Cycle TDS mass-balance residual is {salt_balance_residual_pct:.3f}%; review the selected high-salinity property basis.")
    if config == "dual_compartment":
        warnings.append("Dual-compartment mode treats switching/purge as overlapping production; valve transients and divider leakage are equipment-design checks outside this calculation.")
    if config == "atmospheric_px" and px_mixing > 0:
        warnings.append(f"PX mixing is included as a {100*px_mixing:.1f}% high-/low-pressure stream concentration blend in the instantaneous membrane feed state.")

    reference_sec = _f(raw, "batch_reference_ro_sec", None)
    energy_saving_pct = None
    if reference_sec not in (None, 0):
        energy_saving_pct = 100.0 * (float(reference_sec) - ro_sec) / float(reference_sec)

    result: dict[str, Any] = {
        "batch_ro": True,
        "batch_ro_version": "0.1.0",
        "technology": "Batch RO",
        "batch_configuration": config,
        "batch_configuration_label": _configuration_label(config),
        "recovery": achieved_recovery,
        "target_recovery": target_recovery,
        "product_flow": flow_from_m3h(average_product_m3h, flow_unit),
        "feed_flow": flow_from_m3h(average_product_m3h / max(achieved_recovery, 1e-12), flow_unit),
        "ro_sec": ro_sec,
        "pretreatment_sec": pretreatment_sec,
        "total_sec": total_sec,
        "flow_unit": flow_unit,
        "pressure_unit": pressure_unit,
        "batch_ro_target_recovery_pct": target_recovery_pct,
        "batch_ro_achieved_recovery_pct": 100.0 * achieved_recovery,
        "batch_ro_recovery_limiter": limiter,
        "batch_ro_recovery_limiter_detail": limiter_detail,
        "batch_ro_initial_inventory_m3": initial_inventory_m3,
        "batch_ro_initial_tank_volume_m3": initial_tank_volume_m3,
        "batch_ro_final_tank_volume_m3": max(0.0, initial_inventory_m3 - permeate_volume - fixed_inventory_m3),
        "batch_ro_membrane_channel_volume_m3": element_volume_m3,
        "batch_ro_piping_external_volume_m3": piping_volume_m3,
        "batch_ro_external_volume_pct_elements": external_pct_elements,
        "batch_ro_permeate_volume_per_cycle_m3": permeate_volume,
        "batch_ro_final_brine_inventory_m3": initial_inventory_m3 - permeate_volume,
        "batch_ro_productive_time_s": productive_time_s,
        "batch_ro_reset_time_s": reset_time_s,
        "batch_ro_effective_reset_downtime_s": effective_reset_s,
        "batch_ro_cycle_time_s": cycle_time_s,
        "batch_ro_duty_factor": duty_factor,
        "batch_ro_active_permeate_flow_m3h": active_permeate_m3h,
        "batch_ro_average_product_flow_m3h": average_product_m3h,
        "batch_ro_recirculation_flow_m3h": q_recirculation_m3h,
        "batch_ro_recirculation_flow_per_vessel_m3h": recirc_per_vessel_m3h,
        "batch_ro_active_flux_lmh": active_flux_lmh,
        "batch_ro_effective_flux_lmh": effective_flux_lmh,
        "batch_ro_peak_flux_lmh": peak_flux,
        "batch_ro_peak_polarization_factor": peak_cp,
        "batch_ro_peak_pressure_bar": max_pressure,
        "batch_ro_pressure_limit_bar": pressure_limit_bar,
        "batch_ro_membrane_pressure_limit_bar": membrane_pressure_limit,
        "batch_ro_system_pressure_limit_bar": system_pressure_limit,
        "batch_ro_pressure_utilization_pct": pressure_utilization,
        "batch_ro_minimum_ndp_bar": (0.0 if not math.isfinite(min_ndp) else min_ndp),
        "batch_ro_final_bulk_tds_mg_l": final_tds,
        "batch_ro_composite_permeate_tds_mg_l": composite_perm_tds,
        "batch_ro_final_bulk_composition_mg_l": final_comp,
        "batch_ro_composite_permeate_composition_mg_l": composite_perm_comp,
        "batch_ro_final_bulk_ph": (float(batch_state["ph"]) if full_water else None),
        "batch_ro_composite_permeate_ph": composite_perm_ph,
        "batch_ro_highest_mineral_saturation_pct": max_scaling_pct,
        "batch_ro_limiting_mineral": limiting_mineral,
        "batch_ro_first_scaling_onset_recovery": first_scaling_recovery,
        "batch_ro_first_scaling_onset_mineral": first_scaling_mineral,
        "batch_ro_hpp_energy_kwh_cycle": energy_hpp_kwh,
        "batch_ro_circulation_energy_kwh_cycle": energy_circ_kwh,
        "batch_ro_px_booster_energy_kwh_cycle": energy_booster_kwh,
        "batch_ro_px_transfer_loss_kwh_cycle": energy_px_transfer_loss_kwh,
        "batch_ro_refill_energy_kwh_cycle": reset_energy_kwh,
        "batch_ro_total_ro_energy_kwh_cycle": ro_cycle_energy_kwh,
        "batch_ro_salt_balance_residual_pct": salt_balance_residual_pct,
        "batch_ro_energy_saving_vs_reference_pct": energy_saving_pct,
        "batch_ro_cycle_profile": profile,
        "batch_ro_warnings": warnings,
        "batch_ro_model_basis": (
            "Transient fully-batch inventory with a converged quasi-steady Total RO Design membrane solve at each recovery increment; "
            "variable pressure, solution-diffusion salt passage, concentration polarization, element pressure drop, full-ion osmotic pressure, "
            "TA/CT conservation, scaling screening, pump/PX losses, explicit external volume and reset duty cycle."
        ),
        "batch_ro_model_limitations": (
            "External piping is represented as explicit retained liquid inventory, not CFD/1-D axial dispersion. "
            "Bulk thermodynamic saturation is not an antiscalant kinetic guarantee. Equipment valve/divider transients are not sized."
        ),
    }

    # Reuse the same stage result naming expected by the mature Total RO Design
    # results components. The accepted final/limiting instantaneous membrane
    # state is exposed as Stage 1; the complete transient remains in cycle_profile.
    _attach_membrane(result, last_stage, "stage1_")
    result["stage1_feed_tds"] = float(last_stage.get("feed_tds_ppm", final_tds))
    result["stage1_permeate_tds"] = float(last_stage.get("permeate_tds_ppm", composite_perm_tds))
    result["stage1_reject_tds"] = float(last_stage.get("concentrate_tds_ppm", final_tds))
    result["stage1_feed_pressure"] = pressure_from_bar(float(profile[-1]["feed_pressure_bar"]), pressure_unit)
    result["stage1_reject_pressure"] = pressure_from_bar(float(profile[-1]["reject_pressure_bar"]), pressure_unit)
    result["stage1_dp"] = pressure_from_bar(float(profile[-1]["stage_dp_bar"]), pressure_unit)
    result["stage1_feed_flow"] = flow_from_m3h(q_recirculation_m3h, flow_unit)
    result["stage1_product_flow"] = flow_from_m3h(float(last_stage.get("permeate_flow", active_permeate_m3h)), flow_unit)
    result["stage1_reject_flow"] = flow_from_m3h(float(last_stage.get("reject_flow", q_recirculation_m3h-active_permeate_m3h)), flow_unit)
    return result
