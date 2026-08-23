"""FO staged-transport extraction from the saved FO sizing workbook.

The transport solver is active Python code. Feed osmotic pressure is currently interpolated
from the saved workbook's Pitzer table for its saved feed chemistry. Therefore this is a
useful workbook-regression module and transport sandbox, not yet a general arbitrary-feed
chemistry engine.
"""

from __future__ import annotations

import bisect
import math
from copy import deepcopy
from typing import Any

from .defaults import fo_defaults
from .models import CalculationResult, Stream, WarningMessage

# Saved-workbook OSMOTIC sheet lookup (CF -> bar) for the source feed chemistry.
_FEED_CF = [0.001, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]
_FEED_PI_BAR = [
    0.027669446674601,
    25.5165441978753,
    32.1091874998032,
    38.8291871527181,
    45.6861514432451,
    52.6885866484537,
    67.1596113304871,
    82.2946852862469,
    98.136633047699,
    114.720651771267,
    150.226545667901,
    188.99280274999,
]

# Saved-workbook DRAW sheet lookup for NaCl (molality -> bar).
_DRAW_M = [0.001, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]
_DRAW_PI_BAR = [
    0.0488593501706457,
    11.3865148882884,
    22.7689224753232,
    34.3752498527807,
    46.2634802494524,
    58.4724242445506,
    71.0333449655694,
    97.31410641715,
    125.281515534755,
    155.075029143682,
    186.80942833265,
    220.582159148697,
    294.57367451959,
    377.634813292819,
]


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


