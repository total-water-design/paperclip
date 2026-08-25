"""Crystallization kinetics helpers for Total ZLD Design.

This module provides a conservative engineering foundation for nucleation and
crystal-growth calculations. It does not replace the validated FCC screening
model yet. Parameters such as kinetic constants, exponents, interfacial energy,
shape factors and activation energies must come from literature, experiments,
pilot calibration or supplier/process data for the specific solute/system.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Literal

R_J_MOL_K = 8.31446261815324
K_BOLTZMANN_J_K = 1.380649e-23

NucleationMode = Literal[
    "homogeneous",
    "heterogeneous",
    "secondary",
    "contact",
    "attrition",
    "needle_breeding",
    "polycrystalline_breeding",
]


@dataclass(frozen=True)
class KineticRate:
    rate: float
    driving_force: float
    exponent: float
    rate_constant: float
    temperature_k: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def arrhenius_rate_constant(
    pre_exponential: float,
    activation_energy_j_mol: float,
    temperature_k: float,
) -> float:
    """Return k(T)=A exp(-E/RT)."""
    if pre_exponential < 0:
        raise ValueError("Pre-exponential factor cannot be negative.")
    if activation_energy_j_mol < 0:
        raise ValueError("Activation energy cannot be negative.")
    if temperature_k <= 0:
        raise ValueError("Absolute temperature must be positive.")
    return pre_exponential * math.exp(-activation_energy_j_mol / (R_J_MOL_K * temperature_k))


def power_law_growth_rate(
    supersaturation_driving_force: float,
    growth_rate_constant: float,
    growth_exponent: float,
) -> KineticRate:
    """Industrial empirical crystal growth law G = k_g * ΔC^g."""
    if supersaturation_driving_force < 0:
        raise ValueError("Growth driving force cannot be negative.")
    if growth_rate_constant < 0 or growth_exponent <= 0:
        raise ValueError("Growth rate constant must be non-negative and exponent positive.")
    return KineticRate(
        rate=growth_rate_constant * supersaturation_driving_force ** growth_exponent,
        driving_force=supersaturation_driving_force,
        exponent=growth_exponent,
        rate_constant=growth_rate_constant,
    )


def arrhenius_growth_rate(
    supersaturation_driving_force: float,
    pre_exponential: float,
    activation_energy_j_mol: float,
    temperature_k: float,
    growth_exponent: float,
) -> KineticRate:
    """Temperature-dependent empirical growth law G=A exp(-E/RT) ΔC^g."""
    k = arrhenius_rate_constant(pre_exponential, activation_energy_j_mol, temperature_k)
    out = power_law_growth_rate(supersaturation_driving_force, k, growth_exponent)
    return KineticRate(out.rate, out.driving_force, out.exponent, out.rate_constant, temperature_k)


def power_law_nucleation_rate(
    supersaturation_driving_force: float,
    nucleation_rate_constant: float,
    nucleation_exponent: float,
) -> KineticRate:
    """Industrial empirical nucleation law B = k_b * ΔC^b."""
    if supersaturation_driving_force < 0:
        raise ValueError("Nucleation driving force cannot be negative.")
    if nucleation_rate_constant < 0 or nucleation_exponent <= 0:
        raise ValueError("Nucleation rate constant must be non-negative and exponent positive.")
    return KineticRate(
        rate=nucleation_rate_constant * supersaturation_driving_force ** nucleation_exponent,
        driving_force=supersaturation_driving_force,
        exponent=nucleation_exponent,
        rate_constant=nucleation_rate_constant,
    )


def heterogeneous_surface_energy_factor(contact_angle_deg: float) -> float:
    """Classical heterogeneous nucleation energy factor φ.

    φ = 1/4 * (2 + cos θ) * (1 - cos θ)^2
    so ΔG*_het = φ ΔG*_hom.
    """
    if not 0 <= contact_angle_deg <= 180:
        raise ValueError("Contact angle must be between 0 and 180 degrees.")
    c = math.cos(math.radians(contact_angle_deg))
    return 0.25 * (2.0 + c) * (1.0 - c) ** 2


def classical_critical_radius_m(
    interfacial_energy_j_m2: float,
    molecular_volume_m3: float,
    temperature_k: float,
    supersaturation_ratio: float,
) -> float:
    """Critical nucleus radius from the Gibbs-Thomson relation.

    r* = 2 σ v / (k_B T ln S)
    """
    if interfacial_energy_j_m2 <= 0 or molecular_volume_m3 <= 0 or temperature_k <= 0:
        raise ValueError("Interfacial energy, molecular volume and temperature must be positive.")
    if supersaturation_ratio <= 1:
        return math.inf
    return 2.0 * interfacial_energy_j_m2 * molecular_volume_m3 / (
        K_BOLTZMANN_J_K * temperature_k * math.log(supersaturation_ratio)
    )


def classical_homogeneous_barrier_j(
    interfacial_energy_j_m2: float,
    molecular_volume_m3: float,
    temperature_k: float,
    supersaturation_ratio: float,
) -> float:
    """Classical homogeneous critical free-energy barrier ΔG*."""
    if interfacial_energy_j_m2 <= 0 or molecular_volume_m3 <= 0 or temperature_k <= 0:
        raise ValueError("Interfacial energy, molecular volume and temperature must be positive.")
    if supersaturation_ratio <= 1:
        return math.inf
    ln_s = math.log(supersaturation_ratio)
    return 16.0 * math.pi * interfacial_energy_j_m2 ** 3 * molecular_volume_m3 ** 2 / (
        3.0 * (K_BOLTZMANN_J_K * temperature_k * ln_s) ** 2
    )


def classical_nucleation_rate(
    kinetic_prefactor: float,
    barrier_j: float,
    temperature_k: float,
) -> float:
    """Classical nucleation rate B = A exp(-ΔG*/kT)."""
    if kinetic_prefactor < 0 or temperature_k <= 0:
        raise ValueError("Prefactor must be non-negative and temperature positive.")
    if math.isinf(barrier_j):
        return 0.0
    if barrier_j < 0:
        raise ValueError("Nucleation barrier cannot be negative.")
    return kinetic_prefactor * math.exp(-barrier_j / (K_BOLTZMANN_J_K * temperature_k))


def heterogeneous_nucleation_rate(
    kinetic_prefactor: float,
    homogeneous_barrier_j: float,
    temperature_k: float,
    contact_angle_deg: float,
) -> float:
    phi = heterogeneous_surface_energy_factor(contact_angle_deg)
    return classical_nucleation_rate(kinetic_prefactor, phi * homogeneous_barrier_j, temperature_k)


def combined_diffusion_surface_growth_coefficient(
    diffusion_coefficient: float,
    surface_integration_coefficient: float,
) -> float:
    """Overall coefficient for resistances in series: 1/K = 1/k_d + 1/k_i."""
    if diffusion_coefficient <= 0 or surface_integration_coefficient <= 0:
        raise ValueError("Diffusion and surface-integration coefficients must be positive.")
    return 1.0 / (1.0 / diffusion_coefficient + 1.0 / surface_integration_coefficient)


def growth_control_regime(
    diffusion_coefficient: float,
    surface_integration_coefficient: float,
    ratio_threshold: float = 5.0,
) -> str:
    """Classify the dominant resistance in a two-resistance growth picture."""
    if diffusion_coefficient <= 0 or surface_integration_coefficient <= 0:
        raise ValueError("Growth coefficients must be positive.")
    ratio = diffusion_coefficient / surface_integration_coefficient
    if ratio >= ratio_threshold:
        return "surface-integration-controlled"
    if ratio <= 1.0 / ratio_threshold:
        return "diffusion-controlled"
    return "mixed-control"


def secondary_nucleation_risk(
    supersaturation_ratio: float,
    solids_present: bool,
    agitation_intensity: str = "moderate",
) -> dict[str, Any]:
    """Qualitative engineering screen for secondary nucleation mechanisms.

    This is deliberately not a fitted kinetic correlation. The chapter emphasizes
    that contact, attrition, breeding, crystal hardness, impurities and agitation
    materially change secondary nucleation, so a universal rate should not be
    fabricated without system-specific data.
    """
    agitation = agitation_intensity.strip().lower()
    if agitation not in {"low", "moderate", "high"}:
        raise ValueError("agitation_intensity must be low, moderate or high.")
    if not solids_present or supersaturation_ratio <= 1.0:
        level = "low"
    elif supersaturation_ratio < 1.05 and agitation == "low":
        level = "review"
    elif agitation == "high" or supersaturation_ratio >= 1.20:
        level = "high"
    else:
        level = "moderate"
    mechanisms = []
    if solids_present and supersaturation_ratio > 1.0:
        mechanisms += ["contact", "initial/needle breeding"]
    if solids_present and agitation == "high":
        mechanisms += ["attrition", "polycrystalline breeding"]
    return {
        "risk": level,
        "candidate_mechanisms": mechanisms,
        "kinetic_rate_available": False,
        "note": "Use calibrated secondary-nucleation kinetics for quantitative design.",
    }


def crystal_kinetics_capabilities() -> dict[str, Any]:
    return {
        "status": "engineering foundation; not yet coupled to FCC population balance",
        "growth": ["power-law", "Arrhenius power-law", "diffusion/surface resistance screen"],
        "nucleation": ["classical homogeneous", "classical heterogeneous", "empirical power-law", "secondary qualitative screen"],
        "secondary_mechanisms": ["contact", "attrition", "needle breeding", "polycrystalline breeding"],
        "requires_calibration": ["growth constants/exponents", "nucleation constants/exponents", "interfacial energy", "shape factors", "secondary nucleation kinetics"],
    }
