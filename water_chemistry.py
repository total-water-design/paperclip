"""Multi-ion water chemistry and osmotic-pressure engine.

Full-analysis mode uses pyEQL when available. pyEQL's native electrolyte engine
uses Pitzer parameters where available and its documented effective-Pitzer
method for multicomponent mixtures. For fast coupled membrane calculations,
CalcOsPower v15.2 calibrates an osmotic surrogate once per water case and then
uses exact composition arithmetic plus an interpolated osmotic coefficient in
the element iteration loop. The direct pyEQL path remains available here as the
reference calculation.

If pyEQL is unavailable or cannot model a specific composition, the calculator
falls back to a transparent multi-ion engineering estimate that uses the user's
phi(T,I) surface with ionic strength and particle molarity calculated from the
actual ion analysis.

All user-entered species concentrations are mg/L. Boron is interpreted as mg/L
as elemental B; silica is interpreted as mg/L as SiO2.
"""
from __future__ import annotations

from functools import lru_cache
import math
from typing import Dict, Mapping

from osmotic_model import osmotic_coefficient, R_L_BAR_MOL_K

# Optional dependency is imported ONCE at module import, not inside the hot path.
try:
    from pyEQL import Solution as _Solution
    _PYEQL_ERR = ""
except Exception as _exc:  # pragma: no cover - depends on local optional package
    _Solution = None
    _PYEQL_ERR = f"pyEQL unavailable/unsupported composition: {_exc}"

# key: label, formula used by pyEQL, MW g/mol, charge, input basis
SPECIES = {
    "ammonium":   ("Ammonium",   "NH4+",   18.03846,  +1, "species"),
    "sodium":     ("Sodium",     "Na+",    22.989769, +1, "species"),
    "potassium":  ("Potassium",  "K+",     39.0983,   +1, "species"),
    "magnesium":  ("Magnesium",  "Mg+2",   24.305,    +2, "species"),
    "calcium":    ("Calcium",    "Ca+2",   40.078,    +2, "species"),
    "strontium":  ("Strontium",  "Sr+2",   87.62,     +2, "species"),
    "barium":     ("Barium",     "Ba+2",  137.327,    +2, "species"),
    "iron_ii":    ("Iron (II)",  "Fe+2",   55.845,    +2, "species"),
    "iron_iii":   ("Iron (III)", "Fe+3",   55.845,    +3, "species"),
    "manganese_ii":("Manganese (II)","Mn+2",54.938,  +2, "species"),
    "fluoride":   ("Fluoride",   "F-",     18.998403, -1, "species"),
    "chloride":   ("Chloride",   "Cl-",    35.453,    -1, "species"),
    "sulfate":    ("Sulfate",    "SO4-2",  96.06,     -2, "species"),
    "nitrate":    ("Nitrate",    "NO3-",   62.0049,   -1, "species"),
    "carbonate":  ("Carbonate",  "CO3-2",  60.0089,   -2, "species"),
    "bicarbonate":("Bicarbonate","HCO3-",  61.0168,   -1, "species"),
    "phosphate":  ("o-Phosphate","PO4-3",  94.971,    -3, "species"),
    "boron":      ("Boron",      "H3BO3",  10.81,      0, "element_B"),
    "bromide":    ("Bromide",    "Br-",    79.904,    -1, "species"),
    "silica":     ("Silica",     "SiO2",   60.0843,    0, "species"),
}

DEFAULT_EXAMPLE_MG_L = {
    "ammonium": 0.00,
    "sodium": 1436.94,
    "potassium": 34.27,
    "magnesium": 231.73,
    "calcium": 424.44,
    "strontium": 0.00,
    "barium": 0.00,
    "iron_ii": 0.00,
    "iron_iii": 0.00,
    "manganese_ii": 0.00,
    "fluoride": 0.00,
    "chloride": 2232.38,
    "sulfate": 1617.30,
    "nitrate": 62.27,
    "carbonate": 1.75,
    "bicarbonate": 360.64,
    "phosphate": 0.00,
    "boron": 1.50,
    "bromide": 0.00,
    "silica": 0.00,
}

_KEYS = tuple(SPECIES)
_MW = tuple(float(SPECIES[k][2]) for k in _KEYS)
_Z = tuple(int(SPECIES[k][3]) for k in _KEYS)
_INV_MW_1000 = tuple(1.0 / (1000.0 * mw) for mw in _MW)
_Z2 = tuple(float(z*z) for z in _Z)
_ABSZ = tuple(float(abs(z)) for z in _Z)


