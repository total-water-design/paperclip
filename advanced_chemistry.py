"""Advanced coupled weak-species chemistry for Total Water Design Suite.

This layer keeps the existing validated equilibrium constants, density helpers,
Pitzer/Davies infrastructure and scaling calculations, while upgrading the
acid/base coupling used by RO/NF stream calculations:

* pH roots converge at ~1e-9 pH units;
* NH4+ / NH3 partition uses hydrogen activity and an activity correction;
* neutral NH3 has a membrane-passage path independent from NH4+;
* first metal hydroxo complexes (e.g. CaOH+, MgOH+) participate in alkalinity
  and electroneutrality using constants already present in chemistry_analysis;
* downstream membrane and mixed-stream pH is solved from transported component
  totals + inorganic carbon + electroneutrality rather than assuming total
  alkalinity follows a single membrane rejection factor.

The analytical ``ammonium`` field remains mg/L as NH4-equivalent for backward
compatibility. No new empirical hydrolysis constants are introduced here.
"""
from __future__ import annotations

from typing import Mapping

import chemistry_analysis as _base
from solver import brent_root
from water_chemistry import SPECIES, normalize_composition


HYDROXO_COMPONENTS = {
    "sodium": ("Na", "NaOH(aq)"),
    "potassium": ("K", "KOH(aq)"),
    "calcium": ("Ca", "CaOH+"),
    "magnesium": ("Mg", "MgOH+"),
    "strontium": ("Sr", "SrOH+"),
    "barium": ("Ba", "BaOH+"),
    "iron_ii": ("Fe", "FeOH+"),
    "manganese_ii": ("Mn", "MnOH+"),
}

NH3_MW = 17.03052
NH4_EQ_MW = float(SPECIES["ammonium"][2])


def weak_species_speciation(comp: Mapping[str, float], temp_c: float, ph: float) -> dict:
    """Return weak-species totals with activity-aware NH4+/NH3 partition.

    Other weak systems retain the established chemistry-analysis equations. pH
    is hydrogen activity by definition; NH4+ receives a Davies monovalent
    activity correction and neutral NH3 is taken with gamma ~= 1.
    """
    out = dict(_base._legacy_weak_species_speciation(comp, temp_c, ph))
    c = normalize_composition(comp)
    m = _base._molalities(c, temp_c)
    ionic_strength = 0.5 * sum(
        m[k] * float(SPECIES[k][3]) ** 2 for k in SPECIES if SPECIES[k][3]
    )
    a_h = max(10.0 ** (-float(ph)), 1e-30)
    ka = 10.0 ** _base._logk("KN", temp_c)
    gamma_nh4 = max(_base._davies_gamma(1, ionic_strength), 1e-30)
    ratio_nh3_nh4 = ka * gamma_nh4 / a_h
    total = max(0.0, float(m.get("ammonium", 0.0)))
    nh4 = total / max(1.0 + ratio_nh3_nh4, 1e-30)
    nh3 = max(0.0, total - nh4)
    out["ammonia"] = {
        "total": total,
        "NH4+": nh4,
        "NH3": nh3,
        "gamma_NH4+": gamma_nh4,
        "neutral_fraction": nh3 / max(total, 1e-30),
        "basis": "NH4+/NH3 equilibrium on hydrogen-activity pH basis",
    }
    return out


