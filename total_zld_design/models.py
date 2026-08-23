"""Small dependency-free data structures for Total ZLD Design."""

from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class WarningMessage:
    code: str
    severity: str
    title: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stream:
    name: str
    flow_m3_h: float | None = None
    tds_mg_l: float | None = None
    temperature_c: float | None = None
    solids_t_h: float | None = None
    phase: str = "liquid"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CalculationResult:
    mode: str
    model_status: str
    model_version: str
    inputs: dict[str, Any]
    summary: dict[str, Any]
    modules: dict[str, Any] = field(default_factory=dict)
    streams: list[Stream] = field(default_factory=list)
    warnings: list[WarningMessage] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["streams"] = [s.to_dict() for s in self.streams]
        d["warnings"] = [w.to_dict() for w in self.warnings]
        return d