def normalize_composition(comp: Mapping[str, float] | None) -> Dict[str, float]:
    comp = comp or {}
    return {k: max(0.0, float(comp.get(k, 0.0) or 0.0)) for k in SPECIES}


def _scan_composition(comp: Mapping[str, float] | None) -> dict:
    """Normalize once and accumulate all commonly-used composition diagnostics.

    This replaces the former fallback path that normalized the same composition
    four separate times. ``ionic_strength_molar`` is retained internally because
    CalcOsPower's legacy phi(T,I) fallback surface is calibrated on mol/L.
    Reported ``ionic_strength`` is standardized separately to mol/kg.
    """
    comp = comp or {}
    vals: Dict[str, float] = {}
    tds = particles = ionic2 = cat = an = 0.0
    get = comp.get
    for i, k in enumerate(_KEYS):
        v = get(k, 0.0)
        v = 0.0 if v is None or v == "" else float(v)
        if v < 0.0:
            v = 0.0
        vals[k] = v
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
    denom = max(cat + an, 1e-12)
    return {
        "composition": vals,
        "tds_ppm": tds,
        "particles_mol_l": particles,
        "ionic_strength_molar": 0.5 * ionic2,
        "cations_meq_l": cat,
        "anions_meq_l": an,
        "imbalance_pct": 100.0 * (cat - an) / denom,
    }


def total_tds_mg_l(comp: Mapping[str, float]) -> float:
    return _scan_composition(comp)["tds_ppm"]


def _molarity(key: str, mg_l: float) -> float:
    """Input mg/L -> mol/L.

    For boron, input is mg/L as elemental B, so its molar amount is based on
    atomic B even though H3BO3 is used as the neutral species representation.
    """
    return max(0.0, float(mg_l)) / 1000.0 / SPECIES[key][2]


def ionic_strength_mol_l(comp: Mapping[str, float]) -> float:
    """Ionic strength on a molar concentration basis (mol/L)."""
    return _scan_composition(comp)["ionic_strength_molar"]


def _pure_water_density_kg_l(temp_c: float) -> float:
    """Pure-water density near atmospheric pressure, kg/L (Kell correlation)."""
    t = min(max(float(temp_c), 0.0), 100.0)
    rho_kg_m3 = 1000.0 * (1.0 - ((t + 288.9414) / (508929.2 * (t + 68.12963))) * (t - 3.9863) ** 2)
    return rho_kg_m3 / 1000.0


def solution_specific_gravity(tds_ppm: float, temp_c: float = 25.0) -> float:
    """Engineering specific gravity for the dissolved-solids stream.

    Uses the same solution-density convention already employed by CalcOsPower
    for molarity-to-molality conversion.  SG is reported relative to 1 kg/L,
    which is the convention required by the standard liquid Cv equation.
    """
    tds_g_l = max(0.0, float(tds_ppm)) / 1000.0
    return max(0.90, _pure_water_density_kg_l(temp_c) + 0.00075 * tds_g_l)


def _molar_to_molal_approx(i_molar: float, tds_ppm: float, temp_c: float) -> float:
    """Convert mol/L ionic strength to an engineering mol/kg-water estimate.

    Direct pyEQL states report exact molality. For the internal fallback and
    surrogate diagnostics, solvent mass per litre is estimated from pure-water
    density plus a seawater/brine density increment of about 0.75 kg/m3 per
    g/L dissolved solids. This affects the reported diagnostic only; the legacy
    fallback phi(T,I) correlation continues to use its original molar basis.
    """
    tds_g_l = max(0.0, float(tds_ppm)) / 1000.0
    solution_density = _pure_water_density_kg_l(temp_c) + 0.00075 * tds_g_l
    solute_kg_l = tds_g_l / 1000.0
    solvent_kg_l = max(0.70, solution_density - solute_kg_l)
    return max(0.0, float(i_molar)) / solvent_kg_l


def ionic_strength_mol_kg(comp: Mapping[str, float], temp_c: float = 25.0) -> float:
    s = _scan_composition(comp)
    return _molar_to_molal_approx(s["ionic_strength_molar"], s["tds_ppm"], temp_c)


def charge_balance(comp: Mapping[str, float]) -> dict:
    s = _scan_composition(comp)
    return {k: s[k] for k in ("cations_meq_l", "anions_meq_l", "imbalance_pct")}


def scale_composition(comp: Mapping[str, float], factor: float) -> Dict[str, float]:
    f = max(0.0, float(factor))
    return {k: float(v) * f for k, v in normalize_composition(comp).items()}