def metal_hydroxo_speciation(comp: Mapping[str, float], temp_c: float, ph: float) -> dict:
    """Partition metal totals into free ion and the first hydroxo complex.

    Existing ``HYDRO_LOGK`` constants are interpreted on their documented basis:
    M^z+ + H2O = MOH^(z-1)+ + H+. Activity corrections use Davies gammas.
    """
    c = normalize_composition(comp)
    m = _base._molalities(c, temp_c)
    ionic_strength = 0.5 * sum(
        m[k] * float(SPECIES[k][3]) ** 2 for k in SPECIES if SPECIES[k][3]
    )
    a_h = max(10.0 ** (-float(ph)), 1e-30)
    out = {}
    for key, (symbol, label) in HYDROXO_COMPONENTS.items():
        total = max(0.0, float(m.get(key, 0.0)))
        z = int(SPECIES[key][3])
        product_z = z - 1
        k_hyd = 10.0 ** float(_base.HYDRO_LOGK[symbol])
        gamma_free = max(_base._davies_gamma(z, ionic_strength), 1e-30)
        gamma_hydroxo = 1.0 if product_z == 0 else max(
            _base._davies_gamma(product_z, ionic_strength), 1e-30
        )
        ratio = k_hyd * gamma_free / max(gamma_hydroxo * a_h, 1e-30)
        free = total / max(1.0 + ratio, 1e-30)
        hydroxo = max(0.0, total - free)
        out[key] = {
            "label": label,
            "total_mol_kg": total,
            "free_mol_kg": free,
            "hydroxo_mol_kg": hydroxo,
            "free_charge": z,
            "hydroxo_charge": product_z,
            "hydrolyzed_fraction": hydroxo / max(total, 1e-30),
            "logK_hydrolysis": float(_base.HYDRO_LOGK[symbol]),
        }
    return out


def _phosphate_alkalinity(weak: Mapping[str, object]) -> float:
    p = weak.get("phosphate", {}) or {}
    return (
        float(p.get("HPO4--", 0.0))
        + 2.0 * float(p.get("PO4---", 0.0))
        - float(p.get("H3PO4", 0.0))
    )


def _advanced_state_at_ph_ct(
    comp: Mapping[str, float], temp_c: float, ph: float, ct_mol_kg: float
) -> dict:
    """Extend the established carbonate state with complete proton accounting."""
    state = dict(_base._state_at_ph_ct(comp, temp_c, ph, ct_mol_kg))
    weak = state.get("weak_systems") or weak_species_speciation(comp, temp_c, ph)
    hydroxo = metal_hydroxo_speciation(state.get("composition") or comp, temp_c, ph)

    borate = float((weak.get("boron", {}) or {}).get("B(OH)4-", 0.0))
    phosphate = _phosphate_alkalinity(weak)
    ammonia = float((weak.get("ammonia", {}) or {}).get("NH3", 0.0))
    silica = weak.get("silica", {}) or {}
    silicate = float(silica.get("H3SiO4-", 0.0)) + 2.0 * float(
        silica.get("H2SiO4--", 0.0)
    )
    fluoride = float((weak.get("fluoride", {}) or {}).get("F-", 0.0))
    hydrolysis = sum(float(x.get("hydroxo_mol_kg", 0.0)) for x in hydroxo.values())
    oh = float(state.get("oh_mol_kg", 0.0))
    h = float(state.get("h_mol_kg", 0.0))

    components = {
        "borate": borate,
        "phosphate": phosphate,
        "ammonia_nh3": ammonia,
        "silicate": silicate,
        "fluoride": fluoride,
        "metal_hydrolysis": hydrolysis,
        "hydroxide": oh,
        "hydrogen": -h,
    }
    ta_other = sum(components.values())
    ta = float(state.get("hco3_mol_kg", 0.0)) + 2.0 * float(
        state.get("co3_mol_kg", 0.0)
    ) + ta_other

    base_comp = state.get("composition") or comp
    kgw = _base._kg_water_per_l(base_comp, temp_c)
    amm = weak.get("ammonia", {}) or {}
    state.update(
        {
            "total_alkalinity_mol_kg": ta,
            "total_alkalinity_mg_l_as_hco3": _base._ta_mg_l_as_hco3(
                ta, base_comp, temp_c
            ),
            "ta_min_mol_kg": ta_other,
            "ta_min_mg_l_as_hco3": _base._ta_mg_l_as_hco3(
                ta_other, base_comp, temp_c
            ),
            "weak_systems": weak,
            "hydroxo_species": hydroxo,
            "noncarbonate_alkalinity_components_mol_kg": components,
            "ammonia_total_mol_kg": float(amm.get("total", 0.0)),
            "nh4_mol_kg": float(amm.get("NH4+", 0.0)),
            "nh3_mol_kg": float(amm.get("NH3", 0.0)),
            "nh4_mg_l_as_nh4": float(amm.get("NH4+", 0.0))
            * kgw
            * NH4_EQ_MW
            * 1000.0,
            "nh3_mg_l_as_nh3": float(amm.get("NH3", 0.0))
            * kgw
            * NH3_MW
            * 1000.0,
            "proton_accounting_basis": "carbonate + weak acids/bases + metal hydrolysis",
        }
    )
    return state


