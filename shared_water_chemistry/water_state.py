"""Canonical cross-application water state for Total Water Design Suite.

The handoff object carries analytical composition and conserved chemistry totals.
Equilibrium/speciation is derived data.  Values are never rounded for transport;
rounding belongs only in UI/report presentation.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from water_chemistry import normalize_composition

SCHEMA_ID = "twds.water-state"
SCHEMA_VERSION = 1


def _optional_float(value: object | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


@dataclass(slots=True)
class WaterState:
    """Authoritative water state exchanged between Suite applications.

    ``composition_mg_l`` contains analytical component totals on the established
    Total Water Design Suite input basis.  pH is hydrogen activity and is kept at
    solver precision.  TA and CT are mol/kg-water so they remain suitable for
    equilibrium reconstruction after a process or temperature change.
    """

    composition_mg_l: dict[str, float]
    temperature_c: float = 25.0
    pressure_bar: float = 1.01325
    ph: float | None = None
    total_alkalinity_mol_kg: float | None = None
    total_inorganic_carbon_mol_kg: float | None = None
    source_application: str | None = None
    source_process: str | None = None
    equilibrium: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def normalized(self) -> "WaterState":
        """Return a validated copy using the Suite's canonical ion dictionary."""
        if int(self.schema_version) != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported water-state schema version {self.schema_version}; "
                f"expected {SCHEMA_VERSION}."
            )
        temperature = float(self.temperature_c)
        pressure = float(self.pressure_bar)
        if not (-5.0 <= temperature <= 200.0):
            raise ValueError("Water-state temperature is outside the supported engineering range.")
        if pressure < 0.0:
            raise ValueError("Water-state pressure cannot be negative.")
        ph = _optional_float(self.ph)
        if ph is not None and not (0.0 <= ph <= 14.0):
            raise ValueError("Water-state pH must be between 0 and 14.")
        ta = _optional_float(self.total_alkalinity_mol_kg)
        ct = _optional_float(self.total_inorganic_carbon_mol_kg)
        if ta is not None and not (-10.0 <= ta <= 10.0):
            raise ValueError("Water-state total alkalinity is outside the supported range.")
        if ct is not None and ct < 0.0:
            raise ValueError("Water-state total inorganic carbon cannot be negative.")
        return replace(
            self,
            composition_mg_l=normalize_composition(self.composition_mg_l),
            temperature_c=temperature,
            pressure_bar=pressure,
            ph=ph,
            total_alkalinity_mol_kg=ta,
            total_inorganic_carbon_mol_kg=ct,
            equilibrium=dict(self.equilibrium or {}),
            metadata=dict(self.metadata or {}),
            schema_version=SCHEMA_VERSION,
        )

    @property
    def equilibrium_basis_count(self) -> int:
        return sum(
            value is not None
            for value in (
                self.ph,
                self.total_alkalinity_mol_kg,
                self.total_inorganic_carbon_mol_kg,
            )
        )

    def to_handoff(self) -> dict[str, Any]:
        """Serialize without UI rounding for handoff to another Suite app."""
        state = self.normalized()
        return {
            "schema": SCHEMA_ID,
            "version": SCHEMA_VERSION,
            "state": {
                "composition_mg_l": dict(state.composition_mg_l),
                "temperature_c": state.temperature_c,
                "pressure_bar": state.pressure_bar,
                "ph": state.ph,
                "total_alkalinity_mol_kg": state.total_alkalinity_mol_kg,
                "total_inorganic_carbon_mol_kg": state.total_inorganic_carbon_mol_kg,
                "source_application": state.source_application,
                "source_process": state.source_process,
                "equilibrium": dict(state.equilibrium),
                "metadata": dict(state.metadata),
            },
        }

    @classmethod
    def from_handoff(cls, payload: Mapping[str, Any]) -> "WaterState":
        """Load and validate a Suite water-state handoff payload."""
        if payload.get("schema") != SCHEMA_ID:
            raise ValueError(f"Unsupported water-state schema {payload.get('schema')!r}.")
        version = int(payload.get("version", -1))
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported water-state schema version {version}; expected {SCHEMA_VERSION}."
            )
        raw = payload.get("state")
        if not isinstance(raw, Mapping):
            raise ValueError("Water-state handoff is missing its state mapping.")
        return cls(
            composition_mg_l=dict(raw.get("composition_mg_l") or {}),
            temperature_c=float(raw.get("temperature_c", 25.0)),
            pressure_bar=float(raw.get("pressure_bar", 1.01325)),
            ph=_optional_float(raw.get("ph")),
            total_alkalinity_mol_kg=_optional_float(
                raw.get("total_alkalinity_mol_kg")
            ),
            total_inorganic_carbon_mol_kg=_optional_float(
                raw.get("total_inorganic_carbon_mol_kg")
            ),
            source_application=raw.get("source_application"),
            source_process=raw.get("source_process"),
            equilibrium=dict(raw.get("equilibrium") or {}),
            metadata=dict(raw.get("metadata") or {}),
            schema_version=version,
        ).normalized()
