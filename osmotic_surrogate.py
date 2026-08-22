"""Calibrated osmotic surrogate for fast full-analysis RO calculations.

The expensive pyEQL mixed-electrolyte model is sampled at nine concentration
factors for each unique (feed composition, temperature, pH) case. The membrane
iteration then calculates particle molarity exactly from the current composition
and interpolates only the smooth osmotic coefficient φ versus molar ionic
strength. This keeps pyEQL-informed mixed-electrolyte behavior while removing
pyEQL Solution construction from the element-convergence loop.
"""
from __future__ import annotations

from bisect import bisect_right
from typing import Mapping
import os

from osmotic_model import R_L_BAR_MOL_K, osmotic_coefficient
from water_chemistry import SPECIES, _Solution, _PYEQL_ERR, _molar_to_molal_approx

_KEYS = tuple(SPECIES)
_Z = tuple(SPECIES[k][3] for k in _KEYS)
_Z2 = tuple(float(z*z) for z in _Z)
_ABSZ = tuple(float(abs(z)) for z in _Z)
_INV_MW_1000 = tuple(1.0 / (1000.0 * SPECIES[k][2]) for k in _KEYS)
_FORMULA = tuple(SPECIES[k][1] for k in _KEYS)

# Per attached performance study: 0.002 covers permeate; 4.0 covers high-recovery
# concentrate including concentration polarization. Nine points gave the best
# speed/accuracy balance in the measured CalcOsPower process path.
DEFAULT_CF_GRID = (0.002, 0.05, 0.25, 0.5, 1.0, 1.5, 2.0, 2.75, 4.0)


def _scan(comp: Mapping[str, float]):
    """Single pass: normalized values, TDS, particles, molar I and charge balance."""
    tds = particles = ionic2 = cat = an = 0.0
    vals = []
    get = comp.get
    for i, k in enumerate(_KEYS):
        v = get(k, 0.0)
        v = 0.0 if v is None or v == "" else float(v)
        if v < 0.0:
            v = 0.0
        vals.append(v)
        tds += v
        mol = v * _INV_MW_1000[i]
        particles += mol
        z = _Z[i]
        if z:
            ionic2 += mol * _Z2[i]
            meq = mol * _ABSZ[i] * 1000.0
            if z > 0:
                cat += meq
            else:
                an += meq
    denom = cat + an if (cat + an) > 1e-12 else 1e-12
    return vals, tds, particles, 0.5*ionic2, cat, an, 100.0*(cat-an)/denom


