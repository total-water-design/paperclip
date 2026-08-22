from __future__ import annotations
import math
from typing import Iterable, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


def residual_norm(values: Iterable[float]) -> float:
    vals=[float(v) for v in values]
    return math.sqrt(sum(v*v for v in vals))


def aitken_delta2_scalar(x0: float, x1: float, x2: float, *, denom_tol: float = 1e-14) -> float | None:
    den=float(x2)-2.0*float(x1)+float(x0)
    if abs(den) <= denom_tol:
        return None
    return float(x0) - (float(x1)-float(x0))**2/den


class AndersonMixer:
    """Small-memory Anderson acceleration for fixed-point iterations.

    The class only proposes the next state. The process solver remains responsible
    for physical bounds, residual acceptance, and conservative fallback.
    """
    def __init__(self, memory: int = 4, regularization: float = 1e-10):
        self.memory=max(1,int(memory))
        self.regularization=float(regularization)
        self._x=[]
        self._g=[]
        self._f=[]

    def reset(self) -> None:
        self._x.clear(); self._g.clear(); self._f.clear()

    @property
    def history(self) -> int:
        return len(self._x)

    def propose(self, x: Sequence[float], gx: Sequence[float]) -> list[float] | None:
        xv=[float(v) for v in x]; gv=[float(v) for v in gx]
        if len(xv)!=len(gv) or not xv:
            return None
        fv=[g-v for g,v in zip(gv,xv)]
        self._x.append(xv); self._g.append(gv); self._f.append(fv)
        keep=self.memory+1
        if len(self._x)>keep:
            self._x=self._x[-keep:]; self._g=self._g[-keep:]; self._f=self._f[-keep:]
        # Need at least two residuals. Without NumPy, leave the process solver on
        # its existing adaptive-relaxation path rather than introduce a fragile
        # handwritten least-squares implementation.
        if np is None or len(self._f)<2:
            return None
        m=min(self.memory,len(self._f)-1)
        f_hist=np.asarray(self._f[-(m+1):],dtype=float)
        g_hist=np.asarray(self._g[-(m+1):],dtype=float)
        # Constrained residual minimization: min ||F^T alpha|| subject sum(alpha)=1.
        # Solve the small KKT system with light Tikhonov regularization.
        gram=f_hist @ f_hist.T
        gram=gram + self.regularization*np.eye(gram.shape[0])
        ones=np.ones((gram.shape[0],1))
        kkt=np.block([[gram,ones],[ones.T,np.zeros((1,1))]])
        rhs=np.zeros(gram.shape[0]+1); rhs[-1]=1.0
        try:
            sol=np.linalg.solve(kkt,rhs)
        except Exception:
            try: sol=np.linalg.lstsq(kkt,rhs,rcond=None)[0]
            except Exception: return None
        alpha=sol[:-1]
        proposal=alpha @ g_hist
        if not np.all(np.isfinite(proposal)):
            return None
        return [float(v) for v in proposal.tolist()]