def solve_carbonate_state(
    comp: Mapping[str, float],
    temp_c: float = 25.0,
    *,
    ph: float | None = None,
    total_alkalinity_mol_kg: float | None = None,
    total_inorganic_carbon_mol_kg: float | None = None,
) -> dict:
    """Advanced two-of-three {pH, TA, CT} equilibrium solve."""
    known = sum(
        x is not None
        for x in (ph, total_alkalinity_mol_kg, total_inorganic_carbon_mol_kg)
    )
    if known != 2:
        raise ValueError(
            "Carbonate state requires exactly two of pH, total alkalinity (TA), and total inorganic carbon (CT)."
        )
    analytical = _base._analytical_composition(comp)

    if ph is not None and total_inorganic_carbon_mol_kg is not None:
        return _advanced_state_at_ph_ct(
            analytical, temp_c, float(ph), max(0.0, float(total_inorganic_carbon_mol_kg))
        )

    if ph is not None and total_alkalinity_mol_kg is not None:
        phv = float(ph)
        target = float(total_alkalinity_mol_kg)
        states = {}

        def state_at_ct(ct_value: float) -> dict:
            key = float(ct_value)
            if key not in states:
                states[key] = _advanced_state_at_ph_ct(
                    analytical, temp_c, phv, max(0.0, key)
                )
            return states[key]

        probe = state_at_ct(0.0)
        if target < float(probe["ta_min_mol_kg"]) - 1e-12:
            raise ValueError(
                f"Total alkalinity is below the physical minimum at fixed pH {phv:.2f}. "
                f"Minimum is {float(probe['ta_min_mg_l_as_hco3']):.3f} mg/L as HCO3-equivalent."
            )
        f0 = float(probe["total_alkalinity_mol_kg"]) - target
        if abs(f0) <= 1e-12:
            return probe

        hi = max(target - float(probe["ta_min_mol_kg"]), 1e-9)

        def residual_ct(ct_value: float) -> float:
            return float(state_at_ct(ct_value)["total_alkalinity_mol_kg"]) - target

        fhi = residual_ct(hi)
        for _ in range(30):
            if f0 * fhi <= 0.0:
                break
            hi *= 2.0
            fhi = residual_ct(hi)
        if f0 * fhi > 0.0:
            raise ValueError(
                "Could not bracket inorganic carbon at the supplied fixed pH and alkalinity."
            )
        ct_root, _ = brent_root(
            residual_ct, 0.0, hi, xtol=1e-12, rtol=1e-12, max_iter=80
        )
        return state_at_ct(ct_root)

    target = float(total_alkalinity_mol_kg)
    ct = max(0.0, float(total_inorganic_carbon_mol_kg))
    lo = float(_base.CARBONATE_PH_MIN)
    hi = float(_base.CARBONATE_PH_MAX)
    states = {}

    def state_at_ph(p: float) -> dict:
        key = float(p)
        if key not in states:
            states[key] = _advanced_state_at_ph_ct(analytical, temp_c, key, ct)
        return states[key]

    def residual_ph(p: float) -> float:
        return float(state_at_ph(p)["total_alkalinity_mol_kg"]) - target

    flo = residual_ph(lo)
    fhi = residual_ph(hi)
    if flo == 0.0:
        return state_at_ph(lo)
    if fhi == 0.0:
        return state_at_ph(hi)
    if flo * fhi > 0.0:
        raise ValueError(
            f"Could not bracket carbonate pH between {lo:.0f} and {hi:.0f} for the supplied TA and CT."
        )
    ph_root, _ = brent_root(
        residual_ph, lo, hi, xtol=1e-9, rtol=1e-12, max_iter=80
    )
    return state_at_ph(ph_root)


