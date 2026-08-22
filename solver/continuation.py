from __future__ import annotations
import hashlib, json, math, threading
from dataclasses import dataclass
from typing import Any


def _water_viscosity_mpa_s(temp_c: float) -> float:
    """Compact water-viscosity approximation for warm-start metadata (not process physics)."""
    t=float(temp_c)
    # Andrade relation; adequate for predictor metadata in the normal liquid-water range.
    tk=t+273.15
    return 2.414e-2 * 10.0**(247.8/(tk-140.0))


def water_state_snapshot(*, pressure_bar: float | None = None, flow_m3h: float | None = None,
                         temperature_c: float | None = None, density_kg_l: float | None = None,
                         tds_mg_l: float | None = None, ionic_strength: float | None = None,
                         osmotic_bar: float | None = None, ph: float | None = None,
                         alkalinity_mg_l: float | None = None, composition: dict | None = None,
                         extra: dict | None = None) -> dict[str, Any]:
    t=25.0 if temperature_c is None else float(temperature_c)
    out={
        "pressure_bar": pressure_bar,
        "flow_m3h": flow_m3h,
        "temperature_c": t,
        "density_kg_l": density_kg_l,
        "viscosity_mpa_s": _water_viscosity_mpa_s(t),
        "tds_mg_l": tds_mg_l,
        "ionic_strength": ionic_strength,
        "osmotic_bar": osmotic_bar,
        "ph": ph,
        "alkalinity_mg_l": alkalinity_mg_l,
        "composition_mg_l": dict(composition or {}),
    }
    if extra: out.update(extra)
    return out


def water_state_signature(payload: dict[str, Any], keys: tuple[str,...] | None = None) -> str:
    # Signature excludes target pressure/flow so nearby duty points can share a compatible warm state.
    default=("water_mode","membrane_1","membrane_2","membrane_3","membrane_4","stage_count",
             "flow_unit","pressure_unit","acid_apply","acid_type","target_ph","feed_tds")
    clean={k:payload.get(k) for k in (keys or default)}
    # Ion chemistry is part of compatibility.
    for k,v in sorted(payload.items()):
        if str(k).startswith("ion_"): clean[k]=v
    raw=json.dumps(clean,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


@dataclass
class CacheEntry:
    coordinate: float
    signature: str
    state: dict[str,Any]
    residual: float | None = None


class ThermodynamicStateCache:
    """Small thread-safe continuation cache keyed by compatible process signature."""
    def __init__(self, max_entries: int = 96):
        self.max_entries=max(4,int(max_entries)); self._entries=[]; self._lock=threading.RLock()

    def put(self, coordinate: float, signature: str, state: dict[str,Any], residual: float | None = None):
        if not state: return
        with self._lock:
            self._entries=[e for e in self._entries if not (e.signature==signature and abs(e.coordinate-float(coordinate))<1e-10)]
            self._entries.append(CacheEntry(float(coordinate),str(signature),dict(state),residual))
            if len(self._entries)>self.max_entries: self._entries=self._entries[-self.max_entries:]

    def nearest(self, coordinate: float, signature: str) -> dict[str,Any] | None:
        with self._lock:
            rows=[e for e in self._entries if e.signature==signature]
            if not rows: return None
            e=min(rows,key=lambda r:abs(r.coordinate-float(coordinate)))
            return dict(e.state)

    def predictor(self, coordinate: float, signature: str) -> dict[str,Any] | None:
        with self._lock:
            rows=sorted([e for e in self._entries if e.signature==signature],key=lambda r:abs(r.coordinate-float(coordinate)))
            if not rows: return None
            if len(rows)<2: return dict(rows[0].state)
            a,b=rows[0],rows[1]
            if abs(a.coordinate-b.coordinate)<1e-12: return dict(a.state)
            frac=(float(coordinate)-a.coordinate)/(a.coordinate-b.coordinate)
            out=dict(a.state)
            # Predict only scalar thermohydraulic fields; composition is copied from the nearest state.
            for k,v in list(a.state.items()):
                if isinstance(v,(int,float)) and isinstance(b.state.get(k),(int,float)) and math.isfinite(float(v)) and math.isfinite(float(b.state[k])):
                    out[k]=float(v)+frac*(float(v)-float(b.state[k]))
            return out
