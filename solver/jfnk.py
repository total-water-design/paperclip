"""Jacobian-Free Newton-Krylov utilities for strongly coupled flowsheets.

The implementation is intentionally dependency-light beyond NumPy, which is
already required by the numerical/chemistry stack.  It operates only on a
scaled residual callback and never knows membrane or chemistry internals.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Sequence
import math
import numpy as np


@dataclass
class JFNKResult:
    x: list[float]
    converged: bool
    newton_iterations: int
    residual_norm: float
    function_evaluations: int
    gmres_iterations: int
    message: str


def _norm(v: np.ndarray) -> float:
    return float(np.linalg.norm(v))


def _gmres(matvec: Callable[[np.ndarray], np.ndarray], b: np.ndarray, *,
           tol: float = 1e-5, max_iter: int = 24) -> tuple[np.ndarray, int, float]:
    """Small restarted-free GMRES suitable for tear-stream systems."""
    n = int(b.size)
    beta = _norm(b)
    if beta <= tol:
        return np.zeros_like(b), 0, beta
    m = max(1, min(int(max_iter), n if n else 1))
    V = np.zeros((n, m + 1), dtype=float)
    H = np.zeros((m + 1, m), dtype=float)
    V[:, 0] = b / beta
    e1 = np.zeros(m + 1); e1[0] = beta
    best = np.zeros(n); best_res = beta
    for j in range(m):
        w = np.asarray(matvec(V[:, j]), dtype=float)
        for i in range(j + 1):
            H[i, j] = np.dot(V[:, i], w)
            w -= H[i, j] * V[:, i]
        H[j + 1, j] = _norm(w)
        if H[j + 1, j] > 1e-15:
            V[:, j + 1] = w / H[j + 1, j]
        y, *_ = np.linalg.lstsq(H[:j + 2, :j + 1], e1[:j + 2], rcond=None)
        x = V[:, :j + 1] @ y
        res = _norm(e1[:j + 2] - H[:j + 2, :j + 1] @ y)
        if res < best_res:
            best, best_res = x, res
        if res <= tol:
            return x, j + 1, res
        if H[j + 1, j] <= 1e-15:
            break
    return best, j + 1 if m else 0, best_res


def solve_jfnk(residual: Callable[[Sequence[float]], Sequence[float]], x0: Sequence[float], *,
               scales: Sequence[float] | None = None, residual_scales: Sequence[float] | None = None,
               project: Callable[[np.ndarray], np.ndarray] | None = None,
               max_newton: int = 14, gmres_max: int = 24, atol: float = 1e-8,
               rtol: float = 1e-7, fd_eps: float = 1e-7) -> JFNKResult:
    """Solve F(x)=0 without forming the Jacobian.

    * variables/residuals are scaled before Newton/GMRES;
    * J·v is approximated by finite differences;
    * a backtracking line search globalizes the Newton step;
    * ``project`` may enforce physical bounds before residual evaluation.
    """
    x = np.asarray(x0, dtype=float).copy()
    n = x.size
    xs = np.ones(n) if scales is None else np.maximum(np.abs(np.asarray(scales, dtype=float)), 1e-14)
    rs = np.ones(n) if residual_scales is None else np.maximum(np.abs(np.asarray(residual_scales, dtype=float)), 1e-14)
    fevals = 0; gmres_total = 0

    def eval_scaled(x_phys: np.ndarray) -> np.ndarray:
        nonlocal fevals
        xx = project(x_phys.copy()) if project else x_phys
        raw = np.asarray(residual(xx.tolist()), dtype=float)
        fevals += 1
        if raw.size != n or not np.all(np.isfinite(raw)):
            raise ValueError("JFNK residual returned an invalid/non-finite vector.")
        return raw / rs

    f = eval_scaled(x)
    f0 = max(_norm(f), 1e-30)
    for nit in range(1, int(max_newton) + 1):
        fnorm = _norm(f)
        if fnorm <= atol or fnorm <= rtol * f0:
            return JFNKResult(x.tolist(), True, nit - 1, fnorm, fevals, gmres_total, "converged")

        xhat = x / xs
        def jv(vhat: np.ndarray) -> np.ndarray:
            # Brown/Saad-style scale: perturb relative to current scaled state.
            vnorm = max(_norm(vhat), 1e-30)
            eps = fd_eps * max(1.0, _norm(xhat)) / vnorm
            xp = (xhat + eps * vhat) * xs
            return (eval_scaled(xp) - f) / eps

        step_hat, gm_it, _ = _gmres(jv, -f, tol=max(1e-8, min(0.2, 0.25 * fnorm)), max_iter=gmres_max)
        gmres_total += gm_it
        if not np.all(np.isfinite(step_hat)):
            return JFNKResult(x.tolist(), False, nit, fnorm, fevals, gmres_total, "GMRES produced a non-finite Newton step")

        merit0 = 0.5 * fnorm * fnorm
        accepted = False
        lam = 1.0
        for _ in range(10):
            trial = (xhat + lam * step_hat) * xs
            if project:
                trial = project(trial)
            try:
                ft = eval_scaled(trial)
            except (ValueError, FloatingPointError):
                lam *= 0.5; continue
            merit = 0.5 * _norm(ft) ** 2
            if merit < merit0 * (1.0 - 1e-4 * lam):
                x, f = trial, ft; accepted = True; break
            lam *= 0.5
        if not accepted:
            return JFNKResult(x.tolist(), False, nit, fnorm, fevals, gmres_total, "line search failed to reduce residual")

    return JFNKResult(x.tolist(), False, int(max_newton), _norm(f), fevals, gmres_total, "maximum Newton iterations reached")
