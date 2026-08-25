"""Solution-property utilities for ZLD concentration and crystallization design.

The functions in this module are deliberately generic and dependency-free. They
capture the concentration, saturation and thermal-property bookkeeping needed by
ZLD equipment models without embedding a second aqueous-equilibrium engine.
Rigorous electrolyte activities, speciation and osmotic pressure remain owned by
Shared Water Chemistry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class SaturationState:
    concentration: float
    solubility: float
    saturation_ratio: float
    relative_supersaturation: float
    absolute_supersaturation: float
    state: str


@dataclass(frozen=True)
class SolutionPropertyPoint:
    temperature_c: float
    concentration: float
    density_kg_m3: float | None = None
    viscosity_pa_s: float | None = None
    diffusivity_m2_s: float | None = None
    heat_capacity_kj_kg_k: float | None = None


def mass_fraction_from_solute_per_solvent(solute_mass: float, solvent_mass: float) -> float:
    if solute_mass < 0 or solvent_mass < 0 or solute_mass + solvent_mass <= 0:
        raise ValueError("Solute and solvent masses must be non-negative with positive total mass.")
    return solute_mass / (solute_mass + solvent_mass)


def solute_per_solvent_from_mass_fraction(mass_fraction: float) -> float:
    if not 0 <= mass_fraction < 1:
        raise ValueError("Mass fraction must be in [0, 1).")
    return mass_fraction / max(1.0 - mass_fraction, 1.0e-30)


def mass_fraction_to_g_per_kg_solvent(mass_fraction: float) -> float:
    return 1000.0 * solute_per_solvent_from_mass_fraction(mass_fraction)


def g_per_kg_solvent_to_mass_fraction(g_per_kg_solvent: float) -> float:
    if g_per_kg_solvent < 0:
        raise ValueError("Concentration cannot be negative.")
    ratio = g_per_kg_solvent / 1000.0
    return ratio / (1.0 + ratio)


def mass_fraction_to_g_per_l_solution(mass_fraction: float, density_kg_m3: float) -> float:
    if not 0 <= mass_fraction <= 1 or density_kg_m3 <= 0:
        raise ValueError("Mass fraction must be [0,1] and density must be positive.")
    return mass_fraction * density_kg_m3


def g_per_l_solution_to_mass_fraction(g_per_l: float, density_kg_m3: float) -> float:
    if g_per_l < 0 or density_kg_m3 <= 0:
        raise ValueError("Concentration must be non-negative and density positive.")
    value = g_per_l / density_kg_m3
    if value > 1:
        raise ValueError("Solute concentration exceeds solution mass implied by density.")
    return value


def mole_fraction_binary(solute_mass_kg: float, solvent_mass_kg: float, solute_mw_g_mol: float, solvent_mw_g_mol: float = 18.01528) -> float:
    if min(solute_mass_kg, solvent_mass_kg, solute_mw_g_mol, solvent_mw_g_mol) < 0 or solute_mw_g_mol == 0 or solvent_mw_g_mol == 0:
        raise ValueError("Masses must be non-negative and molecular weights positive.")
    n_solute = solute_mass_kg * 1000.0 / solute_mw_g_mol
    n_solvent = solvent_mass_kg * 1000.0 / solvent_mw_g_mol
    total = n_solute + n_solvent
    if total <= 0:
        raise ValueError("Total moles must be positive.")
    return n_solute / total


def saturation_state(concentration: float, solubility: float, tolerance: float = 1.0e-9) -> SaturationState:
    if concentration < 0 or solubility <= 0:
        raise ValueError("Concentration must be non-negative and solubility positive.")
    ratio = concentration / solubility
    rel = ratio - 1.0
    absolute = concentration - solubility
    if abs(rel) <= tolerance:
        state = "saturated"
    elif rel < 0:
        state = "undersaturated"
    else:
        state = "supersaturated"
    return SaturationState(concentration, solubility, ratio, rel, absolute, state)


def interpolate_property(temperature_c: float, temperatures_c: Sequence[float], values: Sequence[float], *, clamp: bool = False) -> float:
    if len(temperatures_c) != len(values) or len(values) < 2:
        raise ValueError("Property table requires at least two matching temperature/value points.")
    pairs = sorted((float(t), float(v)) for t, v in zip(temperatures_c, values))
    ts = [p[0] for p in pairs]
    vs = [p[1] for p in pairs]
    if temperature_c < ts[0]:
        if clamp:
            return vs[0]
        raise ValueError("Temperature below tabulated property range.")
    if temperature_c > ts[-1]:
        if clamp:
            return vs[-1]
        raise ValueError("Temperature above tabulated property range.")
    for i in range(len(ts) - 1):
        if ts[i] <= temperature_c <= ts[i + 1]:
            f = (temperature_c - ts[i]) / (ts[i + 1] - ts[i])
            return vs[i] + f * (vs[i + 1] - vs[i])
    return vs[-1]


def additive_volume_density_kg_m3(solute_mass_fraction: float, solute_density_kg_m3: float, solvent_density_kg_m3: float) -> float:
    """Estimate solution density by additive specific volumes.

    1/rho_solution = w_solute/rho_solute + w_solvent/rho_solvent.
    This is a fallback estimate only; measured/correlated solution density is preferred.
    """
    if not 0 <= solute_mass_fraction <= 1:
        raise ValueError("Solute mass fraction must be in [0, 1].")
    if min(solute_density_kg_m3, solvent_density_kg_m3) <= 0:
        raise ValueError("Component densities must be positive.")
    w_s = solute_mass_fraction
    w_w = 1.0 - w_s
    return 1.0 / (w_s / solute_density_kg_m3 + w_w / solvent_density_kg_m3)


def ideal_mixture_heat_capacity_kj_kg_k(mass_fractions: Iterable[float], component_cp_kj_kg_k: Iterable[float]) -> float:
    xs = [float(x) for x in mass_fractions]
    cps = [float(x) for x in component_cp_kj_kg_k]
    if len(xs) != len(cps) or not xs:
        raise ValueError("Mass-fraction and heat-capacity arrays must have equal non-zero length.")
    if any(x < 0 for x in xs) or any(cp <= 0 for cp in cps):
        raise ValueError("Mass fractions must be non-negative and heat capacities positive.")
    total = sum(xs)
    if abs(total - 1.0) > 1.0e-9:
        raise ValueError("Mass fractions must sum to one.")
    return sum(x * cp for x, cp in zip(xs, cps))


def watson_latent_heat_kj_kg(reference_latent_heat_kj_kg: float, reference_temperature_k: float, target_temperature_k: float, critical_temperature_k: float) -> float:
    """Watson correlation for latent heat away from a known reference point."""
    if min(reference_latent_heat_kj_kg, reference_temperature_k, target_temperature_k, critical_temperature_k) <= 0:
        raise ValueError("Watson-correlation inputs must be positive.")
    if max(reference_temperature_k, target_temperature_k) >= critical_temperature_k:
        raise ValueError("Reference and target temperatures must remain below critical temperature.")
    ratio = (1.0 - target_temperature_k / critical_temperature_k) / (1.0 - reference_temperature_k / critical_temperature_k)
    return reference_latent_heat_kj_kg * ratio ** 0.38


def solution_property_capabilities() -> dict:
    return {
        "concentration_bases": ["mass_fraction", "g_per_kg_solvent", "g_per_l_solution", "mole_fraction_binary"],
        "saturation_metrics": ["saturation_ratio", "relative_supersaturation", "absolute_supersaturation"],
        "properties": ["density", "viscosity", "diffusivity", "heat_capacity", "latent_heat", "heat_of_solution", "heat_of_crystallization"],
        "implemented": [
            "concentration conversion",
            "saturation-state bookkeeping",
            "tabular property interpolation",
            "additive-volume density fallback",
            "ideal-mixture heat-capacity fallback",
            "Watson latent-heat correlation",
        ],
        "preferred_sources": {
            "electrolyte_thermodynamics": "Shared Water Chemistry",
            "density_viscosity_diffusivity": "measured or validated concentration/temperature correlations",
            "solubility": "compound-specific solubility curves with temperature and solid-phase identity",
            "enthalpy": "compound-specific enthalpy/heat-of-solution data",
        },
        "warning": "Fallback property estimates are not substitutes for validated concentrated-electrolyte data in production ZLD design.",
    }