def polarization_scale_composition(comp: Mapping[str, float], monovalent_factor: float, divalent_factor: float) -> Dict[str, float]:
    """Apply charge-aware concentration-polarization screening factors."""
    mono = max(0.0, float(monovalent_factor))
    di = max(0.0, float(divalent_factor))
    out = {}
    for k, v in normalize_composition(comp).items():
        z = abs(int(SPECIES[k][3]))
        out[k] = float(v) * (di if z >= 2 else mono)
    return out


def mix_compositions(a: Mapping[str, float], qa: float, b: Mapping[str, float], qb: float) -> Dict[str, float]:
    qa = max(0.0, float(qa)); qb = max(0.0, float(qb)); qt = qa + qb
    if qt <= 0:
        return normalize_composition(a)
    aa = normalize_composition(a); bb = normalize_composition(b)
    return {k: (qa * aa[k] + qb * bb[k]) / qt for k in SPECIES}


def permeate_composition(feed_comp: Mapping[str, float], salt_rejection: float, boron_rejection: float | None = None) -> Dict[str, float]:
    """Engineering ion-passage model."""
    c = normalize_composition(feed_comp)
    r = min(max(float(salt_rejection), 0.0), 0.999999999)
    rb = r if boron_rejection is None else min(max(float(boron_rejection), 0.0), 0.999999999)
    out = {}
    for k, v in c.items():
        rr = rb if k == "boron" else r
        out[k] = v * (1.0 - rr)
    return out


def nf_dynamic_rejections(flux_lmh: float, b_mono_mono_lmh: float,
                          b_divalent_divalent_lmh: float, b_mixed_lmh: float | None = None,
                          b_neutral_lmh: float | None = None) -> Dict[str, float]:
    """Return flux-dependent NF salt-pair rejections from calibrated B values.

    The three ionic classes correspond to manufacturer salt benchmarks:
    mono/mono (NaCl-like), divalent/divalent (MgSO4-like), and mixed-valence
    (CaCl2-like).  Rejection follows the same solution-diffusion relation used
    elsewhere in CalcOsPower, R = Jw / (Jw + B).  A missing mixed-valence
    benchmark falls back conservatively to the larger B (lower rejection) of
    the two available ionic classes.
    """
    j=max(0.0,float(flux_lmh))
    bmm=max(0.0,float(b_mono_mono_lmh))
    bdd=max(0.0,float(b_divalent_divalent_lmh))
    bmix=max(bmm,bdd) if b_mixed_lmh is None else max(0.0,float(b_mixed_lmh))
    bneu=bmm if b_neutral_lmh is None else max(0.0,float(b_neutral_lmh))
    def rr(b):
        return j/(j+b) if (j+b)>0 else 0.0
    return {
        'mono_mono':rr(bmm),
        'divalent_divalent':rr(bdd),
        'mixed_valence':rr(bmix),
        'neutral':rr(bneu),
    }


def nf_polarization_scale_composition(comp: Mapping[str, float], monovalent_factor: float,
                                      divalent_factor: float) -> Dict[str, float]:
    """Charge-balanced concentration-polarization transform for NF.

    Ionic equivalents are decomposed into the same proportional salt-pair
    ensemble used by the NF passage model. Mono/mono pairs receive the
    monovalent CP factor, divalent/divalent pairs the divalent factor, and
    mixed-valence pairs the geometric-mean factor. This avoids creating a
    charged membrane-surface composition when cations and anions have different
    valences.
    """
    c=normalize_composition(comp)
    mono=max(0.0,float(monovalent_factor)); di=max(0.0,float(divalent_factor))
    mixed=math.sqrt(max(mono*di,0.0))
    cats=[]; ans=[]; out={k:0.0 for k in SPECIES}
    for k,v in c.items():
        z=int(SPECIES[k][3])
        if z>0: cats.append((k,abs(z),float(v)/float(SPECIES[k][2])*abs(z)))
        elif z<0: ans.append((k,abs(z),float(v)/float(SPECIES[k][2])*abs(z)))
        else: out[k]=float(v)*mono
    cat_total=sum(x[2] for x in cats); an_total=sum(x[2] for x in ans)
    paired_total=min(cat_total,an_total)
    if paired_total<=1e-30: return out
    cfrac={k:eq/cat_total for k,_,eq in cats if cat_total>0}; afrac={k:eq/an_total for k,_,eq in ans if an_total>0}
    surf_eq={k:0.0 for k,_,_ in cats+ans}
    for ck,cz,_ in cats:
        for ak,az,_ in ans:
            pair_eq=paired_total*cfrac[ck]*afrac[ak]
            factor=mono if (cz==1 and az==1) else (di if (cz>=2 and az>=2) else mixed)
            scaled=pair_eq*factor
            surf_eq[ck]+=scaled; surf_eq[ak]+=scaled
    for k,z,_ in cats+ans:
        out[k]=surf_eq[k]/max(float(z),1.0)*float(SPECIES[k][2])
    return out