def _interp(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    j = bisect_right(xs, x)
    x0, x1, y0, y1 = xs[j-1], xs[j], ys[j-1], ys[j]
    return y0 if x1 == x0 else y0 + (x-x0)*(y1-y0)/(x1-x0)


class OsmoticSurrogate:
    """φ(I) calibrated against pyEQL for one feed water, temperature and pH."""

    def __init__(self, feed_comp, temp_c=25.0, ph=7.6,
                 cf_grid=DEFAULT_CF_GRID, solution_cls=None):
        self.temp_c = float(temp_c)
        self.t_k = self.temp_c + 273.15
        self.ph = float(ph)
        self.backend = "internal"
        self.method = "Multi-ion φ(T,I) fallback"
        self.warning = _PYEQL_ERR
        self.pyeql_calls = 0
        self._i_molar: list[float] = []
        self._phi: list[float] = []
        self._molal_ratio: list[float] = []

        disabled = solution_cls is False
        if solution_cls is None:
            solution_cls = _Solution

        if solution_cls is not None and not disabled:
            pts = []
            for cf in cf_grid:
                scaled = {k: float(feed_comp.get(k, 0.0) or 0.0)*cf for k in _KEYS}
                vals, tds, _, i_molar, _, _, _ = _scan(scaled)
                if tds <= 0:
                    continue
                try:
                    components = {_FORMULA[i]: f"{vals[i]*_INV_MW_1000[i]:.12g} mol/L"
                                  for i in range(len(_KEYS)) if vals[i] > 0}
                    try:
                        sol = solution_cls(components, pH=self.ph, temperature=f"{self.temp_c} degC")
                    except Exception:
                        # Neutral entries can vary across electrolyte databases. φ is
                        # governed primarily by the ionic mixture, so retry ions only.
                        ionic = {_FORMULA[i]: f"{vals[i]*_INV_MW_1000[i]:.12g} mol/L"
                                 for i in range(len(_KEYS)) if vals[i] > 0 and _Z[i] != 0}
                        sol = solution_cls(ionic, pH=self.ph, temperature=f"{self.temp_c} degC")
                    phi = float(sol.get_osmotic_coefficient().to("dimensionless").magnitude)
                    i_molal = float(sol.ionic_strength.to("mol/kg").magnitude)
                    self.pyeql_calls += 1
                    ratio = i_molal/max(i_molar, 1e-15)
                    pts.append((i_molar, phi, ratio))
                except Exception:
                    continue
            pts = sorted({(round(a, 15), b, c) for a, b, c in pts})
            if len(pts) >= 2:
                self._i_molar = [p[0] for p in pts]
                self._phi = [p[1] for p in pts]
                self._molal_ratio = [p[2] for p in pts]
                self.backend = "pyEQL (calibrated surrogate)"
                self.method = f"pyEQL effective Pitzer · calibrated φ(I), {len(pts)} points"
                self.warning = ""

    @property
    def calibrated(self) -> bool:
        return bool(self._i_molar)

    def phi(self, i_molar: float) -> float:
        if not self._i_molar:
            return osmotic_coefficient(self.t_k, i_molar)
        return _interp(i_molar, self._i_molar, self._phi)

    def ionic_strength_molal(self, i_molar: float, tds_ppm: float) -> float:
        if self._i_molar:
            ratio = _interp(i_molar, self._i_molar, self._molal_ratio)
            return max(0.0, i_molar*ratio)
        return _molar_to_molal_approx(i_molar, tds_ppm, self.temp_c)

    def state(self, comp: Mapping[str, float]) -> dict:
        _, tds, particles, i_molar, cat, an, imb = _scan(comp)
        phi = self.phi(i_molar)
        return {
            "osmotic_bar": phi*particles*R_L_BAR_MOL_K*self.t_k,
            "phi": phi,
            "ionic_strength": self.ionic_strength_molal(i_molar, tds),
            "ionic_strength_molar": i_molar,
            "ionic_strength_basis": "mol/kg",
            "tds_ppm": tds,
            "method": self.method,
            "backend": self.backend,
            "warning": self.warning,
            "cations_meq_l": cat,
            "anions_meq_l": an,
            "imbalance_pct": imb,
        }


_SURROGATES: dict = {}
_MAX_SURROGATES = 64


def _key(feed_comp, temp_c, ph):
    return (tuple(round(float(feed_comp.get(k, 0.0) or 0.0), 9) for k in _KEYS),
            round(float(temp_c), 4), round(float(ph), 4))


def get_surrogate(feed_comp, temp_c=25.0, ph=7.6) -> OsmoticSurrogate:
    """Return one cached surrogate per feed water, temperature and pH."""
    k = _key(feed_comp, temp_c, ph)
    s = _SURROGATES.get(k)
    if s is None:
        solution_cls = False if os.environ.get('CALCOSPOWER_TEST_FAST_OSMOTIC', '0') == '1' else None
        s = OsmoticSurrogate(feed_comp, temp_c, ph, solution_cls=solution_cls)
        if len(_SURROGATES) >= _MAX_SURROGATES:
            _SURROGATES.clear()
        _SURROGATES[k] = s
    return s


def clear_surrogates() -> None:
    _SURROGATES.clear()


def surrogate_cache_size() -> int:
    return len(_SURROGATES)


def osmotic_state_for(feed_comp, comp, temp_c=25.0, ph=7.6) -> dict:
    return get_surrogate(feed_comp, temp_c, ph).state(comp)
