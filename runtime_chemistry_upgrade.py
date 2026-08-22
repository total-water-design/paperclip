"""Runtime installer for the Total Water Design advanced chemistry layer.

The production WSGI entry point calls :func:`install_runtime_chemistry` before
Flask imports the application. This keeps the existing public APIs and saved
project payloads unchanged while rebinding the chemistry functions used by the
calculation engine to the upgraded equilibrium implementation.
"""
from __future__ import annotations

import math
from typing import Mapping


_INSTALLED = False
_INSTALL_INFO = {}


def install_runtime_chemistry() -> dict:
    global _INSTALLED, _INSTALL_INFO
    if _INSTALLED:
        return dict(_INSTALL_INFO)

    import chemistry_analysis as ca

    # Advanced chemistry intentionally builds on the established constants and
    # private equilibrium helpers. Preserve the original public implementations
    # once, before rebinding their names.
    if not hasattr(ca, "_legacy_weak_species_speciation"):
        ca._legacy_weak_species_speciation = ca.weak_species_speciation
    if not hasattr(ca, "_legacy_solve_carbonate_state"):
        ca._legacy_solve_carbonate_state = ca.solve_carbonate_state
    if not hasattr(ca, "_legacy_membrane_carbonate_split"):
        ca._legacy_membrane_carbonate_split = ca.membrane_carbonate_split
    if not hasattr(ca, "_legacy_mix_carbonate_streams"):
        ca._legacy_mix_carbonate_streams = ca.mix_carbonate_streams
    if not hasattr(ca, "_legacy_analyze_water"):
        ca._legacy_analyze_water = ca.analyze_water
    if not hasattr(ca, "_legacy_carbonate_speciation"):
        ca._legacy_carbonate_speciation = ca.carbonate_speciation

    import advanced_chemistry as adv
    from water_chemistry import (
        SPECIES,
        normalize_composition,
        polarization_scale_composition,
        total_tds_mg_l,
    )

    # Rebind core chemistry first. Existing functions such as acid dosing and
    # analyze_water resolve these names dynamically from chemistry_analysis.
    ca.weak_species_speciation = adv.weak_species_speciation
    ca.metal_hydroxo_speciation = adv.metal_hydroxo_speciation
    ca.solve_carbonate_state = adv.solve_carbonate_state
    ca.solve_charge_balanced_state = adv.solve_charge_balanced_state
    ca.equilibrium_charge_report = adv.equilibrium_charge_report
    ca.ammonia_membrane_transport = adv.ammonia_membrane_transport
    ca.mix_carbonate_streams = adv.mix_carbonate_streams

    def membrane_split_with_neutral_ammonia(
        feed_comp: Mapping[str, float],
        temp_c: float,
        feed_state: dict,
        recovery: float,
        ionic_rejection: float,
        permeate_template: Mapping[str, float],
        concentrate_template: Mapping[str, float],
    ) -> dict:
        """Final authoritative membrane chemistry with NH3/NH4 separation.

        The membrane hydraulic fixed-point remains unchanged. At the converged
        element duty, this function corrects total-ammonia transport using the
        local concentration-polarized state, closes ammonia mass balance, and
        then solves permeate/concentrate pH by explicit electroneutrality.
        """
        y = min(max(float(recovery), 0.0), 0.999999999)
        rej = min(max(float(ionic_rejection), 0.0), 0.999999999)
        feed = normalize_composition(feed_comp)
        perm = normalize_composition(permeate_template)
        conc = normalize_composition(concentrate_template)

        # Reconstruct the same first-order membrane-surface concentration basis
        # used by the element model. The carbon total is scaled consistently and
        # surface pH is solved by electroneutrality before NH3/NH4 partitioning.
        avg = {k: 0.5 * (feed[k] + conc[k]) for k in SPECIES}
        pf = math.exp(0.7 * y)
        pf_divalent = math.exp(0.7 * 1.35 * y)
        surface = polarization_scale_composition(avg, pf, pf_divalent)
        avg_tds = max(total_tds_mg_l(avg), 1e-30)
        surface_factor = max(0.25, min(4.0, total_tds_mg_l(surface) / avg_tds))
        surface_ct = max(
            0.0,
            float(feed_state.get("total_inorganic_carbon_mol_kg", 0.0))
            * surface_factor,
        )
        try:
            surface_state = adv.solve_charge_balanced_state(surface, temp_c, surface_ct)
            surface_ph = float(surface_state["ph"])
        except (KeyError, ValueError, ZeroDivisionError, OverflowError):
            surface_state = None
            surface_ph = float(feed_state.get("ph", 7.0))

        # NH4+ follows the calculated ionic membrane rejection. Neutral NH3 is
        # assigned zero rejection (unit concentration passage) unless a future
        # membrane-specific neutral-ammonia correlation supersedes this default.
        ammonia = adv.ammonia_membrane_transport(
            surface, temp_c, surface_ph, rej, neutral_rejection=0.0
        )
        perm_ammonia = max(
            0.0, float(ammonia["permeate_total_ammonia_mg_l_as_nh4"])
        )
        perm["ammonium"] = perm_ammonia
        if y <= 1e-12:
            conc["ammonium"] = feed["ammonium"]
        else:
            conc["ammonium"] = max(
                0.0,
                (feed["ammonium"] - y * perm_ammonia) / max(1.0 - y, 1e-30),
            )

        out = adv.membrane_carbonate_split(
            feed,
            temp_c,
            feed_state,
            y,
            rej,
            perm,
            conc,
        )
        out["ammonia_transport"] = ammonia
        out["membrane_surface_ph"] = surface_ph
        out["membrane_surface_state"] = surface_state
        out["neutral_ammonia_rejection"] = 0.0
        out["chemistry_model"] = "advanced weak-species/electroneutrality"
        return out

    ca.membrane_carbonate_split = membrane_split_with_neutral_ammonia

    # Upgrade the Water Chemistry analysis result while retaining every existing
    # field expected by the UI/reports. The original analysis automatically uses
    # the rebound advanced solve/speciation functions; this wrapper replaces the
    # raw analytical-ion charge report with equilibrium-species electroneutrality
    # and exposes the new weak-species diagnostics.
    def analyze_water_advanced(
        comp: Mapping[str, float],
        temp_c: float = 25.0,
        ph: float = 8.0,
        source_ph: float | None = None,
        reported_tds: float | None = None,
    ) -> dict:
        result = ca._legacy_analyze_water(
            comp, temp_c, ph, source_ph=source_ph, reported_tds=reported_tds
        )
        analytical = result.get("analytical_composition") or comp
        ta = ca.analytical_alkalinity_mol_kg(analytical, temp_c)
        state = adv.solve_carbonate_state(
            analytical,
            temp_c,
            ph=float(ph),
            total_alkalinity_mol_kg=ta,
        )
        result["charge"] = adv.equilibrium_charge_report(state, temp_c)
        spec = result.setdefault("speciation", {})
        spec["weak_systems"] = state.get("weak_systems", {})
        spec["hydroxo_species"] = state.get("hydroxo_species", {})
        spec["noncarbonate_alkalinity_components_mol_kg"] = state.get(
            "noncarbonate_alkalinity_components_mol_kg", {}
        )
        spec["nh4_mol_kg"] = state.get("nh4_mol_kg")
        spec["nh3_mol_kg"] = state.get("nh3_mol_kg")
        spec["nh4_mg_l_as_nh4"] = state.get("nh4_mg_l_as_nh4")
        spec["nh3_mg_l_as_nh3"] = state.get("nh3_mg_l_as_nh3")
        result["chemistry_model_version"] = "advanced-weak-species-1"
        result["ph_convergence_tolerance"] = 1e-9
        return result

    ca.analyze_water = analyze_water_advanced

    def carbonate_speciation_advanced(
        comp: Mapping[str, float],
        temp_c: float,
        ph: float,
        source_ph: float | None = None,
    ) -> dict:
        result = ca._legacy_carbonate_speciation(comp, temp_c, ph, source_ph)
        analytical = ca._analytical_composition(comp)
        ta = ca.analytical_alkalinity_mol_kg(analytical, temp_c)
        state = adv.solve_carbonate_state(
            analytical,
            temp_c,
            ph=float(ph),
            total_alkalinity_mol_kg=ta,
        )
        result["weak_systems"] = state.get("weak_systems", {})
        result["hydroxo_species"] = state.get("hydroxo_species", {})
        result["charge_balance"] = adv.equilibrium_charge_report(state, temp_c)
        result["chemistry_model_version"] = "advanced-weak-species-1"
        return result

    ca.carbonate_speciation = carbonate_speciation_advanced

    # calculations.py imported the original chemistry callables by name. Rebind
    # its module globals so all existing RO/NF/ERD calculation functions use the
    # advanced layer without changing their public signatures or CALCS registry.
    import calculations as calc

    calc.solve_carbonate_state = adv.solve_carbonate_state
    calc.membrane_carbonate_split = membrane_split_with_neutral_ammonia
    calc.mix_carbonate_streams = adv.mix_carbonate_streams
    calc.solve_charge_balanced_state = adv.solve_charge_balanced_state
    calc.ammonia_membrane_transport = adv.ammonia_membrane_transport
    calc.CHEMISTRY_MODEL_VERSION = "advanced-weak-species-1"
    calc.PH_CONVERGENCE_TOLERANCE = 1e-9

    _INSTALL_INFO = {
        "installed": True,
        "chemistry_model_version": "advanced-weak-species-1",
        "ph_tolerance": 1e-9,
        "neutral_nh3_rejection_default": 0.0,
        "hydroxo_components": tuple(adv.HYDROXO_COMPONENTS),
    }
    _INSTALLED = True
    return dict(_INSTALL_INFO)