def _interp_clamped(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect.bisect_right(xs, x) - 1
    x0, x1 = xs[i], xs[i + 1]
    y0, y1 = ys[i], ys[i + 1]
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def calculate_fo_regression(inputs: dict[str, Any] | None = None) -> CalculationResult:
    p = _merge(fo_defaults(), inputs)
    if str(p.get("draw_solute", "NaCl")) != "NaCl":
        raise ValueError("v0.1 FO regression currently implements the saved-workbook NaCl draw path only.")

    A = float(p["water_permeability_lmh_bar"])
    B = float(p["salt_permeability_lmh"])
    S_um = float(p["structural_parameter_um"])
    D = float(p["draw_diffusivity_m2_s"])
    dh_m = float(p["feed_channel_hydraulic_diameter_mm"]) / 1000.0
    velocity = float(p["feed_crossflow_velocity_m_s"])
    nu = float(p["kinematic_viscosity_m2_s"])
    sh_a = float(p["sherwood_coefficient"])
    sh_b = float(p["sherwood_re_exponent"])
    sh_c = float(p["sherwood_sc_exponent"])
    area_total = float(p["membrane_area_m2"])
    feed0 = float(p["feed_flow_m3_h"])
    draw0 = float(p["draw_flow_m3_h"])
    draw_m0 = float(p["draw_inlet_molality"])
    mw = float(p["draw_molar_mass_g_mol"])
    feed_draw_m = float(p["draw_solute_already_in_feed_mol_kg"])
    stages = int(p["stages"])
    refinements = int(p["bisection_refinements"])

    if min(A, D, dh_m, nu, area_total, feed0, draw0, stages, refinements) <= 0:
        raise ValueError("FO transport inputs must be positive (B may be zero).")
    if stages != 10:
        raise ValueError("v0.1 regression is fixed to the source workbook's 10 equal-area stages.")

    re = velocity * dh_m / nu
    sc = nu / D
    sh = sh_a * re ** sh_b * sc ** sh_c
    k_m_s = sh * D / dh_m
    k_lmh = k_m_s * 3600.0 * 1000.0
    resistivity_s_m = (S_um / 1_000_000.0) / D
    K_lmh = 1.0 / (resistivity_s_m / 3600.0 / 1000.0)
    area_stage = area_total / stages

    def residual(j: float, pi_draw: float, pi_feed: float) -> float:
        jj = max(j, 1e-9)
        ecp = math.exp(jj / k_lmh)
        icp = math.exp(-jj / K_lmh)
        denom = 1.0 + (B / jj) * (ecp - icp)
        return A * (pi_draw * icp - pi_feed * ecp) / denom - j

    def solve_flux(pi_draw: float, pi_feed: float) -> float:
        lo = 0.0
        hi = max(A * pi_draw, 0.001)
        # The workbook has 17 lo/hi refinement pairs, then reports their midpoint.
        for _ in range(refinements):
            mid = (lo + hi) / 2.0
            if residual(mid, pi_draw, pi_feed) > 0.0:
                lo = mid
            else:
                hi = mid
        return max(0.0, (lo + hi) / 2.0)

    feed_flow = feed0
    draw_flow = draw0
    cumulative_salt_loss = 0.0
    stage_rows = []

    for i in range(stages):
        feed_cf = feed0 / max(feed_flow, 1e-9)
        pi_feed = _interp_clamped(feed_cf, _FEED_CF, _FEED_PI_BAR)

        if i == 0:
            draw_m = draw_m0
        else:
            draw_m = max(
                0.0,
                (draw_m0 * draw0 - cumulative_salt_loss / mw) / max(draw_flow, 1e-9),
            )
        pi_draw = _interp_clamped(draw_m, _DRAW_M, _DRAW_PI_BAR)
        jw = solve_flux(pi_draw, pi_feed)
        ecp = math.exp(jw / k_lmh)
        icp = math.exp(-jw / K_lmh)
        pi_draw_mem = pi_draw * icp
        pi_feed_mem = pi_feed * ecp
        effective_df = pi_draw_mem - pi_feed_mem
        raw_df = pi_draw - pi_feed
        df_efficiency = 0.0 if raw_df == 0.0 else effective_df / raw_df

        js = max(
            0.0,
            B
            * (
                draw_m * mw * icp
                - feed_draw_m * feed_cf * mw * ecp
            )
            / (1.0 + (B / max(jw, 1e-9)) * (ecp - icp)),
        )
        water_m3_h = jw * area_stage / 1000.0
        salt_loss_kg_h = js * area_stage / 1000.0
        wall_cf = (feed0 / max(feed_flow - water_m3_h, 1e-9)) * ecp

        stage_rows.append({
            "stage": i + 1,
            "feed_flow_in_m3_h": feed_flow,
            "feed_concentration_factor": feed_cf,
            "feed_osmotic_pressure_bar": pi_feed,
            "draw_flow_in_m3_h": draw_flow,
            "draw_molality": draw_m,
            "draw_osmotic_pressure_bar": pi_draw,
            "water_flux_lmh": jw,
            "draw_membrane_osmotic_pressure_bar": pi_draw_mem,
            "feed_membrane_osmotic_pressure_bar": pi_feed_mem,
            "effective_driving_force_bar": effective_df,
            "driving_force_efficiency": df_efficiency,
            "reverse_salt_flux_g_m2_h": js,
            "specific_reverse_salt_flux_g_l": 0.0 if jw <= 0 else js / jw,
            "water_permeated_m3_h": water_m3_h,
            "draw_solute_lost_kg_h": salt_loss_kg_h,
            "cp_modulus": ecp,
            "wall_concentration_factor": wall_cf,
        })

        feed_flow -= water_m3_h
        draw_flow += water_m3_h
        cumulative_salt_loss += salt_loss_kg_h

    total_water = sum(r["water_permeated_m3_h"] for r in stage_rows)
    total_salt = sum(r["draw_solute_lost_kg_h"] for r in stage_rows)
    recovery = total_water / feed0
    final_cf = feed0 / max(feed0 - total_water, 1e-9)
    final_pi = _interp_clamped(final_cf, _FEED_CF, _FEED_PI_BAR)
    avg_flux = total_water * 1000.0 / area_total
    max_cp = max(r["cp_modulus"] for r in stage_rows)
    max_wall_cf = max(r["wall_concentration_factor"] for r in stage_rows)
    wall_equiv_recovery = 1.0 - 1.0 / max(max_wall_cf, 1.000001)
    diluted_draw_m = draw_m0 * draw0 / (draw0 + total_water)
    diluted_draw_pi = _interp_clamped(diluted_draw_m, _DRAW_M, _DRAW_PI_BAR)
    reverse_solute_mg_l = total_salt * 1000.0 / max(feed0 - total_water, 1e-9)

    warnings: list[WarningMessage] = []
    if draw_m0 > 6.0:
        warnings.append(WarningMessage(
            "FO-DRAW-001", "critical", "NaCl draw outside workbook validation range",
            "The saved DRAW sheet marks NaCl validated to 6 mol/kg.",
        ))
    if min(r["driving_force_efficiency"] for r in stage_rows) < 0.25:
        warnings.append(WarningMessage(
            "FO-ICP-001", "warning", "Severe internal concentration polarization",
            "The workbook classifies this condition as severe ICP. Reducing support-layer structural parameter is more effective than increasing crossflow.",
        ))
    if final_cf > 6.0:
        warnings.append(WarningMessage(
            "FO-CF-001", "critical", "Feed concentration factor beyond saved lookup range",
            "The v0.1 regression clamps the source OSMOTIC table at CF=6. A general chemistry engine is required beyond this range.",
        ))
    warnings.append(WarningMessage(
        "FO-CHEM-PORT-001", "info", "Feed chemistry remains workbook-specific in v0.1",
        "The staged transport solver is active Python, but feed osmotic pressure is interpolated from the saved workbook chemistry case until the full Pitzer/speciation engine is ported.",
    ))

    summary = {
        "total_water_recovered_m3_h": total_water,
        "feed_water_recovery": recovery,
        "final_feed_flow_m3_h": feed0 - total_water,
        "final_bulk_concentration_factor": final_cf,
        "final_feed_osmotic_pressure_bar": final_pi,
        "average_water_flux_lmh": avg_flux,
        "maximum_cp_modulus": max_cp,
        "maximum_wall_concentration_factor": max_wall_cf,
        "wall_equivalent_recovery": wall_equiv_recovery,
        "total_draw_solute_lost_kg_h": total_salt,
        "draw_solute_lost_kg_m3_product": 0.0 if total_water <= 0 else total_salt / total_water,
        "diluted_draw_molality": diluted_draw_m,
        "diluted_draw_osmotic_pressure_bar": diluted_draw_pi,
        "membrane_area_m2": area_total,
        "specific_area_m2_per_m3_h_product": 0.0 if total_water <= 0 else area_total / total_water,
        "reverse_draw_solute_added_mg_l": reverse_solute_mg_l,
        "reverse_draw_cation_added_mg_l": reverse_solute_mg_l * 0.3934,
        "reverse_draw_anion_added_mg_l": reverse_solute_mg_l * (1.0 - 0.3934),
    }

    modules = {
        "transport_coefficients": {
            "reynolds": re,
            "schmidt": sc,
            "sherwood": sh,
            "mass_transfer_coefficient_m_s": k_m_s,
            "mass_transfer_coefficient_lmh": k_lmh,
            "solute_resistivity_s_m": resistivity_s_m,
            "solute_resistivity_lmh": K_lmh,
            "area_per_stage_m2": area_stage,
        },
        "stages": stage_rows,
        "handoff": {
            "bulk_outlet": {
                "flow_m3_h": feed0 - total_water,
                "bulk_concentration_factor": final_cf,
                "osmotic_pressure_bar": final_pi,
                "reverse_draw_solute_added_mg_l": reverse_solute_mg_l,
                "note": "Bulk state is the correct process handoff; wall CF is diagnostic only.",
            },
            "wall_diagnostic": {
                "maximum_wall_concentration_factor": max_wall_cf,
                "wall_equivalent_recovery": wall_equiv_recovery,
                "note": "Do not use as downstream bulk stream.",
            },
        },
    }

    streams = [
        Stream("FO feed", feed0, note="Saved-workbook chemistry basis", phase="liquid"),
        Stream("FO recovered water to draw", total_water, phase="liquid"),
        Stream("FO bulk concentrate", feed0 - total_water, phase="liquid", note=f"Bulk CF {final_cf:.6f}"),
        Stream("Diluted draw", draw0 + total_water, phase="liquid", note=f"NaCl draw {diluted_draw_m:.6f} mol/kg"),
    ]

    return CalculationResult(
        mode="fo_regression",
        model_status="active transport / saved-workbook chemistry regression",
        model_version="0.1.0",
        inputs=p,
        summary=summary,
        modules=modules,
        streams=streams,
        warnings=warnings,
        provenance={
            "source_workbook": "FO_Sizing_Calculator (1)(1).xlsx",
            "source_sections": ["FO PROFILE", "OSMOTIC", "DRAW"],
            "runtime_spreadsheet_dependency": False,
            "feed_chemistry_scope": "saved workbook Pitzer osmotic lookup only",
        },
    )
