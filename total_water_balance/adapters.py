from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

import shared_waterstream as sw

from .model import BalanceTerms


@dataclass(frozen=True, slots=True)
class SpecialistResult:
    """Minimal cross-app handoff consumed by Total Water Balance.

    Specialist applications own the transformation. Water Balance receives only
    authoritative input/output streams plus declared source/sink terms and audit
    metadata.
    """

    unit_id: str
    inputs: Mapping[str, sw.WaterStream]
    outputs: Mapping[str, sw.WaterStream]
    balance_terms: BalanceTerms = field(default_factory=BalanceTerms)
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unit_id = str(self.unit_id or "").strip()
        if not unit_id:
            raise ValueError("unit_id is required.")
        if any(not isinstance(stream, sw.WaterStream) for stream in self.inputs.values()):
            raise TypeError("SpecialistResult inputs must be canonical WaterStreams.")
        if any(not isinstance(stream, sw.WaterStream) for stream in self.outputs.values()):
            raise TypeError("SpecialistResult outputs must be canonical WaterStreams.")
        if not self.outputs:
            raise ValueError("SpecialistResult must expose at least one output stream.")
        object.__setattr__(self, "unit_id", unit_id)
        object.__setattr__(self, "inputs", dict(self.inputs))
        object.__setattr__(self, "outputs", dict(self.outputs))
        if not isinstance(self.balance_terms, BalanceTerms):
            object.__setattr__(self, "balance_terms", BalanceTerms.from_dict(self.balance_terms))
        object.__setattr__(self, "warnings", tuple(str(x) for x in self.warnings))
        object.__setattr__(self, "metadata", sw.FrozenDict(dict(self.metadata or {})).to_dict())

    def to_dict(self) -> dict:
        return {
            "unit_id": self.unit_id,
            "inputs": {key: stream.to_dict() for key, stream in self.inputs.items()},
            "outputs": {key: stream.to_dict() for key, stream in self.outputs.items()},
            "balance_terms": self.balance_terms.to_dict(),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


class SpecialistAdapter(Protocol):
    """Late-integration protocol; no specialist app is required to implement it yet."""

    application: str

    def solve(self, inputs: Mapping[str, sw.WaterStream]) -> SpecialistResult: ...


class StaticSpecialistAdapter:
    """Test/migration adapter for precomputed specialist results.

    This is intentionally not a physics engine. It is useful while specialist
    applications are adopting the common boundary contract on their own schedule.
    """

    def __init__(self, application: str, result: SpecialistResult):
        self.application = str(application or "").strip()
        if not self.application:
            raise ValueError("application is required.")
        self._result = result

    def solve(self, inputs: Mapping[str, sw.WaterStream]) -> SpecialistResult:
        supplied_ids = {key: stream.state_hash for key, stream in inputs.items()}
        expected_ids = {key: stream.state_hash for key, stream in self._result.inputs.items()}
        if supplied_ids != expected_ids:
            raise ValueError(
                "Static specialist adapter input state differs from the validated/precomputed result."
            )
        return self._result
