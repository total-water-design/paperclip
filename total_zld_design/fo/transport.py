"""Local forward-osmosis transport with ECP, ICP and PAFO assistance.

This module is intentionally thermodynamics-agnostic: callers provide bulk
osmotic pressures. Phase 1 therefore remains compatible with future Shared
Water Chemistry integration instead of embedding a second chemistry engine.
"""
from __future__ import annotations

import math

from .models import FOMembrane, FOHydraulics, LocalTransportResult

_EPS = 1.0e-12


def _external_mass_transfer_lmh(
    velocity_m_s: float,
    hydraulic_diameter_mm: float,
    diffusivity_m2_s: float,
    hydraulics: FOHydraulics,
) -> float:
    dh_m = hydraulic_diameter_mm / 1000.0
    if min(velocity_m_s, dh_m, diffusivity_m2_s, hydraulics.kinematic_viscosity_m2_s) <= 0:
        raise ValueError("FO hydrodynamic inputs and diffusivity must be positive.")
    re = velocity_m_s * dh_m / hydraulics.kinematic_viscosity_m2_s
    sc = hydraulics.kinematic_viscosity_m2_s / diffusivity_m2_s
    sh = (
        hydraulics.sherwood_coefficient
        * re ** hydraulics.sherwood_re_exponent
        * sc ** hydraulics.sherwood_sc_exponent
    )
    return sh * diffusivity_m2_s / dh_m * 3.6e6


def _internal_mass_transfer_lmh(structural_parameter_um: float, diffusivity_m2_s: float) -> float:
    s_m = structural_parameter_um * 1.0e-6
    if min(s_m, diffusivity_m2_s) <= 0:
        raise ValueError("FO structural parameter and effective solute diffusivity must be positive.")
    return diffusivity_m2_s / s_m * 3.6e6


def solve_local_transport(
    membrane: FOMembrane,
    hydraulics: FOHydraulics,
    feed_osmotic_pressure_bar: float,
    draw_osmotic_pressure_bar: float,
    feed_total_solute_kg_m3: float,
    draw_total_solute_kg_m3: float,
    feed_diffusivity_m2_s: float,
    draw_diffusivity_m2_s: float,
    feed_applied_pressure_bar: float = 0.0,
) -> LocalTransportResult:
    """Solve one local FO/PAFO transport point.

    AL-FS places the active layer against feed: feed-side ECP and draw-side
    dilutive ICP. AL-DS places the active layer against draw: draw-side ECP and
    feed-side concentrative ICP. Positive feed hydraulic pressure assists
    feed-to-draw water transfer (PAFO).
    """
    if membrane.orientation not in {"AL-DS", "AL-FS"}:
        raise ValueError("FO membrane orientation must be 'AL-DS' or 'AL-FS'.")
    if membrane.water_permeability_lmh_bar <= 0 or membrane.salt_permeability_lmh < 0:
        raise ValueError("FO membrane A must be positive and B must be non-negative.")
    if min(feed_osmotic_pressure_bar, draw_osmotic_pressure_bar, feed_total_solute_kg_m3, draw_total_solute_kg_m3) < 0:
        raise ValueError("FO bulk osmotic pressures and solute concentrations cannot be negative.")
    if min(feed_diffusivity_m2_s, draw_diffusivity_m2_s) <= 0:
        raise ValueError("FO feed and draw effective diffusivities must be positive.")
    if feed_applied_pressure_bar < 0:
        raise ValueError("PAFO feed applied pressure cannot be negative in this model.")

    k_feed = _external_mass_transfer_lmh(
        hydraulics.feed_velocity_m_s,
        hydraulics.feed_hydraulic_diameter_mm,
        feed_diffusivity_m2_s,
        hydraulics,
    )
    k_draw = _external_mass_transfer_lmh(
        hydraulics.draw_velocity_m_s,
        hydraulics.draw_hydraulic_diameter_mm,
        draw_diffusivity_m2_s,
        hydraulics,
    )
    internal_diffusivity = draw_diffusivity_m2_s if membrane.orientation == "AL-FS" else feed_diffusivity_m2_s
    k_internal = _internal_mass_transfer_lmh(membrane.structural_parameter_um, internal_diffusivity)

    def membrane_state(jw: float):
        j = max(jw, _EPS)
        if membrane.orientation == "AL-FS":
            draw_mod = math.exp(-j / k_internal)
            feed_mod = math.exp(j / k_feed)
        else:
            draw_mod = math.exp(-j / k_draw)
            feed_mod = math.exp(j / k_internal)
        pi_draw_m = draw_osmotic_pressure_bar * draw_mod
        pi_feed_m = feed_osmotic_pressure_bar * feed_mod
        c_draw_m = draw_total_solute_kg_m3 * draw_mod
        c_feed_m = feed_total_solute_kg_m3 * feed_mod
        coupling = 1.0 + (membrane.salt_permeability_lmh / j) * abs(draw_mod - feed_mod)
        predicted = membrane.water_permeability_lmh_bar * (
            pi_draw_m - pi_feed_m + feed_applied_pressure_bar
        ) / coupling
        return predicted, pi_feed_m, pi_draw_m, c_feed_m, c_draw_m, feed_mod, draw_mod

    predicted_zero = membrane_state(_EPS)[0]
    if predicted_zero <= 0:
        state = membrane_state(_EPS)
        return LocalTransportResult(
            water_flux_lmh=0.0,
            reverse_solute_flux_g_m2_h=max(0.0, membrane.salt_permeability_lmh * (state[4] - state[3])),
            specific_reverse_solute_flux_g_l=0.0,
            feed_membrane_osmotic_pressure_bar=state[1],
            draw_membrane_osmotic_pressure_bar=state[2],
            effective_driving_force_bar=state[2] - state[1] + feed_applied_pressure_bar,
            feed_cp_modulus=state[5],
            draw_cp_modulus=state[6],
            feed_mass_transfer_lmh=k_feed,
            draw_mass_transfer_lmh=k_draw,
            internal_mass_transfer_lmh=k_internal,
        )

    lo = 0.0
    hi = max(
        membrane.water_permeability_lmh_bar
        * max(draw_osmotic_pressure_bar - feed_osmotic_pressure_bar + feed_applied_pressure_bar, 0.0),
        1.0,
    )
    while membrane_state(hi)[0] - hi > 0.0 and hi < 2000.0:
        hi *= 2.0
    for _ in range(90):
        mid = (lo + hi) / 2.0
        if membrane_state(mid)[0] - mid > 0.0:
            lo = mid
        else:
            hi = mid
    jw = max(0.0, (lo + hi) / 2.0)
    state = membrane_state(jw)
    js = max(0.0, membrane.salt_permeability_lmh * max(state[4] - state[3], 0.0))
    return LocalTransportResult(
        water_flux_lmh=jw,
        reverse_solute_flux_g_m2_h=js,
        specific_reverse_solute_flux_g_l=0.0 if jw <= 0.0 else js / jw,
        feed_membrane_osmotic_pressure_bar=state[1],
        draw_membrane_osmotic_pressure_bar=state[2],
        effective_driving_force_bar=state[2] - state[1] + feed_applied_pressure_bar,
        feed_cp_modulus=state[5],
        draw_cp_modulus=state[6],
        feed_mass_transfer_lmh=k_feed,
        draw_mass_transfer_lmh=k_draw,
        internal_mass_transfer_lmh=k_internal,
    )
