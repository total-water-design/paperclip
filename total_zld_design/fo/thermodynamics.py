"""Thermodynamic integration boundary for industrial FO calculations.

ZLD owns FO transport and process logic; it must not grow a duplicate aqueous
chemistry engine. The protocol below is the injection point for Suite Shared
Water Chemistry. The built-in linear scaler is deliberately a Phase-1 fallback
for cases where the caller already supplies inlet osmotic pressure.
"""
from __future__ import annotations

from typing import Any, Mapping, Protocol


class OsmoticPressureProvider(Protocol):
    def osmotic_pressure_bar(
        self,
        *,
        role: str,
        inlet_state: Mapping[str, Any],
        flow_m3_h: float,
        total_solute_kg_m3: float,
        concentration_factor: float,
    ) -> float:
        """Return bulk osmotic pressure for the current process state."""


def linear_osmotic_pressure_bar(
    inlet_osmotic_pressure_bar: float,
    inlet_total_solute_kg_m3: float,
    current_total_solute_kg_m3: float,
) -> float:
    """Phase-1 fallback using user-supplied inlet osmotic pressure.

    This is not a replacement for high-salinity activity/speciation chemistry.
    """
    if inlet_osmotic_pressure_bar < 0 or inlet_total_solute_kg_m3 < 0 or current_total_solute_kg_m3 < 0:
        raise ValueError("FO osmotic-pressure inputs cannot be negative.")
    if inlet_total_solute_kg_m3 == 0:
        return 0.0 if current_total_solute_kg_m3 == 0 else inlet_osmotic_pressure_bar
    return inlet_osmotic_pressure_bar * current_total_solute_kg_m3 / inlet_total_solute_kg_m3
