"""Crystallization effects of residual RO antiscalants and other impurities.

This module provides a calibration-ready framework for Total ZLD Design. It does
not assign universal inhibition factors to commercial products. Instead it
represents mechanisms documented in industrial crystallization literature:
selective adsorption on crystal faces, growth-step pinning, nucleation delay,
metastable-zone widening, habit modification, impurity incorporation, and
possible downstream crystal-quality impacts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import exp
from typing import Any


@dataclass(frozen=True)
class InhibitorDescriptor:
    chemistry_family: str
    concentration_mg_l: float
    adsorption_constant_l_mg: float = 0.0
    growth_blocking_strength: float = 0.0
    nucleation_blocking_strength: float = 0.0
    metastable_zone_strength: float = 0.0
    habit_modification_strength: float = 0.0
    incorporation_risk_strength: float = 0.0


@dataclass(frozen=True)
class InhibitorEffect:
    surface_coverage_fraction: float
    growth_rate_multiplier: float
    nucleation_rate_multiplier: float
    metastable_zone_multiplier: float
    induction_time_multiplier: float
    habit_modification_index: float
    impurity_incorporation_index: float
    qualitative_risk: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def langmuir_surface_coverage(concentration_mg_l: float, adsorption_constant_l_mg: float) -> float:
    """Return θ = KC/(1+KC), a bounded adsorption proxy.

    The expression is used only as a generic calibration structure. The K value
    must come from data for the crystal/impurity/solvent system of interest.
    """
    if concentration_mg_l < 0 or adsorption_constant_l_mg < 0:
        raise ValueError("Concentration and adsorption constant must be non-negative.")
    x = concentration_mg_l * adsorption_constant_l_mg
    return 0.0 if x <= 0 else x / (1.0 + x)


def evaluate_inhibitor_effect(descriptor: InhibitorDescriptor) -> InhibitorEffect:
    """Evaluate calibrated impurity effects without inventing universal constants.

    Strength parameters are dimensionless calibration coefficients. A value of
    zero produces no modeled effect, preserving a neutral baseline. Increasing
    surface coverage suppresses growth/nucleation exponentially and can widen
    the effective metastable zone and induction time.
    """
    if descriptor.concentration_mg_l < 0:
        raise ValueError("Inhibitor concentration must be non-negative.")
    strengths = (
        descriptor.growth_blocking_strength,
        descriptor.nucleation_blocking_strength,
        descriptor.metastable_zone_strength,
        descriptor.habit_modification_strength,
        descriptor.incorporation_risk_strength,
    )
    if any(x < 0 for x in strengths):
        raise ValueError("Inhibitor strength parameters must be non-negative.")

    theta = langmuir_surface_coverage(
        descriptor.concentration_mg_l,
        descriptor.adsorption_constant_l_mg,
    )
    growth_multiplier = exp(-descriptor.growth_blocking_strength * theta)
    nucleation_multiplier = exp(-descriptor.nucleation_blocking_strength * theta)
    mz_multiplier = 1.0 + descriptor.metastable_zone_strength * theta
    induction_multiplier = 1.0 / max(nucleation_multiplier, 1.0e-12)
    habit_index = descriptor.habit_modification_strength * theta
    incorporation_index = descriptor.incorporation_risk_strength * theta

    score = max(
        1.0 - growth_multiplier,
        1.0 - nucleation_multiplier,
        mz_multiplier - 1.0,
        habit_index,
        incorporation_index,
    )
    if descriptor.concentration_mg_l == 0 or score < 0.05:
        risk = "low"
    elif score < 0.25:
        risk = "review"
    elif score < 0.60:
        risk = "material"
    else:
        risk = "high"

    return InhibitorEffect(
        surface_coverage_fraction=theta,
        growth_rate_multiplier=growth_multiplier,
        nucleation_rate_multiplier=nucleation_multiplier,
        metastable_zone_multiplier=mz_multiplier,
        induction_time_multiplier=induction_multiplier,
        habit_modification_index=habit_index,
        impurity_incorporation_index=incorporation_index,
        qualitative_risk=risk,
    )


def antiscalant_family_guidance() -> dict[str, dict[str, Any]]:
    """Return mechanism guidance only; no universal quantitative coefficients."""
    return {
        "phosphonate": {
            "examples": ["HEDP", "ATMP", "PBTC"],
            "mechanisms": ["surface adsorption", "step pinning", "nucleation delay", "habit modification"],
            "zld_note": "Track residual active concentration and phosphorus loading into evaporator/crystallizer solids.",
        },
        "polycarboxylate": {
            "examples": ["polyacrylate", "polymaleate", "PMA/PCA"],
            "mechanisms": ["surface adsorption", "dispersion", "growth inhibition", "particle stabilization"],
            "zld_note": "May suppress crystal enlargement while stabilizing fines; empirical calibration is required.",
        },
        "sulfonated_copolymer": {
            "examples": ["AA/AMPS-type copolymers"],
            "mechanisms": ["threshold inhibition", "dispersion", "surface adsorption"],
            "zld_note": "Assess persistence through RO concentration and thermal exposure before crystallizer design credit.",
        },
        "proprietary_blend": {
            "examples": ["commercial RO antiscalant blend"],
            "mechanisms": ["unknown or mixed"],
            "zld_note": "Require supplier chemistry/provenance or pilot calibration; do not infer kinetics from dose alone.",
        },
    }


def crystallizer_inhibitor_capabilities() -> dict[str, Any]:
    return {
        "status": "calibration-ready foundation",
        "effects": [
            "crystal growth suppression",
            "primary/secondary nucleation suppression",
            "induction-time extension",
            "metastable-zone widening",
            "crystal habit modification",
            "impurity incorporation risk",
            "fines/agglomeration risk screening",
        ],
        "quantitative_requirement": "system-specific adsorption/kinetic calibration data",
        "families": antiscalant_family_guidance(),
    }
