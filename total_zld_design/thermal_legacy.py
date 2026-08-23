"""Cell-faithful extraction of the Total_MZLD_Design seed workbook.

This module intentionally reproduces workbook behavior, including its known limitations.
It is a regression model, not a claim that the underlying thermal/crystallization physics
has been validated.
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from .defaults import thermal_defaults
from .models import CalculationResult, Stream, WarningMessage


def _merge(base: dict[str, Any], patch: dict[str, Any] | None) -> dict[str, Any]:
    out = deepcopy(base)
    if not patch:
        return out
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def bpe_c(tds_mg_l: float) -> float:
    x = tds_mg_l / 10000.0
    if x >= 100.0:
        raise ValueError("TDS produces invalid workbook wt% basis (>=100%).")
    molality = (10.0 * x / 58.44) / (1.0 - x / 100.0)
    return 1.8 * 0.512 * molality


def density_kg_m3(tds_mg_l: float) -> float:
    return 1000.0 + 0.75 * (tds_mg_l / 1000.0)


def viscosity_mpa_s(tds_mg_l: float) -> float:
    x = tds_mg_l / 10000.0
    return 0.89 * (1.0 + 0.03 * x)


def calculate_thermal_legacy(inputs: dict[str, Any] | None = None) -> CalculationResult:
    p = _merge(thermal_defaults(), inputs)

    q_feed = float(p["feed_flow_m3_h"])
    tds_feed = float(p["feed_tds_mg_l"])
    t_feed = float(p["feed_temperature_c"])
    bc_tds = float(p["bc_concentrate_tds_mg_l"])
    vffe_tds = float(p["vffe_concentrate_tds_mg_l"])
    sat_tds = float(p["nacl_saturation_mg_l"])
    target_recovery = float(p["target_overall_recovery"])

    if min(q_feed, tds_feed, bc_tds, vffe_tds, sat_tds) <= 0:
        raise ValueError("Flow and TDS inputs must be positive.")

    species_sum = sum(float(v) for v in p.get("species_mg_l", {}).values())
    species_gap_fraction = (species_sum - tds_feed) / tds_feed if tds_feed else 0.0

    props = {
        "bc": {
            "temperature_basis_c": t_feed + 8.0,
            "tds_mg_l": bc_tds,
            "wt_percent_proxy": bc_tds / 10000.0,
            "bpe_c": bpe_c(bc_tds),
            "density_kg_m3": density_kg_m3(bc_tds),
            "viscosity_mpa_s": viscosity_mpa_s(bc_tds),
        },
        "vffe": {
            "temperature_basis_c": t_feed + 10.0,
            "tds_mg_l": vffe_tds,
            "wt_percent_proxy": vffe_tds / 10000.0,
            "bpe_c": bpe_c(vffe_tds),
            "density_kg_m3": density_kg_m3(vffe_tds),
            "viscosity_mpa_s": viscosity_mpa_s(vffe_tds),
        },
        "nacl_saturation_reference": {
            "temperature_basis_c": t_feed + 12.0,
            "tds_mg_l": sat_tds,
            "wt_percent_proxy": sat_tds / 10000.0,
            "bpe_c": bpe_c(sat_tds),
            "density_kg_m3": density_kg_m3(sat_tds),
            "viscosity_mpa_s": viscosity_mpa_s(sat_tds),
        },
    }

    # Brine concentrator / MVR seed model
    bc = p["bc"]
    q_bc_conc = q_feed * tds_feed / bc_tds
    q_bc_dist = q_feed - q_bc_conc
    bc_recovery = q_bc_dist / q_feed
    compression_head_c = props["bc"]["bpe_c"] + float(bc["compressor_approach_dt_c"]) + 1.0
    specific_work_kwh_m3 = (
        float(bc["latent_heat_kj_kg"])
        * 0.0025
        * compression_head_c
        / float(bc["compressor_isentropic_efficiency"])
    )
    compressor_kw = specific_work_kwh_m3 * q_bc_dist
    recirc_flow_m3_h = q_feed * float(bc["seed_to_feed_recirculation_ratio"])
    recirc_pump_kw = (
        recirc_flow_m3_h
        * props["bc"]["density_kg_m3"]
        / 1000.0
        * 9.81
        * float(bc["recirculation_head_m"])
        / 3600.0
        / float(bc["pump_efficiency"])
    )
    bc_power_kw = compressor_kw + recirc_pump_kw

    bc_result = {
        "feed_m3_h": q_feed,
        "concentrate_m3_h": q_bc_conc,
        "distillate_m3_h": q_bc_dist,
        "recovery": bc_recovery,
        "bpe_c": props["bc"]["bpe_c"],
        "compression_head_c": compression_head_c,
        "specific_compression_work_kwh_m3_distillate": specific_work_kwh_m3,
        "compressor_power_kw": compressor_kw,
        "recirculation_flow_m3_h": recirc_flow_m3_h,
        "recirculation_pump_kw": recirc_pump_kw,
        "total_power_kw": bc_power_kw,
        "model_status": "screening / workbook-regression",
    }

    # VFFE heat transfer seed model
    vf = p["vffe"]
    q_vffe_feed = q_bc_conc
    q_vffe_conc = q_vffe_feed * bc_tds / vffe_tds
    q_vffe_dist = q_vffe_feed - q_vffe_conc
    effects = int(vf["effects"])
    evap_per_effect_m3_h = q_vffe_dist / effects if effects else 0.0
    wetted_perimeter_m = math.pi * float(vf["tube_od_m"]) * int(vf["tubes_per_effect"])
    gamma_kg_m_s = (q_vffe_feed * props["bc"]["density_kg_m3"] / 3600.0) / wetted_perimeter_m
    mu_mpa_s = props["vffe"]["viscosity_mpa_s"]
    film_re = 4.0 * gamma_kg_m_s / (mu_mpa_s / 1000.0)
    kfilm = float(vf["film_thermal_conductivity_w_m_k"])
    film_htc = (
        1.88
        * film_re ** (-0.22)
        * kfilm
        * (9.81 / ((mu_mpa_s / 1000.0 / props["bc"]["density_kg_m3"]) ** 2.0)) ** (1.0 / 3.0)
    )
    fan_pressure_kpa = (
        float(vf["single_fan_static_pressure_kpa"]) * int(vf["fans_in_series"])
        if "Series" in str(vf["ncg_fan_configuration"])
        else float(vf["single_fan_static_pressure_kpa"])
    )

    # Reproduce the workbook's fixed four displayed effect rows exactly.
    effect_rows = []
    bpe_lo = props["bc"]["bpe_c"]
    bpe_hi = props["vffe"]["bpe_c"]
    steam_temp = float(vf["live_steam_temperature_c"])
    for idx in range(4):
        bpe = bpe_lo + idx / 3.0 * (bpe_hi - bpe_lo)
        boiling_temp = steam_temp - bpe
        next_steam = bpe if idx < 3 else None
        temp_drop_to_next = steam_temp - next_steam if idx < 3 else None
        effect_rows.append({
            "effect": idx + 1,
            "steam_or_vapor_temperature_c": steam_temp,
            "bpe_c": bpe,
            "boiling_temperature_c": boiling_temp,
            "temperature_drop_to_next_c": temp_drop_to_next,
        })
        if idx < 3:
            # Workbook mapping: the next effect's steam/vapor temperature equals
            # the current effect BPE (e.g. C7=D6, C8=D7, C9=D8).
            steam_temp = bpe

    steam_economy = effects * 0.85
    vffe_live_steam_t_h = q_vffe_dist / steam_economy if steam_economy else 0.0
    vffe_thermal_duty_kw = vffe_live_steam_t_h * 1000.0 * float(vf["live_steam_latent_heat_kj_kg"]) / 3600.0

    vffe_result = {
        "feed_m3_h": q_vffe_feed,
        "concentrate_m3_h": q_vffe_conc,
        "distillate_m3_h": q_vffe_dist,
        "evaporation_per_effect_m3_h": evap_per_effect_m3_h,
        "wetted_perimeter_m": wetted_perimeter_m,
        "film_loading_kg_m_s": gamma_kg_m_s,
        "film_reynolds": film_re,
        "film_htc_w_m2_k": film_htc,
        "ncg_total_static_pressure_kpa": fan_pressure_kpa,
        "effect_temperature_rows": effect_rows,
        "steam_economy_kg_distillate_per_kg_steam": steam_economy,
        "live_steam_t_h": vffe_live_steam_t_h,
        "thermal_duty_kw": vffe_thermal_duty_kw,
        "model_status": "screening / workbook-regression",
    }

    # FCC seed model
    fcc = p["fcc"]
    supersaturation = (vffe_tds - sat_tds) / sat_tds
    growth_mm_h = float(fcc["growth_coefficient_m_s"]) * supersaturation ** float(fcc["growth_exponent"]) * 1000.0 * 3600.0
    nucleation_rate = (
        float(fcc["nucleation_coefficient"])
        * float(fcc["magma_density_kg_m3"]) ** float(fcc["nucleation_magma_exponent"])
        * supersaturation ** float(fcc["nucleation_supersaturation_exponent"])
    )
    dominant_crystal_size_mm = 3.0 * growth_mm_h * float(fcc["residence_time_h"])
    q_fcc_feed = q_vffe_conc
    q_fcc_evap = q_fcc_feed * float(fcc["evaporation_fraction"])
    q_mother = q_fcc_feed - q_fcc_evap
    dry_salt_t_h = (q_fcc_feed * vffe_tds - q_mother * sat_tds) / 1_000_000.0

    fcc_result = {
        "feed_m3_h": q_fcc_feed,
        "relative_supersaturation": supersaturation,
        "growth_rate_mm_h": growth_mm_h,
        "nucleation_rate_normalized_per_m3_s": nucleation_rate,
        "dominant_crystal_size_mm": dominant_crystal_size_mm,
        "coefficient_of_variation": 0.5,
        "evaporation_m3_h": q_fcc_evap,
        "dry_salt_t_h": dry_salt_t_h,
        "mother_liquor_m3_h": q_mother,
        "model_status": "placeholder kinetics / pseudo-salt workbook-regression",
    }

    # Crude workbook equipment screening.
    screening = p["screening"]
    caso4_screen_mg_l = float(p["species_mg_l"].get("SO4", 0.0)) * (bc_tds / tds_feed) * 1.7
    caso4_ratio = caso4_screen_mg_l / float(screening["caso4_solubility_limit_mg_l_as_caso4"])
    hx_recommendation = "Plate & Frame (alt.)" if caso4_ratio < 0.8 else "Shell & Tube"

    # Utility rollup and screening economics.
    total_power_kw = bc_power_kw + float(screening["vffe_electric_kw"]) + float(screening["fcc_electric_kw"])
    total_live_steam_t_h = vffe_live_steam_t_h + float(screening["fcc_live_steam_t_h"])
    total_cooling_m3_h = (
        float(screening["bc_cooling_water_m3_h"])
        + float(screening["vffe_cooling_water_m3_h"])
        + float(screening["fcc_cooling_water_m3_h"])
    )
    total_recovered_m3_h = q_bc_dist + q_vffe_dist + q_fcc_evap
    overall_recovery = total_recovered_m3_h / q_feed
    recovery_gap = overall_recovery - target_recovery

    bc_capex = q_bc_dist * float(screening["bc_capex_usd_per_m3_h_distillate"])
    vffe_capex = q_vffe_dist * float(screening["vffe_capex_usd_per_m3_h_distillate"])
    fcc_capex = dry_salt_t_h * float(screening["fcc_capex_usd_per_t_h_salt"])
    bop = float(screening["bop_fraction"]) * (bc_capex + vffe_capex + fcc_capex)
    capex = bc_capex + vffe_capex + fcc_capex + bop

    warnings: list[WarningMessage] = []
    if abs(species_gap_fraction) > 0.05:
        warnings.append(WarningMessage(
            "CHEM-001", "warning", "Ion sum differs from stated TDS",
            f"Entered species sum differs from TDS by {species_gap_fraction * 100:.2f}%. Workbook screening guidance is approximately ±5%.",
        ))
    if film_re > 1800:
        warnings.append(WarningMessage(
            "VFFE-RE-001", "warning", "Falling-film correlation outside stated regime",
            f"Film Reynolds number is {film_re:.1f}; the workbook note gives a typical laminar-wavy range of about 30–1800.",
        ))
    if any(r["boiling_temperature_c"] < 0 for r in effect_rows[1:]):
        warnings.append(WarningMessage(
            "VFFE-T-001", "critical", "Nonphysical VFFE effect temperature chain preserved",
            "The source workbook sets downstream vapor temperature from the previous effect BPE; negative downstream boiling temperatures result. This is preserved only for regression and must be replaced before production validation.",
        ))
    if effects != 4:
        warnings.append(WarningMessage(
            "VFFE-EFF-001", "warning", "Effect table is a four-row workbook regression",
            "The source workbook's detailed temperature table is hard-coded to four effect rows even when the effect-count input changes.",
        ))
    if supersaturation > 0.05:
        warnings.append(WarningMessage(
            "FCC-S-001", "warning", "FCC supersaturation above workbook metastable-zone note",
            f"Relative supersaturation is {supersaturation:.4f}; the workbook notes a typical controlled target around 0.01–0.05.",
        ))
    warnings.append(WarningMessage(
        "FCC-RECYCLE-001", "critical", "Mother-liquor recycle is not closed",
        "The workbook labels the mother liquor as recycle but does not converge it back to the crystallizer feed. Overall recovery therefore does not represent a closed ZLD boundary.",
    ))
    warnings.append(WarningMessage(
        "THERMO-001", "critical", "High-molality thermal chemistry is not yet validated",
        "BPE, density, viscosity, saturation and precipitation in the seed workbook are simplified. Do not present this path as final equipment design physics.",
    ))
    warnings.append(WarningMessage(
        "ECON-001", "info", "CAPEX is screening only",
        "Package unit factors and BOP are source-workbook Class 4/5 screening assumptions, not vendor quotations or Total Water Economics output.",
    ))

    summary = {
        "feed_flow_m3_h": q_feed,
        "total_recovered_water_m3_h": total_recovered_m3_h,
        "overall_recovery": overall_recovery,
        "target_recovery": target_recovery,
        "recovery_gap": recovery_gap,
        "total_electrical_power_kw": total_power_kw,
        "total_live_steam_t_h": total_live_steam_t_h,
        "total_cooling_service_water_m3_h": total_cooling_m3_h,
        "dry_salt_t_h": dry_salt_t_h,
        "screening_capex_usd": capex,
        "species_sum_mg_l": species_sum,
        "species_tds_gap_fraction": species_gap_fraction,
    }

    streams = [
        Stream("ZLD feed", q_feed, tds_feed, t_feed, phase="liquid"),
        Stream("BC distillate", q_bc_dist, 0.0, phase="liquid", note="Workbook assumes zero TDS"),
        Stream("BC concentrate / VFFE feed", q_bc_conc, bc_tds, phase="liquid"),
        Stream("VFFE distillate", q_vffe_dist, 0.0, phase="liquid", note="Workbook assumes zero TDS"),
        Stream("VFFE concentrate / FCC feed", q_vffe_conc, vffe_tds, phase="liquid"),
        Stream("FCC vapor / recovered water", q_fcc_evap, 0.0, phase="vapor"),
        Stream("FCC mother liquor (unclosed recycle)", q_mother, sat_tds, phase="liquid"),
        Stream("Dry salt (pseudo-TDS)", None, None, solids_t_h=dry_salt_t_h, phase="solid"),
    ]

    modules = {
        "properties": props,
        "brine_concentrator": bc_result,
        "vffe": vffe_result,
        "fcc": fcc_result,
        "equipment_screen": {
            "caso4_screen_mg_l_as_caso4": caso4_screen_mg_l,
            "caso4_solubility_ratio": caso4_ratio,
            "heat_exchanger_recommendation": hx_recommendation,
            "ncg_fan_configuration": vf["ncg_fan_configuration"],
        },
        "utilities": {
            "total_electrical_power_kw": total_power_kw,
            "total_live_steam_t_h": total_live_steam_t_h,
            "total_cooling_service_water_m3_h": total_cooling_m3_h,
        },
        "economics_screening": {
            "bc_package_usd": bc_capex,
            "vffe_package_usd": vffe_capex,
            "fcc_package_usd": fcc_capex,
            "bop_usd": bop,
            "total_usd": capex,
            "model_status": "Class 4/5 screening assumptions from workbook",
        },
    }

    return CalculationResult(
        mode="thermal_legacy",
        model_status="workbook-regression / screening",
        model_version="0.1.0",
        inputs=p,
        summary=summary,
        modules=modules,
        streams=streams,
        warnings=warnings,
        provenance={
            "source_workbook": "Total_MZLD_Design(1).xlsx",
            "source_role": "engineering seed/screening model",
            "runtime_spreadsheet_dependency": False,
        },
    )