def equilibrium_charge_report(state: Mapping[str, object], temp_c: float) -> dict:
    """Electroneutrality from explicit equilibrium species, in meq/L."""
    comp = normalize_composition(state.get("composition") or {})
    kgw = _base._kg_water_per_l(comp, temp_c)
    m = _base._molalities(comp, temp_c)
    ph = float(state.get("ph", 7.0))
    weak = state.get("weak_systems") or weak_species_speciation(comp, temp_c, ph)
    hydro = state.get("hydroxo_species") or metal_hydroxo_speciation(comp, temp_c, ph)

    cat_eq = 0.0
    an_eq = 0.0
    rows = []

    def add(key: str, equivalents_mol_kg: float, side: str) -> None:
        nonlocal cat_eq, an_eq
        eq = max(0.0, float(equivalents_mol_kg))
        if side == "cation":
            cat_eq += eq
        else:
            an_eq += eq
        rows.append(
            {
                "key": key,
                "label": key,
                "side": side,
                "meq_l": eq * kgw * 1000.0,
            }
        )

    add("H+", float(state.get("h_mol_kg", 0.0)), "cation")
    add("ammonium", float((weak.get("ammonia", {}) or {}).get("NH4+", 0.0)), "cation")

    for key, item in hydro.items():
        z = int(SPECIES[key][3])
        add(key, float(item.get("free_mol_kg", 0.0)) * max(z, 0), "cation")
        hz = int(item.get("hydroxo_charge", z - 1))
        if hz > 0:
            add(
                str(item.get("label", key + "OH")),
                float(item.get("hydroxo_mol_kg", 0.0)) * hz,
                "cation",
            )

    # Fe(III) does not have a first-hydrolysis constant in the existing workbook
    # table, so it remains on its analytical charge basis here.
    add("iron_iii", float(m.get("iron_iii", 0.0)) * 3.0, "cation")

    add("chloride", float(m.get("chloride", 0.0)), "anion")
    add("sulfate", 2.0 * float(m.get("sulfate", 0.0)), "anion")
    add("nitrate", float(m.get("nitrate", 0.0)), "anion")
    add("bromide", float(m.get("bromide", 0.0)), "anion")
    add("bicarbonate", float(state.get("hco3_mol_kg", 0.0)), "anion")
    add("carbonate", 2.0 * float(state.get("co3_mol_kg", 0.0)), "anion")
    add("fluoride", float((weak.get("fluoride", {}) or {}).get("F-", 0.0)), "anion")

    phosphate = weak.get("phosphate", {}) or {}
    add("H2PO4-", float(phosphate.get("H2PO4-", 0.0)), "anion")
    add("HPO4--", 2.0 * float(phosphate.get("HPO4--", 0.0)), "anion")
    add("PO4---", 3.0 * float(phosphate.get("PO4---", 0.0)), "anion")
    add("B(OH)4-", float((weak.get("boron", {}) or {}).get("B(OH)4-", 0.0)), "anion")

    silica = weak.get("silica", {}) or {}
    add("H3SiO4-", float(silica.get("H3SiO4-", 0.0)), "anion")
    add("H2SiO4--", 2.0 * float(silica.get("H2SiO4--", 0.0)), "anion")
    add("OH-", float(state.get("oh_mol_kg", 0.0)), "anion")

    cat_meq_l = cat_eq * kgw * 1000.0
    an_meq_l = an_eq * kgw * 1000.0
    denom = cat_meq_l + an_meq_l
    imbalance = (
        0.0
        if denom <= 1e-30
        else 2.0 * (cat_meq_l - an_meq_l) / denom * 100.0
    )
    return {
        "rows": rows,
        "cations_meq_l": cat_meq_l,
        "anions_meq_l": an_meq_l,
        "residual_meq_l": cat_meq_l - an_meq_l,
        "imbalance_pct": imbalance,
        "status": "good"
        if abs(imbalance) < 2.0
        else ("review" if abs(imbalance) < 5.0 else "check"),
        "basis": "explicit equilibrium species including NH4/NH3 and first metal hydrolysis",
    }


