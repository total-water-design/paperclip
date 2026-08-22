from __future__ import annotations
from typing import Callable, Sequence


def bounded_step(x: Sequence[float], proposal: Sequence[float], lower: Sequence[float] | None = None,
                 upper: Sequence[float] | None = None) -> list[float]:
    out=[]
    for i,(a,b) in enumerate(zip(x,proposal)):
        v=float(b)
        if lower is not None: v=max(float(lower[i]),v)
        if upper is not None: v=min(float(upper[i]),v)
        out.append(v)
    return out


def bounded_backtracking_line_search(x: Sequence[float], proposal: Sequence[float], merit0: float,
                                     evaluator: Callable[[list[float]], float], *,
                                     lower: Sequence[float] | None = None,
                                     upper: Sequence[float] | None = None,
                                     contraction: float = 0.5, min_step: float = 1/64,
                                     sufficient_decrease: float = 1e-4):
    """Backtrack an accelerated step until the residual merit decreases.

    Returns (accepted_state, merit, step_fraction) or (None, merit0, 0.0).
    """
    x=[float(v) for v in x]; p=[float(v) for v in proposal]
    direction=[b-a for a,b in zip(x,p)]
    step=1.0
    while step>=min_step:
        cand=[a+step*d for a,d in zip(x,direction)]
        cand=bounded_step(x,cand,lower,upper)
        merit=float(evaluator(cand))
        if merit < float(merit0)*(1.0-sufficient_decrease*step):
            return cand,merit,step
        step*=contraction
    return None,float(merit0),0.0
