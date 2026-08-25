"""Total Water Balance application engine.

This package is intentionally independent of Suite Core and specialist-app
runtime code. It consumes the canonical ``shared_waterstream`` contract and
provides facility-level topology, balance closure, recycle orchestration and
presentation payloads for later TWDS integration.
"""
from .model import BalanceTerms, FacilityModel, FlowRole, ProcessNode, StreamEdge
from .graph import FacilityGraph, GraphIssue, GraphValidationError
from .balance import (
    BalanceEngine,
    ClosureDiagnostic,
    ComponentBalance,
    FacilityBalanceReport,
    UnitBalanceReport,
)
from .recycle import (
    FixedPointRecycleSolver,
    RecycleIteration,
    RecycleResult,
    RecycleSolverError,
    normalized_stream_residual,
)
from .adapters import SpecialistAdapter, SpecialistResult, StaticSpecialistAdapter
from .presentation import build_dashboard_payload, build_sankey_payload, build_stream_table

__version__ = "0.1.0"

__all__ = [
    "BalanceEngine", "BalanceTerms", "ClosureDiagnostic", "ComponentBalance",
    "FacilityBalanceReport", "FacilityGraph", "FacilityModel",
    "FixedPointRecycleSolver", "FlowRole", "GraphIssue", "GraphValidationError",
    "ProcessNode", "RecycleIteration", "RecycleResult", "RecycleSolverError",
    "SpecialistAdapter", "SpecialistResult", "StaticSpecialistAdapter",
    "StreamEdge", "UnitBalanceReport", "build_dashboard_payload",
    "build_sankey_payload", "build_stream_table", "normalized_stream_residual",
]
