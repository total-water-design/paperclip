"""Segmented industrial FO/PAFO engineering calculation.

The kernel closes feed/draw water and draw-solute mass balances along the
membrane. Bulk osmotic pressures are explicit state inputs and are scaled with
bulk concentration in Phase 1. This preserves a clean integration point for the
Suite Shared Water Chemistry engine, which will later provide non-linear
high-salinity osmotic pressure and speciation without duplicating chemistry here.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..models import CalculationResult, Stream, WarningMessage
from .models import FOMembrane, FOHydraulics, FOOperatingPoint, FOSolutionState
from .transport import solve_local_transport


_DEFAULTS: dict[str, Any] = {
    "model_basis": "industrial FO transport kernel; external osmotic-pressure thermodynamics",
    "feed": {
        "flow_m3_h": 100.0,
        "osmotic_pressure_bar": 55.0,
        "total_solute_kg_m3": 65.0,
        "solute_diffusivity_m2_s": 1.5e-9,
        "temperature_c": 25.0,
    },
    "draw": {
        "flow_m3_h": 100.0,
        "osmotic_pressure_bar": 120.0,
        "total_solute_kg_m3": 180.0,
        "solute_diffusivity_m2_s": 1.5e-9,
        "temperature_c": 25.0,
    },
    "membrane": {
        "water_permeability_lmh_bar": 2.2,
        "salt_permeability_lmh": 0.20,
        "structural_parameter_um": 215.0,
        "membrane_area_m2": 700.0,
        "orientation": "AL-FS",
        "maximum_tmp_bar": 12.0,
    },
    "hydraulics": {
        "feed_velocity_m_s": 0.20,
        "draw_velocity_m_s": 0.20,
        "feed_hydraulic_diameter_mm": 0.80,
        "draw_hydraulic_diameter_mm": 0.80,
        "kinematic_viscosity_m2_s": 1.0e-6,
        "sherwood_coefficient": 0.20,
        "sherwood_re_exponent": 0.57,
        "sherwood_sc_exponent": 0.40,
        "feed_pressure_drop_bar": 0.50,
        "draw_pressure_drop_bar": 0.50,
        "pump_efficiency": 0.80,
    },
    "operation": {
        "feed_applied_pressure_bar": 0.0,
        "segments": 20,
    },
}


def fo_engineering_defaults() -> dict[str, Any]:
    return deepcopy(_DEFAULTS)


def _merge(base: dict[str, Any], patch: dict[str, Any] | None) -> dict[str, Any]:
    out = deepcopy(base)
    if not patch:
        return out
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _solution(data: dict[str, Any]) -> FOSolutionState:
    return FOSolutionState(
        flow_m3_h=float(data["flow_m3_h"]),
        osmotic_pressure_bar=float(data["osmotic_pressure_bar"]),
        total_solute_kg_m3=float(data["total_solute_kg_m3"]),
        solute_diffusivity_m2_s=float(data.get("solute_diffusivity_m2_s", 1.5e-9)),
        temperature_c=float(data.get("temperature_c", 25.0)),
    )


def _membrane(data: dict[str, Any]) -> FOMembrane:
    return FOMembrane(
        water_permeability_lmh_bar=float(data["water_permeability_lmh_bar"]),
        salt_permeability_lmh=float(data["salt_permeability_lmh"]),
        structural_parameter_um=float(data["structural_parameter_um"]),
        membrane_area_m2=float(data["membrane_area_m2"]),
        orientation=str(data.get("orientation", "AL-FS")).upper(),
        maximum_tmp_bar=float(data.get("maximum_tmp_bar", 12.0)),
    )


def _hydraulics(data: dict[str, Any]) -> FOHydraulics:
    return FOHydraulics(**{k: float(v) for k, v in data.items()})


def _operation(data: dict[str, Any]) -> FOOperatingPoint:
    return FOOperatingPoint(
        feed_applied_pressure_bar=float(data.get("feed_applied_pressure_bar", 0.0)),
        segments=int(data.get("segments", 20)),
    )


def calculate_fo_engineering(inputs: dict[str, Any] | None = None) -> CalculationResult:
    p = _merge(fo_engineering_defaults(), inputs)
    feed = _solution(p["feed"])
    draw = _solution(p["draw"])
    membrane = _membrane(p["membrane"])
    hydraulics = _hydraulics(p["hydraulics"])
    operation = _operation(p["operation"])

    if min(feed.flow_m3_h, draw.flow_m3_h, membrane.membrane_area_m2) <= 0:
        raise ValueError("FO feed flow, draw flow and membrane area must be positive.")
    if min(feed.solute_diffusivity_m2_s, draw.solute_diffusivity_m2_s) <= 0:
        raise ValueError("FO feed and draw effective solute diffusivities must be positive.")
    if operation.segments < 1 or operation.segments > 500:
        raise ValueError("FO axial segments must be between 1 and 500.")
    if not 0 < hydraulics.pump_efficiency <= 1:
        raise ValueError("FO pump efficiency must be in (0, 1].")
    if operation.feed_applied_pressure_bar > membrane.maximum_tmp_bar:
        raise ValueError("PAFO applied feed pressure exceeds the membrane maximum TMP.")

    feed0 = feed.flow_m3_h
    draw0 = draw.flow_m3_h
    feed_solute0 = feed.total_solute_kg_m3 * feed0
    draw_solute0 = draw.total_solute_kg_m3 * draw0
    feed_flow = feed0
    draw_flow = draw0
    feed_solute_mass_kg_h = feed_solute0
    draw_solute_mass_kg_h = draw_solute0
    area_segment = membrane.membrane_area_m2 / operation.segments
    rows: list[dict[str, Any]] = []

    for index in range(operation.segments):
        feed_c = feed_solute_mass_kg_h / max(feed_flow, 1.0e-12)
        draw_c = draw_solute_mass_kg_h / max(draw_flow, 1.0e-12)
        # Phase-1 thermodynamic closure: preserve the user's inlet osmotic
        # pressure and scale it with bulk concentration. Shared Water Chemistry
        # will replace this with a rigorous state evaluation in a later adapter.
        feed_pi = feed.osmotic_pressure_bar * feed_c / max(feed.total_solute_kg_m3, 1.0e-12)
        draw_pi = draw.osmotic_pressure_bar * draw_c / max(draw.total_solute_kg_m3, 1.0e-12)
        local = solve_local_transport(
            membrane,
            hydraulics,
            feed_pi,
            draw_pi,
            feed_c,
            draw_c,
            feed.solute_diffusivity_m2_s,
            draw.solute_diffusivity_m2_s,
            operation.feed_applied_pressure_bar,
        )
        water_m3_h = min(local.water_flux_lmh * area_segment / 1000.0, feed_flow * 0.20)
        reverse_solute_kg_h = local.reverse_solute_flux_g_m2_h * area_segment / 1000.0
        reverse_solute_kg_h = min(reverse_solute_kg_h, max(draw_solute_mass_kg_h, 0.0))

        rows.append({
            "segment": index + 1,
            "area_m2": area_segment,
            "feed_flow_in_m3_h": feed_flow,
            "draw_flow_in_m3_h": draw_flow,
            "feed_total_solute_kg_m3": feed_c,
            "draw_total_solute_kg_m3": draw_c,
            "feed_osmotic_pressure_bar": feed_pi,
            "draw_osmotic_pressure_bar": draw_pi,
            **local.to_dict(),
            "water_transferred_m3_h": water_m3_h,
            "reverse_draw_solute_kg_h": reverse_solute_kg_h,
        })

        feed_flow -= water_m3_h
        draw_flow += water_m3_h
        feed_solute_mass_kg_h += reverse_solute_kg_h
        draw_solute_mass_kg_h -= reverse_solute_kg_h
        if local.water_flux_lmh <= 1.0e-9 or feed_flow <= 1.0e-9:
            break

    total_water = feed0 - feed_flow
    total_reverse = feed_solute_mass_kg_h - feed_solute0
    avg_flux = total_water * 1000.0 / membrane.membrane_area_m2
    recovery = total_water / feed0
    final_feed_c = feed_solute_mass_kg_h / max(feed_flow, 1.0e-12)
    final_draw_c = draw_solute_mass_kg_h / max(draw_flow, 1.0e-12)
    final_feed_pi = feed.osmotic_pressure_bar * final_feed_c / max(feed.total_solute_kg_m3, 1.0e-12)
    final_draw_pi = draw.osmotic_pressure_bar * final_draw_c / max(draw.total_solute_kg_m3, 1.0e-12)

    feed_kw = feed0 * (hydraulics.feed_pressure_drop_bar + operation.feed_applied_pressure_bar) / (36.0 * hydraulics.pump_efficiency)
    draw_kw = draw0 * hydraulics.draw_pressure_drop_bar / (36.0 * hydraulics.pump_efficiency)
    circulation_kw = feed_kw + draw_kw
    sec = 0.0 if total_water <= 0 else circulation_kw / total_water

    warnings: list[WarningMessage] = []
    if operation.feed_applied_pressure_bar > 0:
        warnings.append(WarningMessage(
            "FO-PAFO-001", "info", "Pressure-assisted FO enabled",
            "Applied feed pressure is included in local transport and circulation energy. Confirm membrane/module TMP limits with the supplier.",
        ))
    if rows and min(r["effective_driving_force_bar"] for r in rows) < 3.0:
        warnings.append(WarningMessage(
            "FO-DF-001", "warning", "Low local osmotic driving force",
            "At least one axial segment approaches osmotic equilibrium; additional area may deliver little incremental water transfer.",
        ))
    if rows and max(r["specific_reverse_solute_flux_g_l"] for r in rows) > 1.0:
        warnings.append(WarningMessage(
            "FO-RSF-001", "warning", "High specific reverse-solute flux",
            "Review membrane B, draw chemistry and product/feed contamination limits before commercial design.",
        ))
    warnings.append(WarningMessage(
        "FO-THERMO-001", "info", "External osmotic-pressure thermodynamics",
        "Phase 1 scales user-supplied inlet osmotic pressure with bulk concentration. Arbitrary high-salinity speciation and non-ideal osmotic pressure must come from Shared Water Chemistry before production release.",
    ))

    summary = {
        "feed_water_recovery": recovery,
        "water_transferred_m3_h": total_water,
        "final_feed_flow_m3_h": feed_flow,
        "final_draw_flow_m3_h": draw_flow,
        "final_feed_total_solute_kg_m3": final_feed_c,
        "final_draw_total_solute_kg_m3": final_draw_c,
        "final_feed_osmotic_pressure_bar": final_feed_pi,
        "final_draw_osmotic_pressure_bar": final_draw_pi,
        "average_water_flux_lmh": avg_flux,
        "minimum_water_flux_lmh": min((r["water_flux_lmh"] for r in rows), default=0.0),
        "maximum_water_flux_lmh": max((r["water_flux_lmh"] for r in rows), default=0.0),
        "total_reverse_draw_solute_kg_h": total_reverse,
        "specific_reverse_solute_g_l_product": 0.0 if total_water <= 0 else total_reverse / total_water,
        "membrane_area_m2": membrane.membrane_area_m2,
        "specific_membrane_area_m2_per_m3_h": 0.0 if total_water <= 0 else membrane.membrane_area_m2 / total_water,
        "feed_pump_kw": feed_kw,
        "draw_pump_kw": draw_kw,
        "circulation_power_kw": circulation_kw,
        "circulation_sec_kwh_m3_transferred": sec,
    }

    modules = {
        "feed_state_basis": p["feed"],
        "draw_state_basis": p["draw"],
        "membrane": p["membrane"],
        "hydraulics": p["hydraulics"],
        "operation": p["operation"],
        "segments": rows,
        "mass_balance": {
            "water_in_m3_h": feed0 + draw0,
            "water_out_m3_h": feed_flow + draw_flow,
            "water_balance_error_m3_h": (feed0 + draw0) - (feed_flow + draw_flow),
            "solute_in_kg_h": feed_solute0 + draw_solute0,
            "solute_out_kg_h": feed_solute_mass_kg_h + draw_solute_mass_kg_h,
            "solute_balance_error_kg_h": (feed_solute0 + draw_solute0) - (feed_solute_mass_kg_h + draw_solute_mass_kg_h),
        },
        "handoff": {
            "bulk_concentrate": {
                "flow_m3_h": feed_flow,
                "total_solute_kg_m3": final_feed_c,
                "osmotic_pressure_bar": final_feed_pi,
                "temperature_c": feed.temperature_c,
            },
            "diluted_draw": {
                "flow_m3_h": draw_flow,
                "total_solute_kg_m3": final_draw_c,
                "osmotic_pressure_bar": final_draw_pi,
                "temperature_c": draw.temperature_c,
            },
        },
    }

    streams = [
        Stream("FO feed", feed0, tds_mg_l=feed.total_solute_kg_m3 * 1000.0, temperature_c=feed.temperature_c),
        Stream("FO bulk concentrate", feed_flow, tds_mg_l=final_feed_c * 1000.0, temperature_c=feed.temperature_c),
        Stream("FO draw inlet", draw0, tds_mg_l=draw.total_solute_kg_m3 * 1000.0, temperature_c=draw.temperature_c),
        Stream("FO diluted draw", draw_flow, tds_mg_l=final_draw_c * 1000.0, temperature_c=draw.temperature_c),
    ]

    return CalculationResult(
        mode="fo_engineering",
        model_status="engineering transport kernel / external thermodynamics",
        model_version="0.3.0-phase1",
        inputs=p,
        summary=summary,
        modules=modules,
        streams=streams,
        warnings=warnings,
        provenance={
            "calculation_scope": "FO/PAFO transport, ECP/ICP, reverse-solute transport, axial mass balance and circulation SEC",
            "thermodynamics_scope": "user-supplied inlet osmotic pressures; linear concentration scaling pending Shared Water Chemistry adapter",
            "literature_basis": [
                "Altaee et al., Forward Osmosis Pretreatment of Seawater for Thermal Desalination",
                "El Zayat et al. (2021), FDFO brine concentration bench/pilot study",
                "Zhang et al. (2026), Forward Osmosis Technology and Its Application Progress",
            ],
            "runtime_spreadsheet_dependency": False,
        },
    )