def solve_charge_balanced_state(
    comp: Mapping[str, float], temp_c: float, total_inorganic_carbon_mol_kg: float
) -> dict:
    """Solve downstream pH from component totals + CT + electroneutrality."""
    analytical = _base._analytical_composition(comp)
    ct = max(0.0, float(total_inorganic_carbon_mol_kg))
    lo = float(_base.CARBONATE_PH_MIN)
    hi = float(_base.CARBONATE_PH_MAX)
    states = {}

    def state_at(p: float) -> dict:
        key = float(p)
        if key not in states:
            states[key] = _advanced_state_at_ph_ct(analytical, temp_c, key, ct)
        return states[key]

    def residual(p: float) -> float:
        return float(equilibrium_charge_report(state_at(p), temp_c)["residual_meq_l"])

    # A modest scan makes the charge root robust even when weak-acid systems
    # introduce curvature. The final root remains Brent-safeguarded at 1e-9 pH.
    grid = [lo + (hi - lo) * i / 80.0 for i in range(81)]
    values = [(p, residual(p)) for p in grid]
    root = None
    for (p0, f0), (p1, f1) in zip(values, values[1:]):
        if f0 == 0.0:
            root = p0
            break
        if f0 * f1 <= 0.0:
            root, _ = brent_root(
                residual, p0, p1, xtol=1e-9, rtol=1e-12, max_iter=80
            )
            break
    if root is None:
        best_p, best_f = min(values, key=lambda x: abs(x[1]))
        if abs(best_f) <= 1e-7:
            root = best_p
        else:
            raise ValueError(
                f"Could not close downstream electroneutrality between pH {lo:.0f} and {hi:.0f}; "
                f"best residual is {best_f:.3e} meq/L."
            )

    state = dict(state_at(root))
    state["charge_balance"] = equilibrium_charge_report(state, temp_c)
    state["ph_solver_basis"] = (
        "component mass balance + total inorganic carbon + explicit electroneutrality"
    )
    return state


def ammonia_membrane_transport(
    comp: Mapping[str, float],
    temp_c: float,
    ph: float,
    ionic_rejection: float,
    neutral_rejection: float = 0.0,
) -> dict:
    """Transport NH4+ and neutral NH3 independently.

    Concentrations returned to the Suite remain on the historical mg/L as
    NH4-equivalent total-ammonia basis. ``neutral_rejection=0`` means neutral
    NH3 concentration passage is unity; a membrane-specific value can override it.
    """
    ri = min(max(float(ionic_rejection), 0.0), 0.999999999)
    rn = min(max(float(neutral_rejection), 0.0), 0.999999999)
    c = normalize_composition(comp)
    weak = weak_species_speciation(c, temp_c, ph)
    ammonia = weak.get("ammonia", {}) or {}
    kgw = _base._kg_water_per_l(c, temp_c)
    nh4_mol_l = max(0.0, float(ammonia.get("NH4+", 0.0))) * kgw
    nh3_mol_l = max(0.0, float(ammonia.get("NH3", 0.0))) * kgw

    permeate_nh4 = nh4_mol_l * (1.0 - ri)
    permeate_nh3 = nh3_mol_l * (1.0 - rn)
    permeate_total = permeate_nh4 + permeate_nh3

    return {
        "surface_ph": float(ph),
        "ionic_nh4_rejection": ri,
        "neutral_nh3_rejection": rn,
        "feed_total_ammonia_mg_l_as_nh4": float(c.get("ammonium", 0.0)),
        "feed_nh4_mg_l_as_nh4": nh4_mol_l * NH4_EQ_MW * 1000.0,
        "feed_nh3_mg_l_as_nh3": nh3_mol_l * NH3_MW * 1000.0,
        "feed_nh3_fraction": nh3_mol_l / max(nh4_mol_l + nh3_mol_l, 1e-30),
        "permeate_nh4_mg_l_as_nh4": permeate_nh4 * NH4_EQ_MW * 1000.0,
        "permeate_nh3_mg_l_as_nh3": permeate_nh3 * NH3_MW * 1000.0,
        "permeate_total_ammonia_mg_l_as_nh4": permeate_total
        * NH4_EQ_MW
        * 1000.0,
        "transport_basis": "NH4+ ionic passage + independent neutral NH3 passage",
    }


