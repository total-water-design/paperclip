from __future__ import annotations
import time

class SolverTrace:
    def __init__(self, method: str):
        self.method=str(method); self.started=time.perf_counter(); self.rows=[]; self.fallbacks=[]; self.rejected=0
    def add(self, iteration: int, residual: float, method: str | None = None, step: float | None = None, accepted: bool = True, note: str = ""):
        if not accepted: self.rejected+=1
        self.rows.append({"iteration":int(iteration),"residual":float(abs(residual)),"method":str(method or self.method),"step":step,"accepted":bool(accepted),"note":str(note or "")})
    def fallback(self, name: str): self.fallbacks.append(str(name))
    def as_dict(self, tolerance: float | None = None):
        final=self.rows[-1]["residual"] if self.rows else None
        return {"method":self.method,"iterations":len(self.rows),"residual":final,"tolerance":tolerance,"rejected_steps":self.rejected,
                "fallbacks":list(self.fallbacks),"elapsed_ms":1000.0*(time.perf_counter()-self.started),"history":list(self.rows)}
