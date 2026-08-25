from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable

import shared_waterstream as sw


class RecycleSolverError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RecycleIteration:
    iteration: int
    residual_norm: float
    flow_m3_s: float
    toth_eq_s: float


@dataclass(frozen=True, slots=True)
class RecycleResult:
    converged: bool
    iterations: int
    residual_norm: float
    stream: sw.WaterStream
    history: tuple[RecycleIteration, ...]
    message: str


def _scale(delta: float, a: float, b: float, floor: float) -> float:
    return abs(delta) / max(abs(a), abs(b), floor)


def _require_generic_aqueous(stream: sw.WaterStream, *, label: str) -> None:
    if not isinstance(stream, sw.WaterStream):
        raise RecycleSolverError(f"{label} must be a Shared WaterStream v0.6 object.")
    if stream.phase is not sw.StreamPhase.AQUEOUS:
        raise RecycleSolverError(
            f"Generic recycle convergence currently supports pure AQUEOUS tear streams only; {label} is {stream.phase.value}."
        )
    if stream.tracked_quantities or stream.extensions:
        raise RecycleSolverError(
            f"{label} carries tracked quantities/extensions. Provide an owner-specific recycle solver/transformer rather than ignoring their convergence state."
        )


def normalized_stream_residual(a: sw.WaterStream, b: sw.WaterStream) -> float:
    """Maximum normalized residual across authoritative aqueous tear-stream state."""
    _require_generic_aqueous(a, label="old tear stream")
    _require_generic_aqueous(b, label="new tear stream")
    if a.chemistry_policy.to_dict() != b.chemistry_policy.to_dict():
        raise RecycleSolverError("Recycle states carry different chemistry_policy values.")
    values = [
        _scale(a.flow_m3_s - b.flow_m3_s, a.flow_m3_s, b.flow_m3_s, 1.0e-12),
        _scale(a.toth_eq_s - b.toth_eq_s, a.toth_eq_s, b.toth_eq_s, 1.0e-12),
        _scale(a.temperature_c - b.temperature_c, a.temperature_c, b.temperature_c, 1.0),
        _scale(a.pressure_bar - b.pressure_bar, a.pressure_bar, b.pressure_bar, 1.0e-6),
    ]
    for key in set(a.component_totals_mol_s) | set(b.component_totals_mol_s):
        av = float(a.component_totals_mol_s.get(key, 0.0))
        bv = float(b.component_totals_mol_s.get(key, 0.0))
        values.append(_scale(av - bv, av, bv, 1.0e-18))
    return max(values or [0.0])


def _relax_aqueous(old: sw.WaterStream, new: sw.WaterStream, damping: float) -> sw.WaterStream:
    _require_generic_aqueous(old, label="old tear stream")
    _require_generic_aqueous(new, label="new tear stream")
    if old.chemistry_policy.to_dict() != new.chemistry_policy.to_dict():
        raise RecycleSolverError("Cannot relax recycle states with different chemistry_policy values.")
    if damping >= 1.0:
        return new
    components = {
        key: float(old.component_totals_mol_s.get(key, 0.0))
        + damping * (
            float(new.component_totals_mol_s.get(key, 0.0))
            - float(old.component_totals_mol_s.get(key, 0.0))
        )
        for key in set(old.component_totals_mol_s) | set(new.component_totals_mol_s)
    }
    return sw.WaterStream(
        stream_id=old.stream_id,
        temperature_c=old.temperature_c + damping * (new.temperature_c - old.temperature_c),
        pressure_bar=old.pressure_bar + damping * (new.pressure_bar - old.pressure_bar),
        component_totals_mol_s=sw.FrozenDict(components),
        toth_eq_s=old.toth_eq_s + damping * (new.toth_eq_s - old.toth_eq_s),
        phase=sw.StreamPhase.AQUEOUS,
        chemistry_policy=old.chemistry_policy,
        diagnostics=sw.StreamDiagnostics(
            sw.FrozenDict({"recycle_relaxation": damping}),
            ("ChemistryCertificate intentionally invalidated during recycle relaxation.",),
        ),
        chemistry_certificate=None,
        provenance=(sw.ProvenanceRecord(
            source_type="recycle_solver",
            source_id=old.stream_id,
            application="total-water-balance",
            process="fixed_point_relaxation",
            engine_version="total-water-balance/0.1.0",
            parent_stream_ids=(old.stream_id, new.stream_id),
        ),),
        aqueous_volume_flow_m3_s=old.flow_m3_s + damping * (new.flow_m3_s - old.flow_m3_s),
    )


class FixedPointRecycleSolver:
    """Generic fail-closed fixed-point solver for pure-aqueous recycle tear streams.

    Specialist applications remain responsible for their process map. Total Water
    Balance only iterates the supplied ``mapping(tear_stream) -> new_tear_stream``.
    """

    def __init__(
        self,
        *,
        tolerance: float = 1.0e-9,
        max_iterations: int = 500,
        damping: float = 1.0,
    ):
        self.tolerance = float(tolerance)
        self.max_iterations = int(max_iterations)
        self.damping = float(damping)
        if not isfinite(self.tolerance) or self.tolerance <= 0:
            raise ValueError("tolerance must be finite and positive.")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1.")
        if not isfinite(self.damping) or not 0.0 < self.damping <= 1.0:
            raise ValueError("damping must be in (0, 1].")

    def solve(
        self,
        initial_guess: sw.WaterStream,
        mapping: Callable[[sw.WaterStream], sw.WaterStream],
    ) -> RecycleResult:
        _require_generic_aqueous(initial_guess, label="initial recycle guess")
        guess = initial_guess
        history: list[RecycleIteration] = []
        last_candidate = initial_guess
        for iteration in range(1, self.max_iterations + 1):
            candidate = mapping(guess)
            _require_generic_aqueous(candidate, label="recycle mapping result")
            residual = normalized_stream_residual(guess, candidate)
            if not isfinite(residual):
                raise RecycleSolverError("Recycle mapping produced a non-finite convergence residual.")
            history.append(RecycleIteration(
                iteration=iteration,
                residual_norm=residual,
                flow_m3_s=candidate.flow_m3_s,
                toth_eq_s=candidate.toth_eq_s,
            ))
            last_candidate = candidate
            if residual <= self.tolerance:
                return RecycleResult(
                    converged=True,
                    iterations=iteration,
                    residual_norm=residual,
                    stream=candidate,
                    history=tuple(history),
                    message="Recycle tear stream converged within configured tolerance.",
                )
            guess = _relax_aqueous(guess, candidate, self.damping)
        return RecycleResult(
            converged=False,
            iterations=self.max_iterations,
            residual_norm=history[-1].residual_norm,
            stream=last_candidate,
            history=tuple(history),
            message=(
                f"Recycle tear stream did not converge within {self.max_iterations} iterations; "
                f"final normalized residual is {history[-1].residual_norm:.6g}."
            ),
        )