def membrane_carbonate_split(
    feed_comp: Mapping[str, float],
    temp_c: float,
    feed_state: dict,
    recovery: float,
    ionic_rejection: float,
    permeate_template: Mapping[str, float],
    concentrate_template: Mapping[str, float],
) -> dict:
    """Conserve carbon/components and solve downstream pH by electroneutrality."""
    y = min(max(float(recovery), 0.0), 0.999999999)
    rej = min(max(float(ionic_rejection), 0.0), 0.999999999)
    fcomp = feed_state.get("composition") or normalize_composition(feed_comp)
    kgwf = _base._kg_water_per_l(fcomp, temp_c)
    ct_l = float(feed_state["total_inorganic_carbon_mol_kg"]) * kgwf
    co2_l = float(feed_state["co2_mol_kg"]) * kgwf

    # Neutral CO2 concentration passage is unity; ionic inorganic carbon follows
    # the membrane ionic passage. The concentrate closes exact component balance.
    ct_p_l = co2_l + max(0.0, ct_l - co2_l) * (1.0 - rej)
    ct_c_l = (
        ct_l
        if y <= 1e-12
        else (ct_l - y * ct_p_l) / max(1.0 - y, 1e-30)
    )

    pbase = _base._base_noncarbonate_composition(permeate_template)
    cbase = _base._base_noncarbonate_composition(concentrate_template)
    kgwp = _base._kg_water_per_l(pbase, temp_c)
    kgwc = _base._kg_water_per_l(cbase, temp_c)

    permeate = solve_charge_balanced_state(pbase, temp_c, ct_p_l / max(kgwp, 1e-30))
    concentrate = solve_charge_balanced_state(cbase, temp_c, ct_c_l / max(kgwc, 1e-30))
    return {
        "feed": feed_state,
        "permeate": permeate,
        "concentrate": concentrate,
        "ionic_rejection": rej,
        "recovery": y,
        "transport_solver_basis": (
            "component mass balance + neutral CO2 passage + NH4/NH3 transport + electroneutrality"
        ),
    }


def mix_carbonate_streams(streams, temp_c: float) -> dict:
    """Mix transported components and CT, then solve pH by electroneutrality."""
    valid = [
        x
        for x in streams
        if float(x.get("flow", 0.0) or 0.0) > 0.0
        and x.get("composition")
        and x.get("state")
    ]
    if not valid:
        raise ValueError("At least one positive-flow carbonate stream is required for mixing.")
    qt = sum(float(x["flow"]) for x in valid)
    mix = {k: 0.0 for k in SPECIES}
    ct_l = 0.0
    for stream in valid:
        q = float(stream["flow"])
        comp = normalize_composition(stream["composition"])
        state = stream["state"]
        kgw = _base._kg_water_per_l(comp, temp_c)
        for key in SPECIES:
            mix[key] += q * comp[key] / qt
        ct_l += (
            q
            * float(state["total_inorganic_carbon_mol_kg"])
            * kgw
            / qt
        )
    base_comp = _base._base_noncarbonate_composition(mix)
    kgw_mix = _base._kg_water_per_l(base_comp, temp_c)
    state = solve_charge_balanced_state(
        base_comp, temp_c, ct_l / max(kgw_mix, 1e-30)
    )
    state["mixing_basis"] = (
        "flow-weighted transported components + total inorganic carbon + electroneutrality"
    )
    return state
