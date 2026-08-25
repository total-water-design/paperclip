from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

import shared_waterstream as sw


class FlowRole(str, Enum):
    """Semantic role of a stream edge in the facility balance."""

    FEED = "FEED"
    PRODUCT = "PRODUCT"
    WASTE = "WASTE"
    REUSE = "REUSE"
    RECYCLE = "RECYCLE"
    BYPASS = "BYPASS"
    INTERNAL = "INTERNAL"
    SLUDGE = "SLUDGE"
    SOLIDS = "SOLIDS"
    GAS = "GAS"
    LOSS = "LOSS"
    UTILITY = "UTILITY"


def _json_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    # Shared WaterStream's freezer is a convenient strict JSON-compatibility gate.
    return sw.FrozenDict(dict(value or {})).to_dict()


def _canonical_term_map(values: Mapping[str, float] | None, *, label: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in (values or {}).items():
        canonical = sw.validate_authoritative_component(str(key))
        amount = float(value)
        if not isfinite(amount):
            raise ValueError(f"{label}[{key}] must be finite.")
        if amount < 0.0:
            raise ValueError(f"{label}[{key}] cannot be negative.")
        out[canonical] = out.get(canonical, 0.0) + amount
    return out


def _finite_nonnegative(value: float, *, name: str) -> float:
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be finite.")
    if number < 0.0:
        raise ValueError(f"{name} cannot be negative.")
    return number


@dataclass(frozen=True, slots=True)
class BalanceTerms:
    """Owner-declared non-stream source/sink terms for one UnitOp boundary.

    Canonical components are expressed in mol/s. Prefer explicit WaterStream
    inlets/outlets whenever possible; these terms exist for reaction,
    accumulation and equivalent accounting that cannot be represented as a
    physical boundary stream.
    """

    generated_mol_s: Mapping[str, float] = field(default_factory=dict)
    consumed_mol_s: Mapping[str, float] = field(default_factory=dict)
    chemical_dose_mol_s: Mapping[str, float] = field(default_factory=dict)
    accumulation_mol_s: Mapping[str, float] = field(default_factory=dict)
    toth_generated_eq_s: float = 0.0
    toth_consumed_eq_s: float = 0.0
    toth_dose_eq_s: float = 0.0
    toth_accumulation_eq_s: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "generated_mol_s", _canonical_term_map(self.generated_mol_s, label="generated_mol_s"))
        object.__setattr__(self, "consumed_mol_s", _canonical_term_map(self.consumed_mol_s, label="consumed_mol_s"))
        object.__setattr__(self, "chemical_dose_mol_s", _canonical_term_map(self.chemical_dose_mol_s, label="chemical_dose_mol_s"))
        object.__setattr__(self, "accumulation_mol_s", _canonical_term_map(self.accumulation_mol_s, label="accumulation_mol_s"))
        for name in (
            "toth_generated_eq_s", "toth_consumed_eq_s",
            "toth_dose_eq_s", "toth_accumulation_eq_s",
        ):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))

    @property
    def is_zero(self) -> bool:
        return not (
            self.generated_mol_s or self.consumed_mol_s or self.chemical_dose_mol_s
            or self.accumulation_mol_s or self.toth_generated_eq_s
            or self.toth_consumed_eq_s or self.toth_dose_eq_s
            or self.toth_accumulation_eq_s
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_mol_s": dict(self.generated_mol_s),
            "consumed_mol_s": dict(self.consumed_mol_s),
            "chemical_dose_mol_s": dict(self.chemical_dose_mol_s),
            "accumulation_mol_s": dict(self.accumulation_mol_s),
            "toth_generated_eq_s": self.toth_generated_eq_s,
            "toth_consumed_eq_s": self.toth_consumed_eq_s,
            "toth_dose_eq_s": self.toth_dose_eq_s,
            "toth_accumulation_eq_s": self.toth_accumulation_eq_s,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "BalanceTerms":
        data = dict(payload or {})
        return cls(
            generated_mol_s=data.get("generated_mol_s") or {},
            consumed_mol_s=data.get("consumed_mol_s") or {},
            chemical_dose_mol_s=data.get("chemical_dose_mol_s") or {},
            accumulation_mol_s=data.get("accumulation_mol_s") or {},
            toth_generated_eq_s=data.get("toth_generated_eq_s", 0.0),
            toth_consumed_eq_s=data.get("toth_consumed_eq_s", 0.0),
            toth_dose_eq_s=data.get("toth_dose_eq_s", 0.0),
            toth_accumulation_eq_s=data.get("toth_accumulation_eq_s", 0.0),
        )


@dataclass(frozen=True, slots=True)
class ProcessNode:
    node_id: str
    name: str
    application: str
    process_type: str
    balance_terms: BalanceTerms = field(default_factory=BalanceTerms)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("node_id", "name", "application", "process_type"):
            value = str(getattr(self, name) or "").strip()
            if not value:
                raise ValueError(f"{name} is required.")
            object.__setattr__(self, name, value)
        if not isinstance(self.balance_terms, BalanceTerms):
            object.__setattr__(self, "balance_terms", BalanceTerms.from_dict(self.balance_terms))
        object.__setattr__(self, "metadata", _json_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "application": self.application,
            "process_type": self.process_type,
            "balance_terms": self.balance_terms.to_dict(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProcessNode":
        return cls(
            node_id=str(payload.get("node_id") or ""),
            name=str(payload.get("name") or ""),
            application=str(payload.get("application") or ""),
            process_type=str(payload.get("process_type") or ""),
            balance_terms=BalanceTerms.from_dict(payload.get("balance_terms")),
            metadata=payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class StreamEdge:
    edge_id: str
    stream_id: str
    source_node_id: str | None
    target_node_id: str | None
    role: FlowRole = FlowRole.INTERNAL
    label: str | None = None
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        edge_id = str(self.edge_id or "").strip()
        stream_id = str(self.stream_id or "").strip()
        if not edge_id or not stream_id:
            raise ValueError("edge_id and stream_id are required.")
        source = None if self.source_node_id is None else str(self.source_node_id).strip()
        target = None if self.target_node_id is None else str(self.target_node_id).strip()
        if not source and not target:
            raise ValueError("A stream edge must connect to at least one process node.")
        role = self.role if isinstance(self.role, FlowRole) else FlowRole(str(self.role))
        object.__setattr__(self, "edge_id", edge_id)
        object.__setattr__(self, "stream_id", stream_id)
        object.__setattr__(self, "source_node_id", source or None)
        object.__setattr__(self, "target_node_id", target or None)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "label", None if self.label is None else str(self.label))
        object.__setattr__(self, "tags", tuple(str(x) for x in self.tags))
        object.__setattr__(self, "metadata", _json_mapping(self.metadata))

    @property
    def is_external_input(self) -> bool:
        return self.source_node_id is None and self.target_node_id is not None

    @property
    def is_external_output(self) -> bool:
        return self.source_node_id is not None and self.target_node_id is None

    @property
    def is_internal(self) -> bool:
        return self.source_node_id is not None and self.target_node_id is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "stream_id": self.stream_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "role": self.role.value,
            "label": self.label,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StreamEdge":
        return cls(
            edge_id=str(payload.get("edge_id") or ""),
            stream_id=str(payload.get("stream_id") or ""),
            source_node_id=payload.get("source_node_id"),
            target_node_id=payload.get("target_node_id"),
            role=FlowRole(str(payload.get("role") or FlowRole.INTERNAL.value)),
            label=payload.get("label"),
            tags=tuple(payload.get("tags") or ()),
            metadata=payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class FacilityModel:
    facility_id: str
    name: str
    nodes: tuple[ProcessNode, ...]
    edges: tuple[StreamEdge, ...]
    streams: tuple[sw.WaterStream, ...]
    project_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1.0"

    def __post_init__(self) -> None:
        facility_id = str(self.facility_id or "").strip()
        name = str(self.name or "").strip()
        if not facility_id or not name:
            raise ValueError("facility_id and name are required.")
        object.__setattr__(self, "facility_id", facility_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "nodes", tuple(x if isinstance(x, ProcessNode) else ProcessNode.from_dict(x) for x in self.nodes))
        object.__setattr__(self, "edges", tuple(x if isinstance(x, StreamEdge) else StreamEdge.from_dict(x) for x in self.edges))
        if any(not isinstance(stream, sw.WaterStream) for stream in self.streams):
            raise TypeError("FacilityModel streams must be canonical shared_waterstream.WaterStream objects.")
        object.__setattr__(self, "streams", tuple(self.streams))
        object.__setattr__(self, "project_id", None if self.project_id is None else str(self.project_id))
        object.__setattr__(self, "metadata", _json_mapping(self.metadata))
        if self.schema_version != "0.1.0":
            raise ValueError(f"Unsupported Total Water Balance model schema {self.schema_version!r}.")

    @property
    def node_map(self) -> dict[str, ProcessNode]:
        return {node.node_id: node for node in self.nodes}

    @property
    def edge_map(self) -> dict[str, StreamEdge]:
        return {edge.edge_id: edge for edge in self.edges}

    @property
    def stream_map(self) -> dict[str, sw.WaterStream]:
        return {stream.stream_id: stream for stream in self.streams}

    @property
    def model_hash(self) -> str:
        return sw.content_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "twds.total-water-balance-model",
            "version": self.schema_version,
            "facility_id": self.facility_id,
            "name": self.name,
            "project_id": self.project_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "streams": [stream.to_dict() for stream in self.streams],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FacilityModel":
        if payload.get("schema") != "twds.total-water-balance-model":
            raise ValueError("Unsupported Total Water Balance model schema.")
        if str(payload.get("version")) != "0.1.0":
            raise ValueError("Unsupported Total Water Balance model version.")
        return cls(
            facility_id=str(payload.get("facility_id") or ""),
            name=str(payload.get("name") or ""),
            project_id=payload.get("project_id"),
            nodes=tuple(ProcessNode.from_dict(x) for x in (payload.get("nodes") or ())),
            edges=tuple(StreamEdge.from_dict(x) for x in (payload.get("edges") or ())),
            streams=tuple(sw.WaterStream.from_dict(x) for x in (payload.get("streams") or ())),
            metadata=payload.get("metadata") or {},
        )
