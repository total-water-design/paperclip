"""Dependency-free data models for the industrial FO engineering kernel."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Literal

Orientation = Literal["AL-DS", "AL-FS"]


@dataclass(frozen=True)
class FOSolutionState:
    """Bulk solution state supplied by process chemistry.

    Phase 1 intentionally accepts osmotic pressure as an explicit thermodynamic
    input. A later Shared Water Chemistry adapter can provide it from a canonical
    WaterState without duplicating aqueous chemistry inside the ZLD engine.
    ``solute_diffusivity_m2_s`` is an effective diffusivity for the dominant
    osmotic/draw solute used in concentration-polarization correlations.
    """

    flow_m3_h: float
    osmotic_pressure_bar: float
    total_solute_kg_m3: float
    solute_diffusivity_m2_s: float = 1.5e-9
    temperature_c: float = 25.0


@dataclass(frozen=True)
class FOMembrane:
    water_permeability_lmh_bar: float
    salt_permeability_lmh: float
    structural_parameter_um: float
    membrane_area_m2: float
    orientation: Orientation = "AL-DS"
    maximum_tmp_bar: float = 12.0


@dataclass(frozen=True)
class FOHydraulics:
    feed_velocity_m_s: float = 0.20
    draw_velocity_m_s: float = 0.20
    feed_hydraulic_diameter_mm: float = 0.80
    draw_hydraulic_diameter_mm: float = 0.80
    kinematic_viscosity_m2_s: float = 1.0e-6
    sherwood_coefficient: float = 0.20
    sherwood_re_exponent: float = 0.57
    sherwood_sc_exponent: float = 0.40
    feed_pressure_drop_bar: float = 0.50
    draw_pressure_drop_bar: float = 0.50
    pump_efficiency: float = 0.80


@dataclass(frozen=True)
class FOOperatingPoint:
    feed_applied_pressure_bar: float = 0.0
    segments: int = 20


@dataclass(frozen=True)
class LocalTransportResult:
    water_flux_lmh: float
    reverse_solute_flux_g_m2_h: float
    specific_reverse_solute_flux_g_l: float
    feed_membrane_osmotic_pressure_bar: float
    draw_membrane_osmotic_pressure_bar: float
    effective_driving_force_bar: float
    feed_cp_modulus: float
    draw_cp_modulus: float
    feed_mass_transfer_lmh: float
    draw_mass_transfer_lmh: float
    internal_mass_transfer_lmh: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