def nf_permeate_composition(feed_comp: Mapping[str, float], flux_lmh: float,
                              b_mono_mono_lmh: float, b_divalent_divalent_lmh: float,
                              b_mixed_lmh: float | None = None,
                              b_neutral_lmh: float | None = None) -> Dict[str, float]:
    """Charge-balanced engineering NF passage model.

    NF salt rejection is a coupled-ion property, so applying an independent
    rejection to every ion can create an electrically impossible permeate.
    CalcOsPower therefore decomposes the local ionic composition into a
    proportional ensemble of cation/anion *equivalent* salt pairs.  Each pair
    receives the manufacturer-calibrated passage for its valence class, and the
    paired equivalents are recombined into species concentrations.  This keeps
    permeate cation and anion equivalents balanced by construction while
    preserving the feed's relative ion mixture.

    This is an engineering reduced-order NF model, not a mechanistic DSPM-DE
    electrostatic transport model.  It is used only for membranes carrying
    explicit NF salt-pair calibration data.
    """
    c=normalize_composition(feed_comp)
    r=nf_dynamic_rejections(flux_lmh,b_mono_mono_lmh,b_divalent_divalent_lmh,b_mixed_lmh,b_neutral_lmh)
    passage={k:1.0-v for k,v in r.items()}
    cats=[]; ans=[]; out={k:0.0 for k in SPECIES}
    for k,v in c.items():
        z=int(SPECIES[k][3])
        if z>0:
            cats.append((k,abs(z),float(v)/float(SPECIES[k][2])*abs(z)))
        elif z<0:
            ans.append((k,abs(z),float(v)/float(SPECIES[k][2])*abs(z)))
        else:
            out[k]=float(v)*passage['neutral']
    cat_total=sum(x[2] for x in cats); an_total=sum(x[2] for x in ans)
    paired_total=min(cat_total,an_total)
    if paired_total<=1e-30:
        # No complete ionic salt pair exists.  Leave charged species rejected
        # rather than inventing counter-charge in the permeate.
        return out
    cfrac={k:eq/cat_total for k,_,eq in cats if cat_total>0}
    afrac={k:eq/an_total for k,_,eq in ans if an_total>0}
    perm_eq={k:0.0 for k,_,_ in cats+ans}
    for ck,cz,_ in cats:
        for ak,az,_ in ans:
            pair_eq=paired_total*cfrac[ck]*afrac[ak]
            if cz==1 and az==1:
                pp=passage['mono_mono']
            elif cz>=2 and az>=2:
                pp=passage['divalent_divalent']
            else:
                pp=passage['mixed_valence']
            transported=pair_eq*pp
            perm_eq[ck]+=transported
            perm_eq[ak]+=transported
    for k,z,_ in cats+ans:
        out[k]=perm_eq[k]/max(float(z),1.0)*float(SPECIES[k][2])
    return out


def concentrate_composition(feed_comp: Mapping[str, float], q_feed: float, perm_comp: Mapping[str, float], q_perm: float) -> Dict[str, float]:
    qf = max(float(q_feed), 1e-12); qp = min(max(float(q_perm), 0.0), qf * (1 - 1e-12)); qc = qf - qp
    f = normalize_composition(feed_comp); p = normalize_composition(perm_comp)
    return {k: max(0.0, (qf * f[k] - qp * p[k]) / qc) for k in SPECIES}


def _fallback_state_from_scan(s: dict, temp_c: float, reason: str = "") -> dict:
    t_k = float(temp_c) + 273.15
    i_molar = s["ionic_strength_molar"]
    # Preserve the established fallback phi surface on its original molar basis.
    phi = osmotic_coefficient(t_k, i_molar)
    pi_bar = phi * s["particles_mol_l"] * R_L_BAR_MOL_K * t_k
    i_molal = _molar_to_molal_approx(i_molar, s["tds_ppm"], temp_c)
    return {
        "osmotic_bar": pi_bar,
        "phi": phi,
        "ionic_strength": i_molal,
        "ionic_strength_molar": i_molar,
        "ionic_strength_basis": "mol/kg",
        "tds_ppm": s["tds_ppm"],
        "method": "Multi-ion φ(T,I) fallback",
        "backend": "internal",
        "warning": reason,
        "cations_meq_l": s["cations_meq_l"],
        "anions_meq_l": s["anions_meq_l"],
        "imbalance_pct": s["imbalance_pct"],
    }


