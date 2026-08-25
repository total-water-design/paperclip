"""Falling-film evaporator design support for Total ZLD Design.

The module adds a design-oriented falling-film evaporator layer without changing
``thermal_legacy.py``.  The Shahzad/Burhan/Ng horizontal-tube saline-water
correlation is implemented only inside its published applicability window.
Outside that window the engine requires a user/vendor design U value rather than
silently presenting an extrapolation as validated ZLD physics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil, exp, log, pi, sqrt
from typing import Any

from .models import CalculationResult, Stream, WarningMessage

G_M_S2 = 9.80665


@dataclass(frozen=True)
class FFECorrelationResult:
    heat_transfer_coefficient_w_m2_k: float
    thermally_driven_term_w_m2_k: float
    bubble_assisted_term_w_m2_k: float
    film_reynolds: float
    prandtl: float
    saturation_temperature_k: float
    salinity_ppm: float
    in_published_range: bool
    range_failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FFEDesignResult:
    feed_mass_flow_kg_h: float
    concentrate_mass_flow_kg_h: float
    evaporation_rate_kg_h: float
    evaporation_rate_m3_h: float
    solids_mass_flow_kg_h: float
    heat_duty_kw: float
    sensible_heat_kw: float
    latent_heat_kw: float
    lmtd_k: float
    evaporation_htc_w_m2_k: float | None
    overall_u_w_m2_k: float
    required_heat_transfer_area_m2: float
    tube_area_each_m2: float
    required_tube_count: int
    installed_heat_transfer_area_m2: float
    design_film_reynolds: float
    liquid_loading_kg_m_s: float
    distributor_flow_kg_h: float
    recirculation_ratio_to_feed: float
    vapor_volumetric_flow_m3_s: float
    minimum_vapor_disengagement_area_m2: float
    minimum_vapor_diameter_m: float
    correlation_in_published_range: bool
    correlation_range_failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def film_reynolds_from_loading(liquid_loading_kg_m_s: float, viscosity_pa_s: float) -> float:
    """Return film Reynolds number using the engineering convention ReΓ=4Γ/μ."""
    if liquid_loading_kg_m_s <= 0 or viscosity_pa_s <= 0:
        raise ValueError("Liquid loading and viscosity must be positive.")
    return 4.0 * liquid_loading_kg_m_s / viscosity_pa_s


def liquid_loading_from_film_reynolds(film_reynolds: float, viscosity_pa_s: float) -> float:
    if film_reynolds <= 0 or viscosity_pa_s <= 0:
        raise ValueError("Film Reynolds number and viscosity must be positive.")
    return film_reynolds * viscosity_pa_s / 4.0


def prandtl_number(viscosity_pa_s: float, cp_j_kg_k: float, thermal_conductivity_w_m_k: float) -> float:
    if min(viscosity_pa_s, cp_j_kg_k, thermal_conductivity_w_m_k) <= 0:
        raise ValueError("Viscosity, heat capacity and thermal conductivity must be positive.")
    return viscosity_pa_s * cp_j_kg_k / thermal_conductivity_w_m_k


def shahzad_horizontal_saline_ffe_htc(
    *,
    viscosity_pa_s: float,
    density_kg_m3: float,
    thermal_conductivity_w_m_k: float,
    cp_j_kg_k: float,
    film_reynolds: float,
    salinity_ppm: float,
    saturation_temperature_k: float,
    heat_flux_w_m2: float,
    film_delta_t_k: float,
    vapor_specific_volume_m3_kg: float,
) -> FFECorrelationResult:
    """Published low-temperature saline horizontal-tube falling-film correlation.

    Shahzad, Burhan & Ng report applicability at 280–305 K, salinity
    35,000–95,000 ppm, ReΓ 45–90 and Pr 5–10.  The function still returns the
    algebraic value outside the range for sensitivity review, but explicitly marks
    it out-of-range.  ``size_falling_film_evaporator`` will not use that value for
    design outside the published range unless a separate design-U is supplied.
    """
    if min(
        viscosity_pa_s,
        density_kg_m3,
        thermal_conductivity_w_m_k,
        cp_j_kg_k,
        film_reynolds,
        saturation_temperature_k,
        heat_flux_w_m2,
        film_delta_t_k,
        vapor_specific_volume_m3_kg,
    ) <= 0:
        raise ValueError("FFE correlation inputs must be positive.")
    if salinity_ppm < 0:
        raise ValueError("Salinity cannot be negative.")

    pr = prandtl_number(viscosity_pa_s, cp_j_kg_k, thermal_conductivity_w_m_k)
    property_group = viscosity_pa_s**2 / (
        G_M_S2 * density_kg_m3**2 * thermal_conductivity_w_m_k**3
    )
    thermal_term = (
        0.279
        * property_group ** (-0.333)
        * film_reynolds ** (-2.18)
        * pr**4.0
        * (2.0 * exp(salinity_ppm / 30000.0) - 1.0) ** (-0.45)
        * (saturation_temperature_k / 322.0)
    )
    bubble_term = (
        0.875
        * (heat_flux_w_m2 / film_delta_t_k)
        * (vapor_specific_volume_m3_kg / 52.65)
    )
    h = thermal_term + bubble_term

    failures: list[str] = []
    if not 280.0 <= saturation_temperature_k <= 305.0:
        failures.append("saturation_temperature_k outside 280–305 K")
    if not 35000.0 <= salinity_ppm <= 95000.0:
        failures.append("salinity_ppm outside 35,000–95,000 ppm")
    if not 45.0 <= film_reynolds <= 90.0:
        failures.append("film_reynolds outside 45–90")
    if not 5.0 <= pr <= 10.0:
        failures.append("Prandtl outside 5–10")

    return FFECorrelationResult(
        heat_transfer_coefficient_w_m2_k=h,
        thermally_driven_term_w_m2_k=thermal_term,
        bubble_assisted_term_w_m2_k=bubble_term,
        film_reynolds=film_reynolds,
        prandtl=pr,
        saturation_temperature_k=saturation_temperature_k,
        salinity_ppm=salinity_ppm,
        in_published_range=not failures,
        range_failures=tuple(failures),
    )


def log_mean_temperature_difference(
    hot_in_c: float,
    hot_out_c: float,
    boiling_temperature_c: float,
) -> float:
    """LMTD for a condensing/boiling side at approximately constant temperature."""
    dt1 = hot_in_c - boiling_temperature_c
    dt2 = hot_out_c - boiling_temperature_c
    if dt1 <= 0 or dt2 <= 0:
        raise ValueError("Heating-medium temperatures must exceed boiling temperature.")
    if abs(dt1 - dt2) < 1.0e-12:
        return dt1
    return (dt1 - dt2) / log(dt1 / dt2)


def _mass_fraction_from_tds_mg_l(tds_mg_l: float, density_kg_m3: float) -> float:
    if tds_mg_l < 0 or density_kg_m3 <= 0:
        raise ValueError("TDS must be non-negative and density positive.")
    # mg/L numerically equals kg/m3.
    value = (tds_mg_l / 1000.0) / density_kg_m3
    if not 0 <= value < 1:
        raise ValueError("TDS and density imply an invalid solution mass fraction.")
    return value


def _overall_u_from_resistances(
    outside_htc_w_m2_k: float,
    tubeside_htc_w_m2_k: float,
    wall_thickness_m: float,
    wall_conductivity_w_m_k: float,
    fouling_resistance_m2_k_w: float,
) -> float:
    if min(outside_htc_w_m2_k, tubeside_htc_w_m2_k, wall_conductivity_w_m_k) <= 0:
        raise ValueError("Heat-transfer coefficients and wall conductivity must be positive.")
    if wall_thickness_m < 0 or fouling_resistance_m2_k_w < 0:
        raise ValueError("Wall thickness and fouling resistance cannot be negative.")
    resistance = (
        1.0 / outside_htc_w_m2_k
        + 1.0 / tubeside_htc_w_m2_k
        + wall_thickness_m / wall_conductivity_w_m_k
        + fouling_resistance_m2_k_w
    )
    return 1.0 / resistance


def falling_film_defaults() -> dict[str, Any]:
    return {
        "feed_flow_m3_h": 50.0,
        "feed_density_kg_m3": 1065.0,
        "feed_tds_mg_l": 65000.0,
        "target_concentrate_tds_mg_l": 95000.0,
        "concentrate_density_kg_m3": 1090.0,
        "feed_temperature_c": 25.0,
        "boiling_temperature_c": 25.0,
        "boiling_point_elevation_c": 0.0,
        "latent_heat_kj_kg": 2442.0,
        "solution_cp_kj_kg_k": 3.9,
        "heating_medium_in_c": 35.0,
        "heating_medium_out_c": 32.0,
        "liquid_viscosity_pa_s": 0.0012,
        "liquid_thermal_conductivity_w_m_k": 0.60,
        "film_reynolds": 65.0,
        "heat_flux_w_m2": 18000.0,
        "film_delta_t_k": 5.0,
        "vapor_specific_volume_m3_kg": 43.4,
        "tubeside_htc_w_m2_k": 4500.0,
        "wall_thickness_m": 0.0010,
        "wall_conductivity_w_m_k": 16.0,
        "fouling_resistance_m2_k_w": 0.00020,
        "design_overall_u_w_m2_k": None,
        "tube_outer_diameter_m": 0.025,
        "tube_length_m": 2.0,
        "allowable_vapor_velocity_m_s": 3.0,
        "area_margin_fraction": 0.15,
        "correlation": "Shahzad-Burhan-Ng-2019-horizontal-saline",
    }


def size_falling_film_evaporator(inputs: dict[str, Any] | None = None) -> CalculationResult:
    p = falling_film_defaults()
    if inputs:
        p.update(inputs)

    feed_q = float(p["feed_flow_m3_h"])
    rho_f = float(p["feed_density_kg_m3"])
    rho_c = float(p["concentrate_density_kg_m3"])
    if min(feed_q, rho_f, rho_c) <= 0:
        raise ValueError("FFE feed flow and solution densities must be positive.")
    wf = _mass_fraction_from_tds_mg_l(float(p["feed_tds_mg_l"]), rho_f)
    wc = _mass_fraction_from_tds_mg_l(float(p["target_concentrate_tds_mg_l"]), rho_c)
    if wc <= wf:
        raise ValueError("FFE target concentration must exceed feed concentration.")

    feed_mass = feed_q * rho_f
    solids_mass = feed_mass * wf
    concentrate_mass = solids_mass / wc
    evaporation = feed_mass - concentrate_mass
    if evaporation <= 0:
        raise ValueError("FFE concentration basis produces no positive evaporation duty.")

    cp = float(p["solution_cp_kj_kg_k"])
    latent = float(p["latent_heat_kj_kg"])
    feed_t = float(p["feed_temperature_c"])
    boiling_t = float(p["boiling_temperature_c"]) + float(p["boiling_point_elevation_c"])
    sensible_kw = max(0.0, feed_mass * cp * (boiling_t - feed_t) / 3600.0)
    latent_kw = evaporation * latent / 3600.0
    duty_kw = sensible_kw + latent_kw
    lmtd = log_mean_temperature_difference(
        float(p["heating_medium_in_c"]),
        float(p["heating_medium_out_c"]),
        boiling_t,
    )

    corr = shahzad_horizontal_saline_ffe_htc(
        viscosity_pa_s=float(p["liquid_viscosity_pa_s"]),
        density_kg_m3=rho_f,
        thermal_conductivity_w_m_k=float(p["liquid_thermal_conductivity_w_m_k"]),
        cp_j_kg_k=cp * 1000.0,
        film_reynolds=float(p["film_reynolds"]),
        salinity_ppm=float(p["feed_tds_mg_l"]),
        saturation_temperature_k=boiling_t + 273.15,
        heat_flux_w_m2=float(p["heat_flux_w_m2"]),
        film_delta_t_k=float(p["film_delta_t_k"]),
        vapor_specific_volume_m3_kg=float(p["vapor_specific_volume_m3_kg"]),
    )

    design_u = p.get("design_overall_u_w_m2_k")
    if design_u is not None:
        overall_u = float(design_u)
        if overall_u <= 0:
            raise ValueError("design_overall_u_w_m2_k must be positive when supplied.")
    elif corr.in_published_range:
        overall_u = _overall_u_from_resistances(
            corr.heat_transfer_coefficient_w_m2_k,
            float(p["tubeside_htc_w_m2_k"]),
            float(p["wall_thickness_m"]),
            float(p["wall_conductivity_w_m_k"]),
            float(p["fouling_resistance_m2_k_w"]),
        )
    else:
        raise ValueError(
            "Shahzad falling-film correlation is outside its published range; "
            "supply a validated design_overall_u_w_m2_k for this ZLD condition. "
            + "; ".join(corr.range_failures)
        )

    margin = float(p["area_margin_fraction"])
    if margin < 0:
        raise ValueError("FFE area margin cannot be negative.")
    area = duty_kw * 1000.0 / (overall_u * lmtd) * (1.0 + margin)
    od = float(p["tube_outer_diameter_m"])
    tube_length = float(p["tube_length_m"])
    if min(od, tube_length) <= 0:
        raise ValueError("FFE tube diameter and length must be positive.")
    tube_area = pi * od * tube_length
    tube_count = max(1, ceil(area / tube_area))
    installed_area = tube_count * tube_area

    gamma = liquid_loading_from_film_reynolds(float(p["film_reynolds"]), float(p["liquid_viscosity_pa_s"]))
    total_tube_length = tube_count * tube_length
    distributor_kg_h = gamma * total_tube_length * 3600.0
    recirc_ratio = distributor_kg_h / feed_mass

    vapor_vdot = evaporation * float(p["vapor_specific_volume_m3_kg"]) / 3600.0
    vapor_velocity = float(p["allowable_vapor_velocity_m_s"])
    if vapor_velocity <= 0:
        raise ValueError("Allowable vapor velocity must be positive.")
    disengagement_area = vapor_vdot / vapor_velocity
    vapor_diameter = sqrt(4.0 * disengagement_area / pi)

    design = FFEDesignResult(
        feed_mass_flow_kg_h=feed_mass,
        concentrate_mass_flow_kg_h=concentrate_mass,
        evaporation_rate_kg_h=evaporation,
        evaporation_rate_m3_h=evaporation / 1000.0,
        solids_mass_flow_kg_h=solids_mass,
        heat_duty_kw=duty_kw,
        sensible_heat_kw=sensible_kw,
        latent_heat_kw=latent_kw,
        lmtd_k=lmtd,
        evaporation_htc_w_m2_k=corr.heat_transfer_coefficient_w_m2_k,
        overall_u_w_m2_k=overall_u,
        required_heat_transfer_area_m2=area,
        tube_area_each_m2=tube_area,
        required_tube_count=tube_count,
        installed_heat_transfer_area_m2=installed_area,
        design_film_reynolds=float(p["film_reynolds"]),
        liquid_loading_kg_m_s=gamma,
        distributor_flow_kg_h=distributor_kg_h,
        recirculation_ratio_to_feed=recirc_ratio,
        vapor_volumetric_flow_m3_s=vapor_vdot,
        minimum_vapor_disengagement_area_m2=disengagement_area,
        minimum_vapor_diameter_m=vapor_diameter,
        correlation_in_published_range=corr.in_published_range,
        correlation_range_failures=corr.range_failures,
    )

    warnings: list[WarningMessage] = []
    if not corr.in_published_range:
        warnings.append(WarningMessage(
            "FFE-CORR-001", "warning", "Published FFE correlation outside validated range",
            "; ".join(corr.range_failures) + ". A separate validated design U was used.",
        ))
    if float(p["feed_tds_mg_l"]) > 95000:
        warnings.append(WarningMessage(
            "FFE-ZLD-001", "warning", "Hypersaline ZLD duty exceeds source-correlation salinity range",
            "Use measured/vendor heat-transfer data including boiling-point elevation, viscosity, fouling and precipitation risk before final equipment sizing.",
        ))
    if recirc_ratio < 1.0:
        warnings.append(WarningMessage(
            "FFE-WET-001", "review", "Low distributor flow relative to fresh feed",
            "Review distributor hydraulics and minimum wetting rate; dry-out control is a design constraint, not only a heat-duty calculation.",
        ))

    concentrate_q = concentrate_mass / rho_c
    result_dict = design.to_dict()
    result_dict["correlation"] = corr.to_dict()
    result_dict["boiling_temperature_c_including_bpe"] = boiling_t

    return CalculationResult(
        mode="falling_film_evaporator",
        model_status="design screening / published-range correlation with explicit ZLD guardrails",
        model_version="0.3.0-ffe1",
        inputs=p,
        summary={
            "evaporation_rate_kg_h": evaporation,
            "concentrate_flow_m3_h": concentrate_q,
            "heat_duty_kw": duty_kw,
            "overall_u_w_m2_k": overall_u,
            "required_heat_transfer_area_m2": area,
            "required_tube_count": tube_count,
            "recirculation_ratio_to_feed": recirc_ratio,
            "minimum_vapor_diameter_m": vapor_diameter,
        },
        modules={"falling_film_evaporator": result_dict},
        streams=[
            Stream("FFE feed", feed_q, tds_mg_l=float(p["feed_tds_mg_l"]), temperature_c=feed_t),
            Stream("FFE distillate", evaporation / 1000.0, tds_mg_l=0.0, temperature_c=boiling_t),
            Stream("FFE concentrate", concentrate_q, tds_mg_l=float(p["target_concentrate_tds_mg_l"]), temperature_c=boiling_t),
        ],
        warnings=warnings,
        provenance={
            "source": "Shahzad, Burhan & Ng (2019), Design of Industrial Falling Film Evaporators",
            "published_correlation_geometry": "horizontal-tube falling-film evaporator",
            "published_range": "280–305 K; 35,000–95,000 ppm; ReΓ 45–90; Pr 5–10",
            "zld_guardrail": "outside published range requires user/vendor validated overall U",
            "boiling_point_elevation": "external input pending rigorous Shared Water Chemistry/solution-property integration",
        },
    )


def falling_film_capabilities() -> dict[str, Any]:
    return {
        "status": "design screening with published applicability guardrails",
        "implemented": [
            "nonvolatile-solute feed/concentrate/evaporation mass balance",
            "sensible plus latent heat duty",
            "boiling-point-elevation input",
            "LMTD",
            "Shahzad/Burhan/Ng low-temperature saline horizontal-tube FFE correlation",
            "overall-U resistance calculation",
            "heat-transfer area and tube-count sizing",
            "film-Reynolds liquid-loading/distributor-flow sizing",
            "vapor volumetric load and minimum disengagement diameter",
        ],
        "published_range": {
            "saturation_temperature_k": [280, 305],
            "salinity_ppm": [35000, 95000],
            "film_reynolds": [45, 90],
            "prandtl": [5, 10],
        },
        "not_yet_production": [
            "species-specific boiling-point elevation",
            "hypersaline viscosity/density/conductivity correlations",
            "precipitation/fouling heat-transfer degradation",
            "multi-effect vapor/energy cascade",
            "vertical-tube vendor correlation selection",
            "non-condensable gas/vacuum system sizing",
            "mechanical tube-sheet/shell design",
        ],
    }
