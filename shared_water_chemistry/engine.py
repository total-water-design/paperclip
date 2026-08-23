"""Shared chemistry facade used by Total Water Design Suite applications.

This module intentionally delegates thermodynamics to the existing validated
``advanced_chemistry`` and ``water_chemistry`` modules.  It establishes a stable
cross-application contract without duplicating equations.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from advanced_chemistry import equilibrium_charge_report, solve_carbonate_state
from water_chemistry import normalize_composition

from .water_state import WaterState


def equilibrate(state: WaterState) -> WaterState:
    """Resolve a canonical water state using the existing advanced chemistry engine.

    If TA and CT are available they are treated as conserved analytical totals and
    pH is re-solved.  Otherwise the available two-of-three {pH, TA, CT} basis is
    passed through.  This preference prevents a rounded/stale upstream pH from
    overriding mass-conserved chemistry after a process handoff.
    """
    s = state.normalized()
    ph = s.ph
    ta = s.total_alkalinity_mol_kg
    ct = s.total_inorganic_carbon_mol_kg

    if sum(value is not None for value in (ph, ta, ct)) < 2:
        raise ValueError(
            "Shared chemistry equilibrium requires at least two of pH, total "
            "alkalinity (TA), and total inorganic carbon (CT)."
        )

    if ta is not None and ct is not None:
        basis = "TA+CT -> pH"
        solved = solve_carbonate_state(
            s.composition_mg_l,
            s.temperature_c,
            total_alkalinity_mol_kg=ta,
            total_inorganic_carbon_mol_kg=ct,
        )
    elif ph is not None and ct is not None:
        basis = "pH+CT -> TA"
        solved = solve_carbonate_state(
            s.composition_mg_l,
            s.temperature_c,
            ph=ph,
            total_inorganic_carbon_mol_kg=ct,
        )
    else:
        basis = "pH+TA -> CT"
        solved = solve_carbonate_state(
            s.composition_mg_l,
            s.temperature_c,
            ph=ph,
            total_alkalinity_mol_kg=ta,
        )

    charge = equilibrium_charge_report(solved, s.temperature_c)
    composition = normalize_composition(solved.get("composition") or s.composition_mg_l)
    equilibrium = {
        "engine": "advanced_chemistry.solve_carbonate_state",
        "basis": basis,
        "state": solved,
        "charge_report": charge,
    }
    return replace(
        s,
        composition_mg_l=composition,
        ph=float(solved["ph"]),
        total_alkalinity_mol_kg=float(solved["total_alkalinity_mol_kg"]),
        total_inorganic_carbon_mol_kg=float(
            solved["total_inorganic_carbon_mol_kg"]
        ),
        equilibrium=equilibrium,
    )


def recalculate_after_process_change(
    state: WaterState,
    *,
    composition_mg_l: Mapping[str, float] | None = None,
    temperature_c: float | None = None,
    pressure_bar: float | None = None,
    total_alkalinity_mol_kg: float | None = None,
    total_inorganic_carbon_mol_kg: float | None = None,
    source_application: str | None = None,
    source_process: str | None = None,
) -> WaterState:
    """Apply a process change and recompute pH from analytical TA + CT.

    The caller must supply changed TA/CT when the process adds/removes acid,
    base, inorganic carbon, or another alkalinity contributor.  Existing totals
    are preserved only when the caller leaves them unchanged.
    """
    s = state.normalized()
    ta = (
        s.total_alkalinity_mol_kg
        if total_alkalinity_mol_kg is None
        else float(total_alkalinity_mol_kg)
    )
    ct = (
        s.total_inorganic_carbon_mol_kg
        if total_inorganic_carbon_mol_kg is None
        else float(total_inorganic_carbon_mol_kg)
    )
    if ta is None or ct is None:
        raise ValueError(
            "Process-change recalculation requires analytical TA and CT so pH "
            "can be recomputed rather than copied from the upstream app."
        )
    changed = replace(
        s,
        composition_mg_l=(
            dict(s.composition_mg_l)
            if composition_mg_l is None
            else dict(composition_mg_l)
        ),
        temperature_c=s.temperature_c if temperature_c is None else float(temperature_c),
        pressure_bar=s.pressure_bar if pressure_bar is None else float(pressure_bar),
        ph=None,
        total_alkalinity_mol_kg=ta,
        total_inorganic_carbon_mol_kg=ct,
        source_application=source_application or s.source_application,
        source_process=source_process or s.source_process,
        equilibrium={},
    )
    return equilibrate(changed)


def prepare_handoff(
    state: WaterState,
    *,
    source_application: str,
    source_process: str | None = None,
    destination_application: str | None = None,
) -> dict:
    """Return the canonical, high-precision payload sent between applications."""
    s = state.normalized()
    if s.equilibrium_basis_count >= 2:
        s = equilibrate(s)
    metadata = dict(s.metadata)
    if destination_application:
        metadata["destination_application"] = destination_application
    s = replace(
        s,
        source_application=source_application,
        source_process=source_process or s.source_process,
        metadata=metadata,
    )
    return s.to_handoff()


def receive_handoff(payload: Mapping[str, object]) -> WaterState:
    """Read a canonical handoff.  No display rounding is applied."""
    return WaterState.from_handoff(payload)