def _fallback_state(comp: Mapping[str, float], temp_c: float, reason: str = "") -> dict:
    return _fallback_state_from_scan(_scan_composition(comp), temp_c, reason)


def _osmotic_state_uncached(comp: Mapping[str, float], temp_c: float = 25.0, ph: float = 7.6) -> dict:
    """Reference mixed-electrolyte osmotic calculation.

    Direct pyEQL remains the validation/reference path. The membrane hot loop
    uses :mod:`osmotic_surrogate` instead so that Solution objects are not
    reconstructed hundreds of times per membrane pass.
    """
    s = _scan_composition(comp)
    c = s["composition"]
    if s["tds_ppm"] <= 0:
        return _fallback_state_from_scan(s, temp_c)
    if _Solution is None:
        return _fallback_state_from_scan(s, temp_c, _PYEQL_ERR)

    try:
        components = {}
        neutral_extra_mol_l = 0.0
        for k, mg_l in c.items():
            if mg_l <= 0:
                continue
            components[SPECIES[k][1]] = f"{_molarity(k, mg_l):.12g} mol/L"
        try:
            sol = _Solution(components, pH=float(ph), temperature=f"{float(temp_c)} degC")
            pi_bar = sol.osmotic_pressure.to("bar").magnitude
            phi = sol.get_osmotic_coefficient().to("dimensionless").magnitude
            i_molal = sol.ionic_strength.to("mol/kg").magnitude
        except Exception:
            ionic_components = {}
            for k, mg_l in c.items():
                if mg_l <= 0 or SPECIES[k][3] == 0:
                    if mg_l > 0 and SPECIES[k][3] == 0:
                        neutral_extra_mol_l += _molarity(k, mg_l)
                    continue
                ionic_components[SPECIES[k][1]] = f"{_molarity(k, mg_l):.12g} mol/L"
            sol = _Solution(ionic_components, pH=float(ph), temperature=f"{float(temp_c)} degC")
            pi_bar = sol.osmotic_pressure.to("bar").magnitude + neutral_extra_mol_l * R_L_BAR_MOL_K * (float(temp_c)+273.15)
            phi = sol.get_osmotic_coefficient().to("dimensionless").magnitude
            i_molal = sol.ionic_strength.to("mol/kg").magnitude
        return {
            "osmotic_bar": float(pi_bar),
            "phi": float(phi),
            "ionic_strength": float(i_molal),
            "ionic_strength_molar": s["ionic_strength_molar"],
            "ionic_strength_basis": "mol/kg",
            "tds_ppm": s["tds_ppm"],
            "method": "pyEQL effective Pitzer multi-ion",
            "backend": "pyEQL",
            "warning": "",
            "cations_meq_l": s["cations_meq_l"],
            "anions_meq_l": s["anions_meq_l"],
            "imbalance_pct": s["imbalance_pct"],
        }
    except Exception as exc:
        return _fallback_state_from_scan(s, temp_c, f"pyEQL unavailable/unsupported composition: {exc}")


@lru_cache(maxsize=4096)
def _osmotic_state_cached(values: tuple[float, ...], temp_c: float, ph: float) -> tuple[tuple[str, object], ...]:
    comp = {k: values[i] for i, k in enumerate(SPECIES)}
    return tuple(_osmotic_state_uncached(comp, temp_c, ph).items())


def osmotic_state_from_composition(comp: Mapping[str, float], temp_c: float = 25.0, ph: float = 7.6) -> dict:
    """Cached direct/reference mixed-electrolyte osmotic state."""
    c = normalize_composition(comp)
    values = tuple(float(c[k]) for k in SPECIES)
    return dict(_osmotic_state_cached(values, float(temp_c), float(ph)))


def clear_osmotic_state_cache() -> None:
    _osmotic_state_cached.cache_clear()


def composition_from_request(data: Mapping[str, object]) -> Dict[str, float]:
    # v17.2: the analytical bicarbonate field stores total alkalinity expressed
    # as mg/L HCO3-equivalent. Alkalinity may legitimately be negative in acidic
    # waters; all other analytical concentrations remain non-negative.
    out={}
    for k in SPECIES:
        v=float(data.get(f"ion_{k}",0.0) or 0.0)
        out[k]=v if k=="bicarbonate" else max(0.0,v)
    return out
