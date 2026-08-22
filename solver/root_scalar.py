from __future__ import annotations
import math


def brent_root(func, a: float, b: float, *, xtol: float = 1e-10, rtol: float = 1e-10, max_iter: int = 80):
    """Safeguarded Brent-Dekker scalar root solver returning (root, iterations)."""
    a=float(a); b=float(b); fa=float(func(a)); fb=float(func(b))
    if not (math.isfinite(fa) and math.isfinite(fb)): raise ValueError("Root bracket produced a non-finite residual.")
    if fa==0: return a,0
    if fb==0: return b,0
    if fa*fb>0: raise ValueError("Root is not bracketed.")
    c=a; fc=fa; d=e=b-a
    for it in range(1,max_iter+1):
        if fb*fc>0: c=a; fc=fa; d=e=b-a
        if abs(fc)<abs(fb): a,b,c=b,c,b; fa,fb,fc=fb,fc,fb
        tol=2.0*rtol*abs(b)+xtol; m=0.5*(c-b)
        if abs(m)<=tol or fb==0.0: return b,it
        if abs(e)>=tol and abs(fa)>abs(fb):
            s=fb/fa
            if a==c:
                p=2.0*m*s; q=1.0-s
            else:
                q=fa/fc; r=fb/fc
                p=s*(2.0*m*q*(q-r)-(b-a)*(r-1.0)); q=(q-1.0)*(r-1.0)*(s-1.0)
            if p>0: q=-q
            else: p=-p
            if 2.0*p < min(3.0*m*q-abs(tol*q),abs(e*q)):
                e=d; d=p/q
            else: d=m; e=m
        else: d=m; e=m
        a=b; fa=fb
        b += d if abs(d)>tol else (tol if m>0 else -tol)
        fb=float(func(b))
        if not math.isfinite(fb): raise ValueError("Root iteration produced a non-finite residual.")
    raise ValueError("Brent root solver did not converge within the iteration limit.")
