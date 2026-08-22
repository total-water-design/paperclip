"""Reusable numerical-solver utilities for CalcOsPower.

These routines accelerate convergence only; they do not define process physics.
"""
from .fixed_point import AndersonMixer, aitken_delta2_scalar, residual_norm
from .line_search import bounded_backtracking_line_search, bounded_step
from .continuation import ThermodynamicStateCache, water_state_signature, water_state_snapshot
from .diagnostics import SolverTrace
from .root_scalar import brent_root
from .jfnk import solve_jfnk, JFNKResult

__all__ = [
    "AndersonMixer", "aitken_delta2_scalar", "residual_norm",
    "bounded_backtracking_line_search", "bounded_step",
    "ThermodynamicStateCache", "water_state_signature", "water_state_snapshot",
    "SolverTrace", "brent_root", "solve_jfnk", "JFNKResult",
]
