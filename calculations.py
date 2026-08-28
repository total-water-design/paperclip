import math
import os
from membrane_db import get_membrane
from pump_db import select_pump as select_vcmp_pump, curve_points as vcmp_curve_points
from osmotic_model import osmotic_state, nacl_equivalent_ionic_strength
from water_chemistry import (osmotic_state_from_composition, composition_from_request, total_tds_mg_l,
    normalize_composition, scale_composition, polarization_scale_composition, nf_polarization_scale_composition, mix_compositions, permeate_composition, nf_permeate_composition, nf_dynamic_rejections, concentrate_composition, SPECIES, solution_specific_gravity)
from osmotic_surrogate import get_surrogate
from chemistry_analysis import solve_carbonate_state, analytical_alkalinity_mol_kg, membrane_carbonate_split, mix_carbonate_streams, acid_dose_to_target_ph
from solver import AndersonMixer, SolverTrace, ThermodynamicStateCache, water_state_signature, water_state_snapshot
from compute_engine import raise_if_cancelled, set_compute_progress, advance_compute_progress

_PX_STATE_CACHE = ThermodynamicStateCache(max_entries=128)

FLOW_TO_M3H = {"m3/h": 1.0, "L/s": 3.6, "gpm": 0.227124707}
PSI_PER_BAR = 14.5037738
BAR_PER_PSI = 1 / PSI_PER_BAR
KV_PER_CV = 1.156
DIVALENT_CP_EXPONENT_MULTIPLIER = 1.35

REG = {
    "low": {
        "std": (6.602502660584673, 39.921808422295854),
        "cfd": (6.2398554051631, 44.44463643353859),
    },
    "high": {
        "std": (0.7444009214573731, 73.69887014309043),
        "cfd": (2.040755708597643, 67.11912592185516),
    },
}


def flow_to_m3h(value, unit):
    return float(value) * FLOW_TO_M3H[unit]


def flow_from_m3h(value, unit):
    return float(value) / FLOW_TO_M3H[unit]


def pressure_to_bar(value, unit):
    return float(value) if unit == "bar" else float(value) * BAR_PER_PSI


def pressure_from_bar(value, unit):
    return float(value) if unit == "bar" else float(value) / BAR_PER_PSI


def turbo_efficiency(q_m3h, cfd=True):
    if q_m3h <= 0:
        raise ValueError("Flow must be greater than zero.")
    curve = "cfd" if cfd else "std"
    if q_m3h <= 350:
        slope, intercept = REG["low"][curve]
    elif q_m3h < 3200:
        slope, intercept = REG["high"][curve]
    else:
        raise ValueError("Turbo efficiency correlation is valid only below 3200 m³/h.")
    return (slope * math.log(q_m3h) + intercept) / 100.0


def split_turbo_efficiency(overall_eff: float, pump_minus_turbine: float = 0.01):
    """Split overall turbocharger efficiency into pump and turbine efficiencies.

    Matches the user-supplied off-design workbook: eta_p = eta_t + 0.01 and
    eta_p * eta_t = overall efficiency.
    """
    e=max(0.0,min(0.999999,float(overall_eff))); d=float(pump_minus_turbine)
    pump=(d + math.sqrt(d*d + 4.0*e))/2.0
    turbine=pump-d
    return max(0.0,min(1.0,turbine)), max(0.0,min(1.0,pump))


def derate_turbo_component_efficiencies(turbine_eff, pump_eff, overall_penalty_pp, pre_scale_factor=1.0):
    """Apply an absolute overall-efficiency derate while keeping components consistent.

    ``overall_penalty_pp`` is supplied as an absolute efficiency fraction
    (0.03 = three percentage points). ``pre_scale_factor`` is an overall
    efficiency multiplier already imposed by another model (for example a Cv
    off-design penalty).  That multiplier is split equally in log/product space
    across turbine and pump components before the BiTurbo penalty is applied.

    The returned component efficiencies therefore satisfy, to floating-point
    precision, ``eta_t_net * eta_p_net == eta_overall_net``.
    """
    et=max(0.0,float(turbine_eff)); ep=max(0.0,float(pump_eff))
    scale=max(0.0,float(pre_scale_factor))
    if scale != 1.0:
        k0=math.sqrt(scale)
        et*=k0; ep*=k0
    pre=et*ep
    penalty=max(0.0,float(overall_penalty_pp))
    target=max(0.0,pre-penalty)
    if pre<=1e-15 or target<=0.0:
        return {
            "turbine_eff_pre_derate": et, "pump_eff_pre_derate": ep,
            "overall_eff_pre_derate": pre, "turbine_eff_net": 0.0,
            "pump_eff_net": 0.0, "overall_eff_net": 0.0,
            "component_derate_factor": 0.0, "overall_penalty_fraction": penalty,
        }
    k=math.sqrt(target/pre)
    etn=et*k; epn=ep*k
    return {
        "turbine_eff_pre_derate": et, "pump_eff_pre_derate": ep,
        "overall_eff_pre_derate": pre, "turbine_eff_net": etn,
        "pump_eff_net": epn, "overall_eff_net": etn*epn,
        "component_derate_factor": k, "overall_penalty_fraction": penalty,
    }


def off_design_turbo_efficiency(design_overall_eff, q_pump, q_turbine, p_pump, p_turbine,
                                design_q_pump, design_q_turbine, design_p_pump, design_p_turbine):
    """Workbook-based turbocharger off-design efficiency correlation.

    Turbine efficiency de-rates quadratically with turbine flow and turbine
    inlet pressure. Pump efficiency de-rates quadratically with pump flow and
    pump discharge pressure. The design efficiencies are recovered exactly at
    the locked design duty point.
    """
    et0, ep0 = split_turbo_efficiency(design_overall_eff)
    def penalty(base, x, x0, p, p0):
        if abs(x0) < 1e-12 or abs(p0) < 1e-12: return base
        # Exact workbook equation: no hidden clipping is applied. If an
        # extreme extrapolation leaves the physical 0..1 range, the result is
        # flagged so the engineer can treat that case as outside the calibrated map.
        return base - (base/(x0*x0))*(x-x0)**2 - (base/(p0*p0))*(p-p0)**2
    et=penalty(et0,float(q_turbine),float(design_q_turbine),float(p_turbine),float(design_p_turbine))
    ep=penalty(ep0,float(q_pump),float(design_q_pump),float(p_pump),float(design_p_pump))
    return {"turbine_eff":et,"pump_eff":ep,"overall_eff":et*ep,
            "design_turbine_eff":et0,"design_pump_eff":ep0,"design_overall_eff":float(design_overall_eff),
            "efficiency_extrapolated": not (0.0 <= et <= 1.0 and 0.0 <= ep <= 1.0)}


def _turbo_case_efficiency(data, q_pump, q_turbine, p_pump, p_turbine, prefix=""):
    """Return design/off-design turbo efficiency for one turbine/pump pair."""
    key=lambda n:f"{prefix}{n}" if prefix else n
    design_mode=str(data.get(key("off_design_model"), data.get("off_design_model",""))).lower()
    dqf=_float(data,key("design_qf"),None); dqr=_float(data,key("design_qr"),None)
    dpm=_float(data,key("design_pm"),None); dpr=_float(data,key("design_pr"),None)
    deff=_float(data,key("design_overall_eff"),None)
    if design_mode in {"spreadsheet","locked","case_locked"} and None not in (dqf,dqr,dpm,dpr):
        if deff is None:
            deff=turbo_efficiency(float(dqf), data.get("curve","cfd")=="cfd")
        out=off_design_turbo_efficiency(deff,q_pump,q_turbine,p_pump,p_turbine,dqf,dqr,dpm,dpr)
        out["method"]="Locked design duty · workbook quadratic off-design"
        return out
    overall=turbo_efficiency(float(q_pump), data.get("curve","cfd")=="cfd")
    et,ep=split_turbo_efficiency(overall)
    return {"turbine_eff":et,"pump_eff":ep,"overall_eff":overall,
            "design_turbine_eff":et,"design_pump_eff":ep,"design_overall_eff":overall,
            "method":"3D/standard design-point efficiency correlation"}




TURBO_MIN_REJECT_RATIO = 0.20
TURBO_PEAK_REJECT_RATIO_LOW = 0.65
TURBO_PEAK_REJECT_RATIO_HIGH = 0.70
BITURBO_MIN_LOCAL_TDS_MG_L = 30000.0

def turbo_reject_ratio(q_turbine, q_pump):
    """Return the canonical turbocharger reject ratio Qtr/Qpf.

    Qtr is the reject/brine flow through the turbine side of the turbocharger.
    Qpf is the flow through the pump side of the same turbocharger.
    """
    qp=float(q_pump or 0.0); qt=float(q_turbine or 0.0)
    if qp <= 0:
        raise ValueError("Turbocharger pump-side flow Qpf must be greater than zero.")
    return qt/qp

def turbo_reject_ratio_status(ratio):
    r=float(ratio)
    if r <= TURBO_MIN_REJECT_RATIO + 1e-12:
        return "not_allowed"
    if TURBO_PEAK_REJECT_RATIO_LOW <= r <= TURBO_PEAK_REJECT_RATIO_HIGH:
        return "peak"
    if r < 0.50:
        return "poor"
    if r < TURBO_PEAK_REJECT_RATIO_LOW:
        return "good"
    return "acceptable"

def _enforce_turbo_reject_ratio(q_turbine, q_pump, label="Turbocharger"):
    rr=turbo_reject_ratio(q_turbine,q_pump)
    if rr <= TURBO_MIN_REJECT_RATIO + 1e-12:
        raise ValueError(
            f"{label} is not allowed because Reject Ratio Qtr/Qpf = {rr:.3f} is at or below the 0.20 minimum. "
            "Expected turbocharger efficiency is too low at this turbine-side/pump-side flow match."
        )
    return rr

def _float(data, key, default=None):
    value = data.get(key, default)
    if value is None or value == "":
        return None
    return float(value)


def _bool(data, key, default=False):
    v = data.get(key, default)
    if isinstance(v, bool):
        return v
    return str(v).lower() in {"1", "true", "yes", "on", "coupled"}


def _nested_cpu_disabled(data):
    """Return True when an outer batch already owns CPU parallelism.

    The legacy _disable_inner_parallel key is preserved for backward-compatible
    saved/test payloads.  GPU permission is intentionally independent.
    """
    return _bool(data, "_disable_nested_cpu_pool", False) or _bool(data, "_disable_inner_parallel", False)


def _gpu_disabled(data):
    return _bool(data, "_disable_gpu", False) or os.environ.get("CALCOSPOWER_DISABLE_GPU", "0") == "1"

def _vfd_eff(data, eff_key, no_vfd_key):
    """Return 1.0 when the user explicitly selects No VFD."""
    return 1.0 if _bool(data, no_vfd_key, False) else float(data.get(eff_key, 1.0))

def _pump_wire_power_kw(flow_m3h, dp_bar, pump_eff, motor_eff, vfd_eff):
    hyd = max(0.0, float(flow_m3h))*max(0.0, float(dp_bar))/36.0
    return hyd / max(float(pump_eff)*float(motor_eff)*float(vfd_eff), 1e-12)



def osmotic_pressure_bar(tds_ppm, temperature_c=25.0, ionic_strength=None):
    return osmotic_state(tds_ppm, temperature_c, ionic_strength)["osmotic_bar"]


def _osmotic_for_concentration(tds_ppm, temperature_c, reference_tds_ppm=None, reference_ionic_strength=None):
    """Osmotic state using optional feed ionic-strength calibration.

    If a feed ionic strength is supplied, downstream ionic strength scales with
    concentration relative to the feed. Otherwise TDS is treated as NaCl-equivalent.
    """
    i = None
    if reference_ionic_strength is not None and reference_tds_ppm and reference_tds_ppm > 0:
        i = max(0.0, float(reference_ionic_strength) * float(tds_ppm) / float(reference_tds_ppm))
    return osmotic_state(tds_ppm, temperature_c, i)


def _element_clean_dp_bar(q_feed_m3h, q_conc_m3h, element_diameter_in=8.0):
    """DuPont FilmTec Technical Manual Eq. 67 for one 8-inch element.

    Delta P_fc [psi] = 0.01 * qbar_fc^1.7, with qbar_fc in US gpm.
    Applied element-by-element so the declining concentrate-side flow is respected.
    """
    qbar_m3h = 0.5 * (float(q_feed_m3h) + float(q_conc_m3h))
    qbar_gpm = flow_from_m3h(max(qbar_m3h, 0.0), "gpm")
    # Eq.67 is an 8-inch correlation. For smaller specialty elements we use
    # an equal-superficial-velocity diameter scaling as an engineering approximation.
    diameter = max(float(element_diameter_in), 0.1)
    q_equiv_8in_gpm = qbar_gpm * (8.0 / diameter) ** 2
    dp_psi = 0.01 * (q_equiv_8in_gpm ** 1.7)
    return dp_psi * BAR_PER_PSI


def clean_stage_pressure_drop(q_feed_m3h, q_reject_m3h, vessels, elements_per_vessel):
    """Clean-vessel pressure drop using FilmTec Eq. 67 element by element.

    When only total stage feed/reject flows are known, use DuPont Eq. 62 to
    distribute the total recovery uniformly as an equivalent element recovery.
    """
    if vessels <= 0 or elements_per_vessel <= 0:
        raise ValueError("Pressure vessels and elements per vessel must be positive.")
    qin = float(q_feed_m3h) / float(vessels)
    qfinal = float(q_reject_m3h) / float(vessels)
    if qfinal <= 0 or qfinal > qin:
        raise ValueError("Reject flow must be greater than zero and no greater than feed flow.")
    n = int(elements_per_vessel)
    factor = (qfinal / qin) ** (1.0 / n)
    total_dp = 0.0
    element_dps = []
    element_flows = []
    for i in range(n):
        qout = qin * factor
        dp = _element_clean_dp_bar(qin, qout)
        total_dp += dp
        element_dps.append(dp)
        element_flows.append({"element": i + 1, "feed_m3h": qin, "reject_m3h": qout, "dp_bar": dp})
        qin = qout
    return total_dp, element_dps, element_flows


def _membrane_model_coefficients(m):
    """Calibrate simplified solution-diffusion A and B to datasheet test data.

    A is recalibrated using the user's osmotic-pressure rule and DuPont's clean
    element pressure-drop correlation. B follows Wang et al. solution-diffusion
    R = Jw/(Jw+B), rearranged at the datasheet test point.
    """
    r = float(m["rejection_pct"]) / 100.0
    j_test = float(m["test_flux_lmh"])

    # Shared-catalog records may carry A/B values already calibrated on this
    # exact Total RO Design transport basis. Use them only when both are present;
    # all existing records continue through the established legacy calibration.
    explicit_a = m.get("water_permeability_A_lmh_bar")
    if explicit_a in (None, ""):
        explicit_a = m.get("specific_flux_A_app_lmh_bar")
    explicit_b = m.get("salt_permeability_B_lmh")
    if explicit_a not in (None, "") and explicit_b not in (None, ""):
        return float(explicit_a), float(explicit_b)

    b_lmh = j_test * max(1.0 - r, 1e-9) / max(r, 1e-9)
    # NF records can carry a water-permeability calibration obtained from
    # multiple manufacturer salt test points.  Do not force those records back
    # through the legacy NaCl-equivalent TDS calibration.
    a_nf = m.get("water_permeability_A_lmh_bar")
    if a_nf is not None:
        return float(a_nf), b_lmh

    test_rec = float(m.get("recovery_pct", 8.0)) / 100.0
    test_qp = float(m["flow_m3d"]) / 24.0
    test_qf = test_qp / max(test_rec, 1e-9)
    test_qc = test_qf - test_qp
    test_dp = _element_clean_dp_bar(test_qf, test_qc, m.get("diameter_in", 8.0))
    cf = float(m["tds_ppm"])
    # Datasheet observed rejection used to close a simple test salt balance.
    cp = cf * (1.0 - r)
    cc = (test_qf * cf - test_qp * cp) / max(test_qc, 1e-9)
    cavg = 0.5 * (cf + cc)
    pf = math.exp(0.7 * test_rec)  # DuPont Eq. 55 for an 8-inch element
    test_temp_c = float(m.get("temp_c", 25.0))
    pi_surface = osmotic_pressure_bar(cavg * pf, test_temp_c)
    pi_perm = osmotic_pressure_bar(cp, test_temp_c)
    p_test = float(m["pressure_psi"]) * BAR_PER_PSI
    ndp_test = p_test - test_dp / 2.0 - (pi_surface - pi_perm)
    if ndp_test <= 0:
        # Fallback only for malformed/edge datasheet records.
        a_lmh_bar = float(m["specific_flux_A_app_lmh_bar"])
    else:
        a_lmh_bar = j_test / ndp_test
    return a_lmh_bar, b_lmh




def _temperature_transport_parameters(m, temperature_c):
    """Return Jin/Jawor/Kim/Hoek temperature corrections for membrane A and B.

    Jin et al., Desalination 239 (2009) Eq. 16a/16b express water and
    solute permeability relative to 25 C as an Arrhenius-type function.
    CalcOsPower generalizes the same relation to the membrane datasheet test
    temperature so coefficients calibrated at non-25 C test points remain
    self-consistent.

    The paper's fitted experimental coefficients are used as defaults for
    polyamide RO/NF membranes (RO: XLE basis; NF: NF90 basis). Individual
    membrane records may override either coefficient when a manufacturer- or
    membrane-specific value is available. Negative K values make permeability
    increase with increasing temperature, as reported in the paper.
    """
    t_ref_c = float(m.get("temp_c", 25.0))
    t_c = float(temperature_c)
    membrane_type = str(m.get("membrane_type", "RO")).strip().upper()
    if membrane_type == "NF":
        kw_default = -2385.0
        ks_default = -3405.0
        basis = "Jin et al. 2009 fitted NF90 polyamide temperature coefficients"
    else:
        kw_default = -2849.0
        ks_default = -3281.0
        basis = "Jin et al. 2009 fitted XLE polyamide RO temperature coefficients"
    kw = float(m.get("water_temp_coefficient_k", kw_default))
    ks = float(m.get("salt_temp_coefficient_k", ks_default))
    tk = 273.15 + t_c
    trefk = 273.15 + t_ref_c
    if tk <= 0 or trefk <= 0:
        raise ValueError("Membrane temperature must be above absolute zero.")
    a_factor = math.exp(kw * (1.0 / tk - 1.0 / trefk))
    b_factor = math.exp(ks * (1.0 / tk - 1.0 / trefk))
    return {
        "reference_temperature_c": t_ref_c,
        "water_temp_coefficient_k": kw,
        "salt_temp_coefficient_k": ks,
        "water_temperature_factor": a_factor,
        "salt_temperature_factor": b_factor,
        "temperature_transport_basis": basis,
    }

def _membrane_pressure_limit_bar(m, temperature_c):
    table = m.get("max_pressure_by_temp")
    if not table:
        return float(m.get("max_operating_pressure_bar", 83.0))
    pts = sorted((float(t), float(p)) for t,p in table)
    t = float(temperature_c)
    if t <= pts[0][0]: return pts[0][1]
    if t >= pts[-1][0]: return pts[-1][1]
    for (t0,p0),(t1,p1) in zip(pts,pts[1:]):
        if t0 <= t <= t1:
            f=(t-t0)/(t1-t0)
            return p0+f*(p1-p0)
    return pts[-1][1]

# Numerical convergence policy. Hydraulics stop at engineering-significant
# precision; chemistry/speciation remains tighter and all intermediate values
# retain full floating-point precision.
HYDRAULIC_PRESSURE_ABS_TOL_BAR = 1e-3
ELEMENT_FLOW_ABS_TOL_M3H = 1e-3
ELEMENT_FLOW_REL_TOL = 1e-4
ELEMENT_TDS_REL_TOL = 1e-6


def _normalize_membrane_recipe(membrane_id, elements_per_vessel, membrane_recipe=None):
    """Return one verified membrane record id per element position.

    ``membrane_recipe`` may be a JSON/list payload from the UI or a compact
    comma-separated string.  Empty positions fall back to the stage membrane so
    legacy uniform-array projects remain fully compatible.
    """
    n = int(elements_per_vessel)
    recipe = membrane_recipe
    if recipe in (None, ""):
        return [str(membrane_id)] * n
    if isinstance(recipe, str):
        raw = recipe.strip()
        if raw.startswith('['):
            try:
                import json
                recipe = json.loads(raw)
            except Exception:
                recipe = [x.strip() for x in raw.split(',') if x.strip()]
        else:
            recipe = [x.strip() for x in raw.split(',') if x.strip()]
    if not isinstance(recipe, (list, tuple)):
        raise ValueError("Hybrid membrane recipe must be a list of membrane record IDs.")
    recipe = [str(x or membrane_id) for x in recipe]
    if len(recipe) != n:
        raise ValueError(f"Hybrid membrane recipe contains {len(recipe)} positions but the vessel has {n} elements.")
    # Validate all records immediately so a typo cannot silently reach a solver loop.
    for mid in recipe:
        get_membrane(mid)
    return recipe


def _recipe_summary(recipe):
    out=[]
    for mid in recipe:
        model=get_membrane(mid)['model']
        if out and out[-1][0]==model: out[-1][1]+=1
        else: out.append([model,1])
    return ' · '.join(f"{n}× {model}" for model,n in out)


def membrane_stage(q_feed_m3h, p_feed_bar, membrane_id, vessels, elements_per_vessel,
                   feed_tds_ppm, permeate_pressure_bar=0.0, temperature_c=25.0,
                   feed_ionic_strength=None, datasheet_max_dp_per_element_bar=1.0,
                   feed_composition=None, feed_ph=7.6, water_mode="tds",
                   fouling_factor=1.0, salt_passage_factor=1.0,
                   feed_carbonate_state=None, resolve_carbonate_streams=True,
                   membrane_recipe=None):
    """Element-to-element clean RO stage calculation.

    Water transport uses the datasheet-calibrated solution-diffusion model.
    Osmotic pressure can be calculated in two ways:
      * water_mode='tds': legacy TDS/NaCl-equivalent phi(T,I) model.
      * water_mode='full': actual multi-ion composition, preferably through
        a pyEQL-calibrated effective-Pitzer osmotic surrogate (with a transparent
        internal multi-ion fallback if pyEQL is unavailable).

    In full-analysis mode each ion is mass-balanced element by element. RO
    membranes use the dynamic overall salt-passage model (with the datasheet
    boron rejection where available). Calculation-ready NF membranes instead
    use manufacturer-calibrated, charge-balanced salt-pair transport with
    separate mono/mono, mixed-valence, and divalent/divalent passage classes.
    Carbonate alkalinity/CT are propagated separately and re-equilibrated
    element-by-element. During
    inverse-pressure trial evaluations this expensive reporting chemistry can
    be suppressed; the converged duty is always recalculated with it enabled.
    """
    if q_feed_m3h <= 0:
        raise ValueError("Membrane stage feed flow must be greater than zero.")
    if vessels <= 0:
        raise ValueError("Number of pressure vessels must be greater than zero.")
    n = int(elements_per_vessel)
    if n != elements_per_vessel or not (1 <= n <= 8):
        raise ValueError("Membranes per pressure vessel must be an integer from 1 to 8.")

    full = str(water_mode).lower() == "full"
    carbonate_feed_state = None
    analytical_feed_comp = None
    if full:
        # v17.2 analytical basis: bicarbonate input is total alkalinity (mg/L as
        # HCO3-equivalent); carbonate input is lab-reported QC only. Convert to
        # an equilibrium composition before the membrane/osmotic calculation.
        analytical_feed_comp = dict(feed_composition or {})
        # Fast inverse-solver passes intentionally suppress downstream carbonate
        # reporting. Older interstage/BiTurbo handoff code can therefore supply a
        # carbonate-state dictionary whose TA/CT members are None. Treat that as
        # "state unavailable" rather than attempting float(None), which caused
        # every parallel pressure candidate to fail and was then misreported as
        # "No valid pressure range". The converged full-detail solve still
        # propagates the exact upstream TA/CT state.
        valid_feed_carbonate_state = False
        prepared_feed_state = False
        if isinstance(feed_carbonate_state, dict):
            try:
                ta_state = float(feed_carbonate_state.get('total_alkalinity_mol_kg'))
                ct_state = float(feed_carbonate_state.get('total_inorganic_carbon_mol_kg'))
                valid_feed_carbonate_state = math.isfinite(ta_state) and math.isfinite(ct_state)
                prepared_feed_state = valid_feed_carbonate_state and bool(feed_carbonate_state.get('_prepared_feed_state')) and bool(feed_carbonate_state.get('composition'))
            except (TypeError, ValueError):
                valid_feed_carbonate_state = False
                prepared_feed_state = False
        if prepared_feed_state:
            # Water Quality / request preparation already solved this exact feed
            # state.  Reuse it across all pressure trials instead of repeating
            # the same full Pitzer/carbonate root solve at every candidate.
            carbonate_feed_state = feed_carbonate_state
        elif valid_feed_carbonate_state:
            carbonate_feed_state = solve_carbonate_state(
                analytical_feed_comp, temperature_c,
                total_alkalinity_mol_kg=ta_state,
                total_inorganic_carbon_mol_kg=ct_state)
        else:
            ta_feed = analytical_alkalinity_mol_kg(analytical_feed_comp, temperature_c)
            carbonate_feed_state = solve_carbonate_state(
                analytical_feed_comp, temperature_c, ph=float(feed_ph),
                total_alkalinity_mol_kg=ta_feed)
        feed_ph = float(carbonate_feed_state['ph'])
        feed_comp = normalize_composition(carbonate_feed_state['composition'])
        feed_tds_ppm = total_tds_mg_l(feed_comp)
        if feed_tds_ppm <= 0:
            raise ValueError("Full water analysis mode requires at least one species concentration.")
    else:
        feed_comp = None
        if feed_tds_ppm < 0:
            raise ValueError("Feed TDS cannot be negative.")

    recipe = _normalize_membrane_recipe(membrane_id, n, membrane_recipe)
    membrane_records = [get_membrane(mid) for mid in recipe]
    if any(str(mm.get("membrane_type", "RO")).upper() == "NF" for mm in membrane_records) and not full:
        raise ValueError("Calculation-ready NF membranes require Full Water Analysis mode so monovalent/divalent salt selectivity can be applied to the actual ion composition.")
    uniform_recipe = len(set(recipe)) == 1
    stage_primary = membrane_records[0]
    max_pressure_bar = min(_membrane_pressure_limit_bar(mm, temperature_c) for mm in membrane_records)
    if float(p_feed_bar) > max_pressure_bar + 1e-9:
        limiting = min(membrane_records, key=lambda mm: _membrane_pressure_limit_bar(mm, temperature_c))
        raise ValueError(f"Hybrid/stage membrane {limiting['model']} is limited to {max_pressure_bar:.1f} bar at the applicable datasheet condition.")
    area_per_position = [float(mm["area_m2"]) for mm in membrane_records]
    area_total = sum(area_per_position) * float(vessels)
    fouling_factor = min(max(float(fouling_factor), 0.30), 1.20)
    salt_passage_factor = min(max(float(salt_passage_factor), 0.25), 5.0)
    element_transport=[]
    for mm in membrane_records:
        a_ds,b_ds=_membrane_model_coefficients(mm)
        tt=_temperature_transport_parameters(mm,temperature_c)
        a_clean=a_ds*tt["water_temperature_factor"]
        b_clean=b_ds*tt["salt_temperature_factor"]
        r=float(mm["rejection_pct"])/100.0
        rb=mm.get("boron_rejection_pct"); rb=None if rb is None else float(rb)/100.0
        is_nf=str(mm.get("membrane_type", "RO")).upper()=="NF" and mm.get("nf_b_mono_mono_lmh") is not None and mm.get("nf_b_divalent_divalent_lmh") is not None
        nf_b_mm_ds=float(mm.get("nf_b_mono_mono_lmh", b_ds))
        nf_b_dd_ds=float(mm.get("nf_b_divalent_divalent_lmh", b_ds))
        nf_b_mix_raw=mm.get("nf_b_mixed_lmh")
        nf_b_mix_ds=None if nf_b_mix_raw is None else float(nf_b_mix_raw)
        nf_b_neu_raw=mm.get("nf_b_neutral_lmh")
        nf_b_neu_ds=None if nf_b_neu_raw is None else float(nf_b_neu_raw)
        btemp=tt["salt_temperature_factor"]*salt_passage_factor
        element_transport.append({"m":mm,"a_ds":a_ds,"b_ds":b_ds,"temp":tt,"a_clean":a_clean,"b_clean":b_clean,
                                  "a":a_clean*fouling_factor,"b":b_clean*salt_passage_factor,"r_test":r,"rb_test":rb,
                                  "is_nf":is_nf,
                                  "nf_b_mm":nf_b_mm_ds*btemp,"nf_b_dd":nf_b_dd_ds*btemp,
                                  "nf_b_mix":None if nf_b_mix_ds is None else nf_b_mix_ds*btemp,
                                  "nf_b_neutral":None if nf_b_neu_ds is None else nf_b_neu_ds*btemp,
                                  "max_dp":float(mm.get("max_dp_per_element_bar",datasheet_max_dp_per_element_bar))})
    # Stage summary transport values are membrane-area-weighted; element-level
    # calculations always use the exact membrane loaded at that position.
    area_sum=max(sum(area_per_position),1e-12)
    def _aw(key): return sum(t[key]*a for t,a in zip(element_transport,area_per_position))/area_sum
    a_datasheet_lmh_bar=_aw("a_ds"); b_datasheet_lmh=_aw("b_ds")
    a_clean_lmh_bar=_aw("a_clean"); b_clean_lmh=_aw("b_clean")
    a_lmh_bar=_aw("a"); b_lmh=_aw("b")
    temp_transport=element_transport[0]["temp"]
    r_test=_aw("r_test")
    rb_vals=[(t["rb_test"],a) for t,a in zip(element_transport,area_per_position) if t["rb_test"] is not None]
    rb_test=(sum(v*a for v,a in rb_vals)/sum(a for _,a in rb_vals)) if rb_vals else None
    datasheet_max_dp_per_element_bar=min(t["max_dp"] for t in element_transport)
    area_each=area_sum/n

    def osm_state_tds(tds):
        return _osmotic_for_concentration(tds, temperature_c, feed_tds_ppm, feed_ionic_strength)

    # Full-analysis hot path: calibrate pyEQL once per unique case and reuse the
    # surrogate through all element iterations and inverse-pressure passes.
    _osmotic_surrogate = get_surrogate(feed_comp, temperature_c, feed_ph) if full else None

    def osm_state_comp(comp):
        return _osmotic_surrogate.state(comp) if _osmotic_surrogate is not None else osmotic_state_from_composition(comp, temperature_c, feed_ph)

    def boron_dynamic_rejection(overall_rej, r_base, rb_base):
        if rb_base is None:
            return overall_rej
        base_pass = max(1.0-r_base, 1e-9)
        ratio = max(0.0, (1.0-rb_base) / base_pass)
        return min(max(1.0 - (1.0-overall_rej)*ratio, 0.0), 0.999999999)

    qin = float(q_feed_m3h) / float(vessels)
    cin = float(feed_tds_ppm)
    comp_in = normalize_composition(feed_comp) if full else None
    pin = float(p_feed_bar)
    total_perm_vessel = 0.0
    salt_perm_vessel = 0.0
    species_perm_mass = {k: 0.0 for k in SPECIES}
    element_results = []
    carbonate_state_current = carbonate_feed_state if full else None
    carbonate_permeate_streams = []
    # Running mixed-permeate state.  The previous implementation repeatedly
    # remixed every historical element stream to reconstruct the same upstream
    # cumulative state.  Carrying the exact prior mixture forward is
    # algebraically equivalent and removes duplicate carbonate/Pitzer solves.
    cumulative_permeate_state_current = None
    cumulative_permeate_comp_current = None

    for elem in range(1, n + 1):
        raise_if_cancelled()
        tr = element_transport[elem-1]
        m = tr["m"]
        area_each = float(m["area_m2"])
        a_lmh_bar = tr["a"]; b_lmh = tr["b"]
        is_nf = bool(tr.get("is_nf"))
        r_test_local = tr["r_test"]; rb_test_local = tr["rb_test"]
        max_pressure_local = _membrane_pressure_limit_bar(m, temperature_c)
        if pin > max_pressure_local + 1e-9:
            raise ValueError(f"Element {elem} membrane {m['model']} is limited to {max_pressure_local:.1f} bar at the calculated local condition.")
        qp = min(qin * 0.08, max(qin * 0.001, 0.01))
        cp = cin * (1.0-r_test_local)
        if full and is_nf:
            cp_comp = nf_permeate_composition(comp_in, float(m.get("test_flux_lmh", 30.0)),
                                               tr["nf_b_mm"], tr["nf_b_dd"], tr.get("nf_b_mix"), tr.get("nf_b_neutral"))
            cp = total_tds_mg_l(cp_comp)
        else:
            cp_comp = permeate_composition(comp_in, r_test_local, rb_test_local) if full else None
        last_qp = None
        element_relax = 0.45
        element_relax_history = [element_relax]
        previous_raw_residual = None
        previous_q_residual = None
        for iteration in range(240):
            if iteration % 8 == 0:
                raise_if_cancelled()
            qout = max(qin - qp, qin * 1e-6)
            yi = qp / qin
            pf = math.exp(0.7 * yi)
            pf_divalent = math.exp(0.7 * DIVALENT_CP_EXPONENT_MULTIPLIER * yi)
            dp = _element_clean_dp_bar(qin, qout, m.get("diameter_in", 8.0))
            pavg = pin - dp / 2.0

            if full:
                comp_out = concentrate_composition(comp_in, qin, cp_comp, qp)
                cavg_comp = {k: 0.5*(comp_in[k]+comp_out[k]) for k in SPECIES}
                cm_comp = (nf_polarization_scale_composition(cavg_comp, pf, pf_divalent)
                           if is_nf else polarization_scale_composition(cavg_comp, pf, pf_divalent))
                osm_m = osm_state_comp(cm_comp)
                osm_p = osm_state_comp(cp_comp)
                cm_tds = total_tds_mg_l(cm_comp)
                cc = total_tds_mg_l(comp_out)
                cp = total_tds_mg_l(cp_comp)
            else:
                cc = max(cin, (qin * cin - qp * cp) / qout)
                cavg = 0.5 * (cin + cc)
                cm_tds = cavg * pf
                osm_m = osm_state_tds(cm_tds)
                osm_p = osm_state_tds(cp)

            ndp = pavg - float(permeate_pressure_bar) - (osm_m["osmotic_bar"] - osm_p["osmotic_bar"])
            flux = max(0.0, a_lmh_bar * ndp)
            qp_new = min(qin * 0.90, flux * area_each / 1000.0)
            rej = flux / (flux + b_lmh) if (flux + b_lmh) > 0 else 0.0
            nf_rej_local = None
            if full:
                if is_nf:
                    nf_rej_local = nf_dynamic_rejections(flux, tr["nf_b_mm"], tr["nf_b_dd"], tr.get("nf_b_mix"), tr.get("nf_b_neutral"))
                    cp_new_comp = nf_permeate_composition(cm_comp, flux, tr["nf_b_mm"], tr["nf_b_dd"], tr.get("nf_b_mix"), tr.get("nf_b_neutral"))
                    cp_new = total_tds_mg_l(cp_new_comp)
                    rej = min(max(1.0-cp_new/max(total_tds_mg_l(cm_comp),1e-12),0.0),0.999999999)
                else:
                    cp_new_comp = permeate_composition(cm_comp, rej, boron_dynamic_rejection(rej, r_test_local, rb_test_local))
                    cp_new = total_tds_mg_l(cp_new_comp)
            else:
                cp_new = max(0.0, cm_tds * (1.0 - rej))
                cp_new_comp = None
            # The membrane element fixed-point map can become oscillatory at high
            # local recovery.  Retain the historical 45% update when it contracts,
            # but automatically damp the step when the raw fixed-point residual
            # grows or alternates without sufficient contraction.  This changes
            # only the numerical path, not the converged membrane equations.
            q_residual = qp_new - qp
            c_residual = cp_new - cp
            raw_residual = max(abs(q_residual)/max(1.0,qin), abs(c_residual)/max(1.0,cin))
            if previous_raw_residual is not None:
                growing = raw_residual > previous_raw_residual * 1.05
                oscillating = (previous_q_residual is not None and q_residual * previous_q_residual < 0.0
                               and abs(q_residual) > 0.75 * abs(previous_q_residual))
                if growing or oscillating:
                    reduced_relax = max(0.12, element_relax * 0.5)
                    if reduced_relax != element_relax:
                        element_relax = reduced_relax
                        element_relax_history.append(element_relax)
            qp_next = qp + element_relax * q_residual
            cp_next = cp + element_relax * c_residual
            if full:
                cp_comp = {k: cp_comp[k] + element_relax*(cp_new_comp[k]-cp_comp[k]) for k in SPECIES}
            if last_qp is not None and abs(q_residual) < max(ELEMENT_FLOW_ABS_TOL_M3H, ELEMENT_FLOW_REL_TOL*max(1.0,qin)) and abs(c_residual) < ELEMENT_TDS_REL_TOL*max(1.0,cin):
                qp, cp = qp_next, cp_next
                break
            previous_raw_residual = raw_residual
            previous_q_residual = q_residual
            last_qp = qp
            qp, cp = qp_next, cp_next
        else:
            raise ValueError(f"Membrane element {elem} did not converge.")

        qout = max(qin - qp, qin * 1e-9)
        yi = qp/qin
        pf = math.exp(0.7*yi)
        pf_divalent = math.exp(0.7*DIVALENT_CP_EXPONENT_MULTIPLIER*yi)
        dp = _element_clean_dp_bar(qin, qout, m.get("diameter_in",8.0))
        pavg = pin-dp/2.0
        if full:
            # Preserve the actual chemistry entering this element before the
            # concentrate state is advanced downstream.  For the tail element
            # this is the upstream-element concentrate chemistry requested by
            # the Tail Element Water Chemistry report.
            element_feed_comp = normalize_composition(comp_in)
            element_feed_state = carbonate_state_current
            upstream_perm_flow = total_perm_vessel
            upstream_perm_comp = ({k:species_perm_mass[k]/max(upstream_perm_flow,1e-12) for k in SPECIES}
                                  if upstream_perm_flow > 1e-12 else None)
            upstream_perm_state = cumulative_permeate_state_current if resolve_carbonate_streams else None
            if upstream_perm_state is not None:
                upstream_perm_comp = normalize_composition(cumulative_permeate_comp_current or upstream_perm_state['composition'])
            comp_out = concentrate_composition(comp_in, qin, cp_comp, qp)
            cavg_comp = {k:0.5*(comp_in[k]+comp_out[k]) for k in SPECIES}
            cm_comp = (nf_polarization_scale_composition(cavg_comp,pf,pf_divalent)
                       if is_nf else polarization_scale_composition(cavg_comp,pf,pf_divalent))
            osm_m = osm_state_comp(cm_comp); osm_p = osm_state_comp(cp_comp)
            csplit = None
            if resolve_carbonate_streams:
                carbonate_rej = (nf_rej_local or {}).get('mono_mono', rej) if is_nf else rej
                csplit=membrane_carbonate_split(comp_in,temperature_c,carbonate_state_current,yi,carbonate_rej,cp_comp,comp_out)
                cp_comp=normalize_composition(csplit['permeate']['composition'])
                comp_out=normalize_composition(csplit['concentrate']['composition'])
                carbonate_state_current=csplit['concentrate']
                carbonate_permeate_streams.append({'flow':qp,'composition':cp_comp,'state':csplit['permeate']})
            cumulative_out_flow = upstream_perm_flow + qp
            cumulative_out_comp = {k:(species_perm_mass[k] + qp*cp_comp[k])/max(cumulative_out_flow,1e-12) for k in SPECIES}
            cumulative_out_state = None
            if resolve_carbonate_streams and csplit is not None:
                try:
                    if upstream_perm_flow <= 1e-12 or upstream_perm_state is None or upstream_perm_comp is None:
                        cumulative_out_state = csplit['permeate']
                        cumulative_out_comp = normalize_composition(cp_comp)
                    else:
                        cumulative_out_state = mix_carbonate_streams([
                            {'flow':upstream_perm_flow,'composition':upstream_perm_comp,'state':upstream_perm_state},
                            {'flow':qp,'composition':cp_comp,'state':csplit['permeate']},
                        ], temperature_c)
                        cumulative_out_comp = normalize_composition(cumulative_out_state['composition'])
                    cumulative_permeate_state_current = cumulative_out_state
                    cumulative_permeate_comp_current = cumulative_out_comp
                except (KeyError, ValueError, ZeroDivisionError):
                    cumulative_out_state = None
            cin_now = total_tds_mg_l(element_feed_comp); cp = total_tds_mg_l(cp_comp); cc = total_tds_mg_l(comp_out)
        else:
            cc = max(cin,(qin*cin-qp*cp)/qout)
            cavg=0.5*(cin+cc); cm_tds=cavg*pf
            osm_m=osm_state_tds(cm_tds); osm_p=osm_state_tds(cp)
            cin_now=cin
        ndp = pavg-float(permeate_pressure_bar)-(osm_m["osmotic_bar"]-osm_p["osmotic_bar"])
        flux = qp*1000.0/area_each
        rej = flux/(flux+b_lmh) if (flux+b_lmh)>0 else 0.0
        e = {
            "element":elem,"feed_flow_m3h":qin,"permeate_flow_m3h":qp,"reject_flow_m3h":qout,
            "feed_pressure_bar":pin,"reject_pressure_bar":pin-dp,"dp_bar":dp,
            "feed_tds_ppm":cin_now,"permeate_tds_ppm":cp,"reject_tds_ppm":cc,
            "recovery":yi,"polarization_factor":pf,"polarization_factor_monovalent":pf,
            "polarization_factor_divalent":pf_divalent,"flux_lmh":flux,"rejection":rej,"ndp_bar":ndp,
            "feed_osmotic_bar": osm_state_comp(element_feed_comp)["osmotic_bar"] if full else osm_state_tds(cin)["osmotic_bar"],
            "membrane_surface_osmotic_bar": osm_m["osmotic_bar"],
            "membrane_id": recipe[elem-1], "membrane_manufacturer": m.get("manufacturer",""),
            "membrane_model": m.get("model",""), "membrane_area_m2": area_each,
            "convergence_iterations": iteration + 1,
            "convergence_flow_residual_m3h": q_residual,
            "convergence_tds_residual_mg_l": c_residual,
            "convergence_relaxation_factor": element_relax,
            "convergence_relaxation_history": element_relax_history,
        }
        if is_nf:
            nf_now=nf_dynamic_rejections(flux,tr["nf_b_mm"],tr["nf_b_dd"],tr.get("nf_b_mix"),tr.get("nf_b_neutral"))
            e.update({
                "nf_rejection_mono_mono":nf_now["mono_mono"],
                "nf_rejection_divalent_divalent":nf_now["divalent_divalent"],
                "nf_rejection_mixed_valence":nf_now["mixed_valence"],
                "nf_transport_model":"charge-balanced salt-pair solution-diffusion",
            })
        if full:
            e.update({
                "feed_composition_mg_l": element_feed_comp,
                "permeate_composition_mg_l": normalize_composition(cp_comp),
                "reject_composition_mg_l": normalize_composition(comp_out),
                "cumulative_permeate_in_flow_m3h": upstream_perm_flow,
                "cumulative_permeate_in_composition_mg_l": upstream_perm_comp,
                "cumulative_permeate_out_flow_m3h": cumulative_out_flow,
                "cumulative_permeate_out_composition_mg_l": cumulative_out_comp,
            })
            if element_feed_state is not None:
                e["feed_ph"] = float(element_feed_state.get("ph", feed_ph))
                e["feed_alkalinity_mg_l_as_hco3"] = float(element_feed_state.get("total_alkalinity_mg_l_as_hco3", 0.0))
            if csplit is not None:
                e["permeate_ph"] = float(csplit["permeate"].get("ph", feed_ph))
                e["permeate_alkalinity_mg_l_as_hco3"] = float(csplit["permeate"].get("total_alkalinity_mg_l_as_hco3", 0.0))
                e["reject_ph"] = float(csplit["concentrate"].get("ph", feed_ph))
                e["reject_alkalinity_mg_l_as_hco3"] = float(csplit["concentrate"].get("total_alkalinity_mg_l_as_hco3", 0.0))
            if upstream_perm_state is not None:
                e["cumulative_permeate_in_ph"] = float(upstream_perm_state.get("ph", feed_ph))
                e["cumulative_permeate_in_alkalinity_mg_l_as_hco3"] = float(upstream_perm_state.get("total_alkalinity_mg_l_as_hco3", 0.0))
            if cumulative_out_state is not None:
                e["cumulative_permeate_out_ph"] = float(cumulative_out_state.get("ph", feed_ph))
                e["cumulative_permeate_out_alkalinity_mg_l_as_hco3"] = float(cumulative_out_state.get("total_alkalinity_mg_l_as_hco3", 0.0))
        element_results.append(e)
        total_perm_vessel += qp
        salt_perm_vessel += qp*cp
        if full:
            for k in SPECIES:
                species_perm_mass[k] += qp*cp_comp[k]
            comp_in = comp_out
        qin, cin, pin = qout, cc, pin-dp

    qp_total=total_perm_vessel*float(vessels); qc_total=qin*float(vessels)
    recovery=qp_total/float(q_feed_m3h)
    cp_stage=salt_perm_vessel/max(total_perm_vessel,1e-12)
    stage_dp=float(p_feed_bar)-pin; avg_dp=stage_dp/n
    max_actual=max(e["dp_bar"] for e in element_results)
    dp_limit_fraction=max((e["dp_bar"]/max(element_transport[i]["max_dp"],1e-12) for i,e in enumerate(element_results)), default=0.0)
    datasheet_max_stage_dp_bar=sum(t["max_dp"] for t in element_transport)
    avg_flux=qp_total*1000.0/area_total
    avg_polarization_factor=sum(e["polarization_factor"] for e in element_results)/n
    avg_polarization_factor_divalent=sum(e["polarization_factor_divalent"] for e in element_results)/n
    nf_elements=[e for e in element_results if e.get("nf_transport_model")]
    nf_summary={}
    if nf_elements:
        nf_summary={
            "nf_transport_model":"charge-balanced salt-pair solution-diffusion",
            "nf_avg_rejection_mono_mono_pct":100.0*sum(e["nf_rejection_mono_mono"] for e in nf_elements)/len(nf_elements),
            "nf_avg_rejection_mixed_valence_pct":100.0*sum(e["nf_rejection_mixed_valence"] for e in nf_elements)/len(nf_elements),
            "nf_avg_rejection_divalent_divalent_pct":100.0*sum(e["nf_rejection_divalent_divalent"] for e in nf_elements)/len(nf_elements),
        }

    if full:
        feed_comp_norm=normalize_composition(feed_comp)
        conc_comp=normalize_composition(comp_in)
        perm_comp={k:species_perm_mass[k]/max(total_perm_vessel,1e-12) for k in SPECIES}
        if resolve_carbonate_streams:
            final_permeate_state = cumulative_permeate_state_current
            if final_permeate_state is None:
                final_permeate_state = mix_carbonate_streams(carbonate_permeate_streams,temperature_c)
            carbon_split={'feed':carbonate_feed_state,'concentrate':carbonate_state_current,
                          'permeate':final_permeate_state}
            feed_comp_norm=normalize_composition(carbon_split['feed']['composition'])
            perm_comp=normalize_composition(carbon_split['permeate']['composition'])
            conc_comp=normalize_composition(carbon_split['concentrate']['composition'])
        else:
            # Fast inverse-solver path: retain the resolved feed state while
            # avoiding repeated TA/CT pH root-solves at every trial pressure.
            # Final converged calculations always run with this flag enabled.
            carbon_split={'feed':carbonate_feed_state,'concentrate':carbonate_feed_state,
                          'permeate':carbonate_feed_state}
        avg_comp={k:0.5*(feed_comp_norm[k]+conc_comp[k]) for k in SPECIES}
        feed_osm=osm_state_comp(feed_comp_norm); conc_osm=osm_state_comp(conc_comp)
        avg_osm=osm_state_comp(avg_comp); perm_osm=osm_state_comp(perm_comp)
        cp_stage=total_tds_mg_l(perm_comp); cin=total_tds_mg_l(conc_comp)
        osm_method=feed_osm["method"]
        osm_backend=feed_osm["backend"]
        charge= {"feed_charge_imbalance_pct": feed_osm.get("imbalance_pct",0.0),
                 "concentrate_charge_imbalance_pct":conc_osm.get("imbalance_pct",0.0)}
    else:
        feed_comp_norm=conc_comp=perm_comp=None
        feed_osm=osm_state_tds(feed_tds_ppm); conc_osm=osm_state_tds(cin)
        avg_osm=osm_state_tds(0.5*(feed_tds_ppm+cin)); perm_osm=osm_state_tds(cp_stage)
        osm_method="phi(T,I) interpolation + NaCl-equivalent van't Hoff"
        osm_backend="internal NaCl-equivalent"
        charge={}

    tail_element_chemistry = None
    if full and element_results:
        tail = element_results[-1]
        def _chem_stream(label, comp, ph=None, alk=None, flow=None):
            if not comp:
                return None
            cc=normalize_composition(comp)
            return {"label":label,"composition_mg_l":cc,"tds_mg_l":total_tds_mg_l(cc),
                    "ph":ph,"alkalinity_mg_l_as_hco3":alk,"flow_m3h":flow,"temperature_c":float(temperature_c)}
        tail_element_chemistry = {
            "stage_feed": _chem_stream("Adjusted system/stage feed", feed_comp_norm, carbon_split["feed"].get("ph") if resolve_carbonate_streams else feed_ph, carbon_split["feed"].get("total_alkalinity_mg_l_as_hco3") if resolve_carbonate_streams else None, float(q_feed_m3h)/float(vessels)),
            "tail_feed": _chem_stream("Feed to tail element", tail.get("feed_composition_mg_l"), tail.get("feed_ph"), tail.get("feed_alkalinity_mg_l_as_hco3"), tail.get("feed_flow_m3h")),
            "tail_concentrate": _chem_stream("Tail-element concentrate", tail.get("reject_composition_mg_l"), tail.get("reject_ph"), tail.get("reject_alkalinity_mg_l_as_hco3"), tail.get("reject_flow_m3h")),
            "cumulative_permeate_in": _chem_stream("Cumulative permeate entering tail element tube", tail.get("cumulative_permeate_in_composition_mg_l"), tail.get("cumulative_permeate_in_ph"), tail.get("cumulative_permeate_in_alkalinity_mg_l_as_hco3"), tail.get("cumulative_permeate_in_flow_m3h")),
            "tail_local_permeate": _chem_stream("Local tail-element permeate", tail.get("permeate_composition_mg_l"), tail.get("permeate_ph"), tail.get("permeate_alkalinity_mg_l_as_hco3"), tail.get("permeate_flow_m3h")),
            "cumulative_permeate_out": _chem_stream("Cumulative permeate leaving tail element tube", tail.get("cumulative_permeate_out_composition_mg_l"), tail.get("cumulative_permeate_out_ph"), tail.get("cumulative_permeate_out_alkalinity_mg_l_as_hco3"), tail.get("cumulative_permeate_out_flow_m3h")),
            "tail_element": int(tail.get("element", n)),
            "tail_membrane_id": tail.get("membrane_id"),
            "tail_membrane_model": tail.get("membrane_model"),
        }

    stage_membrane_id = recipe[0] if uniform_recipe else "hybrid"
    stage_membrane_manufacturer = stage_primary.get("manufacturer","") if uniform_recipe else "Hybrid"
    stage_membrane_model = stage_primary.get("model","") if uniform_recipe else _recipe_summary(recipe)

    return {
        "membrane_id":stage_membrane_id,"membrane_manufacturer":stage_membrane_manufacturer,"membrane_model":stage_membrane_model,
        "membrane_family":stage_primary.get("family","") if uniform_recipe else "Hybrid vessel recipe","membrane_max_operating_pressure_bar":max_pressure_bar,
        "membrane_transport_note":stage_primary.get("transport_note","") if uniform_recipe else "Element-position-specific hybrid membrane recipe",
        "membrane_area_each_m2":area_sum/n,"membrane_recipe":recipe,"membrane_recipe_summary":_recipe_summary(recipe),"hybrid_membrane_design":not uniform_recipe,
        "membrane_elements":float(vessels)*n,"pressure_vessels":float(vessels),"elements_per_vessel":n,
        "membrane_total_area_m2":area_total,"stage_dp_bar":stage_dp,"dp_per_element_bar":avg_dp,
        "a_datasheet_lmh_bar":a_datasheet_lmh_bar,"b_datasheet_lmh":b_datasheet_lmh,
        "transport_reference_temperature_c":temp_transport["reference_temperature_c"],
        "water_temp_coefficient_k":temp_transport["water_temp_coefficient_k"],
        "salt_temp_coefficient_k":temp_transport["salt_temp_coefficient_k"],
        "water_temperature_factor":temp_transport["water_temperature_factor"],
        "salt_temperature_factor":temp_transport["salt_temperature_factor"],
        "temperature_transport_basis":temp_transport["temperature_transport_basis"],
        "max_actual_dp_per_element_bar":max_actual,"datasheet_max_dp_per_element_bar":datasheet_max_dp_per_element_bar,
        "datasheet_max_stage_dp_bar":datasheet_max_stage_dp_bar,"dp_limit_fraction":dp_limit_fraction,
        "vessel_feed_flow_m3h":float(q_feed_m3h)/float(vessels),"vessel_reject_flow_m3h":qin,
        "a_app_lmh_bar":a_lmh_bar,"a_clean_lmh_bar":a_clean_lmh_bar,"b_app_lmh":b_lmh,"b_clean_lmh":b_clean_lmh,
        "fouling_factor":fouling_factor,"salt_passage_factor":salt_passage_factor,"datasheet_salt_rejection":r_test,
        "datasheet_salt_passage":1-r_test,
        "observed_salt_rejection_pct":100.0*(1.0-cp_stage/max(float(feed_tds_ppm),1e-12)),
        "observed_salt_passage_pct":100.0*cp_stage/max(float(feed_tds_ppm),1e-12),
        "permeate_flow":qp_total,"reject_flow":qc_total,"recovery":recovery,
        "flux_lmh":avg_flux,"avg_polarization_factor":avg_polarization_factor,
        "avg_polarization_factor_monovalent":avg_polarization_factor,
        "avg_polarization_factor_divalent":avg_polarization_factor_divalent,
        "feed_tds_ppm":float(feed_tds_ppm),
        "permeate_tds_ppm":cp_stage,"concentrate_tds_ppm":cin,"feed_osmotic_bar":feed_osm["osmotic_bar"],
        "concentrate_osmotic_bar":conc_osm["osmotic_bar"],"avg_osmotic_bar":avg_osm["osmotic_bar"],
        "permeate_osmotic_bar":perm_osm["osmotic_bar"],"feed_osmotic_coefficient":feed_osm["phi"],
        "concentrate_osmotic_coefficient":conc_osm["phi"],"avg_osmotic_coefficient":avg_osm["phi"],
        "feed_ionic_strength":feed_osm["ionic_strength"],"concentrate_ionic_strength":conc_osm["ionic_strength"],
        "temperature_c":float(temperature_c),"avg_hydraulic_pressure_bar":0.5*(float(p_feed_bar)+pin),
        "ndp_bar":sum(e["ndp_bar"] for e in element_results)/n,"iterations":len(element_results),
        "reject_pressure_bar":pin,"element_results":element_results,
        "pressure_drop_method":("DuPont FilmTec Eq.67 element-by-element" if float(m.get("diameter_in",8.0))>=7.0 else "FilmTec Eq.67 with equal-superficial-velocity diameter scaling (engineering approximation)"),
        "transport_method":("Species-selective NF: charge-balanced valence-pair solution-diffusion calibrated to manufacturer NaCl/CaCl2/MgSO4 benchmarks + Jin/Jawor/Kim/Hoek temperature correction" if nf_elements else "Solution-diffusion calibrated to datasheet test + Jin/Jawor/Kim/Hoek 2009 Eq. 16a/16b temperature correction"),
        "osmotic_method":osm_method,"osmotic_backend":osm_backend,"water_mode":water_mode,
        "feed_composition_mg_l":feed_comp_norm,"concentrate_composition_mg_l":conc_comp,"permeate_composition_mg_l":perm_comp,
        **({"feed_ph":carbon_split["feed"]["ph"],"concentrate_ph":carbon_split["concentrate"]["ph"],"permeate_ph":carbon_split["permeate"]["ph"],
            "feed_total_alkalinity_mol_kg":carbon_split["feed"]["total_alkalinity_mol_kg"],"concentrate_total_alkalinity_mol_kg":carbon_split["concentrate"]["total_alkalinity_mol_kg"],"permeate_total_alkalinity_mol_kg":carbon_split["permeate"]["total_alkalinity_mol_kg"],
            "feed_total_inorganic_carbon_mol_kg":carbon_split["feed"]["total_inorganic_carbon_mol_kg"],"concentrate_total_inorganic_carbon_mol_kg":carbon_split["concentrate"]["total_inorganic_carbon_mol_kg"],"permeate_total_inorganic_carbon_mol_kg":carbon_split["permeate"]["total_inorganic_carbon_mol_kg"],
            "feed_alkalinity_mg_l_as_hco3":carbon_split["feed"]["total_alkalinity_mg_l_as_hco3"],"concentrate_alkalinity_mg_l_as_hco3":carbon_split["concentrate"]["total_alkalinity_mg_l_as_hco3"],"permeate_alkalinity_mg_l_as_hco3":carbon_split["permeate"]["total_alkalinity_mg_l_as_hco3"]} if (full and resolve_carbonate_streams) else {}),
        "tail_element_chemistry":tail_element_chemistry,
        **nf_summary,
        "osmotic_warning":feed_osm.get("warning",""), **charge,
    }

def turbine_cv(q_m3h, dp_bar, sg=1.025, cvc=None, aux_range=0.85, max_eff_loss=0.03, precomputed_cv_required=None):
    if q_m3h <= 0:
        raise ValueError("Turbine flow must be greater than zero for Cv calculation.")
    if dp_bar <= 0:
        raise ValueError("Turbine ΔP must be greater than zero for Cv calculation.")
    if sg <= 0:
        raise ValueError("Specific gravity must be greater than zero.")
    if not (0 < aux_range <= 1):
        raise ValueError("Auxiliary range must be greater than 0 and no greater than 1.0.")
    if not (0 <= max_eff_loss < 1):
        raise ValueError("Maximum efficiency loss must be between 0 and 1.")

    q_gpm = flow_from_m3h(q_m3h, "gpm")
    dp_psi = dp_bar * PSI_PER_BAR
    cv_required = float(precomputed_cv_required) if precomputed_cv_required is not None else q_gpm * math.sqrt(sg / dp_psi)
    auto_design = cvc is None or cvc <= 0
    cvc = cv_required if auto_design else float(cvc)
    cvo = cvc / math.sqrt(aux_range)

    q_cvc_m3h = flow_to_m3h(cvc * math.sqrt(dp_psi / sg), "gpm")
    q_cvo_m3h = flow_to_m3h(cvo * math.sqrt(dp_psi / sg), "gpm")
    dp_at_cvc_bar = (sg * (q_gpm / cvc) ** 2) * BAR_PER_PSI
    dp_at_cvo_bar = (sg * (q_gpm / cvo) ** 2) * BAR_PER_PSI

    bypass_flow = pressure_increase = backpressure_required = flow_increase = 0.0
    if cv_required < cvc - 1e-9:
        aux_opening = 0.0
        status = "below_cvc"
        duty_status = "backpressure_required"
        backpressure_required = max(0.0, dp_bar - dp_at_cvc_bar)
        flow_increase = max(0.0, q_cvc_m3h - q_m3h)
        message = "Required Cv is below Cvc; at this flow and turbine ΔP the closed auxiliary condition is still too open."
    elif cv_required <= cvo + 1e-9:
        span = cvo - cvc
        aux_opening = 0.0 if span <= 0 else min(1.0, max(0.0, (cv_required - cvc) / span))
        status = duty_status = "in_range"
        message = "Required Cv is within the turbine auxiliary operating range."
    else:
        aux_opening = 1.0
        status = "above_cvo"
        duty_status = "bypass_required"
        bypass_flow = max(0.0, q_m3h - q_cvo_m3h)
        pressure_increase = max(0.0, dp_at_cvo_bar - dp_bar)
        message = "Required Cv exceeds Cvo; the turbine cannot pass the full concentrate flow at the available turbine ΔP."

    eff_loss = max_eff_loss * aux_opening
    effective_cv = cvc + aux_opening * (cvo - cvc)
    aux_cv_effective = max(0.0, effective_cv - cvc)
    aux_flow_fraction = 0.0 if effective_cv <= 0 else aux_cv_effective / effective_cv

    return {
        "sg": sg,
        "cv_required": cv_required, "kv_required": cv_required * KV_PER_CV,
        "cvc": cvc, "kvc": cvc * KV_PER_CV, "cvo": cvo, "kvo": cvo * KV_PER_CV,
        "aux_range": aux_range, "aux_opening": aux_opening,
        "aux_flow_fraction_est": aux_flow_fraction,
        "efficiency_loss": eff_loss, "efficiency_factor": 1.0 - eff_loss,
        "cv_status": status, "duty_status": duty_status, "cv_message": message,
        "cvc_auto_design": auto_design,
        "flow_at_cvc_current_dp": q_cvc_m3h, "flow_at_cvo_current_dp": q_cvo_m3h,
        "required_dp_at_cvc": dp_at_cvc_bar, "required_dp_at_cvo": dp_at_cvo_bar,
        "bypass_flow_required": bypass_flow,
        "pressure_increase_to_avoid_bypass": pressure_increase,
        "flow_reduction_to_avoid_bypass": bypass_flow,
        "backpressure_required": backpressure_required,
        "pressure_reduction_to_avoid_backpressure": backpressure_required,
        "flow_increase_to_avoid_backpressure": flow_increase,
    }


def common(data):
    fu, pu = data.get("flow_unit", "m3/h"), data.get("pressure_unit", "bar")
    getf = lambda k: flow_to_m3h(data[k], fu)
    getp = lambda k: pressure_to_bar(data[k], pu)
    return fu, pu, getf, getp


def display(result, fu, pu):
    # Keep unit conversion generic so the RO Plant Designer can add Stage 3+
    # without another hard-coded conversion list. Composition and element-profile
    # dictionaries intentionally remain on the internal bar / m3/h basis.
    flow_keys = {k for k in result if (k.endswith("_flow") or ("_flow_" in k and k.rsplit("_",1)[-1].isdigit()) or "flow_at_" in k or "bypass_flow" in k or "flow_reduction" in k or "flow_increase" in k)}
    flow_keys |= {"feed_flow", "product_flow", "plus1_product_flow", "minus1_product_flow",
                  "plus1_reject_flow", "minus1_reject_flow", "px_unit_flow", "px_min_unit_flow",
                  "px_max_unit_flow", "px_lubrication_flow", "px_lp_flow", "hpp_flow", "circ_flow"}
    pressure_keys = {k for k in result if (k.endswith("_dp") or k.endswith("_pressure") or ("_pressure_" in k and k.rsplit("_",1)[-1].isdigit()) or "boost" in k or
                     "backpressure" in k or "required_dp" in k or "pressure_increase" in k or
                     "pressure_reduction" in k or "dp_per_element" in k or "max_stage_dp" in k or
                     k.endswith("_ndp") or k.endswith("_feed_osmotic") or k.endswith("_concentrate_osmotic") or
                     k.endswith("_permeate_osmotic") or k.endswith("_avg_osmotic") or
                     "datasheet_max_dp_per_element" in k or "max_actual_dp_per_element" in k)}
    pressure_keys |= {"pex", "turbo_pfin", "feed_turbo_pfin", "inter_turbo_pfin",
                      "px_hp_dp", "px_lp_dp", "px_hp_in_pressure", "px_hp_out_pressure",
                      "px_lp_in_pressure", "px_lp_out_pressure", "hpp_dp", "circ_dp"}
    out = dict(result)
    for k in flow_keys & out.keys():
        if isinstance(out[k], (int, float)):
            out[k] = flow_from_m3h(out[k], fu)
    for k in pressure_keys & out.keys():
        if isinstance(out[k], (int, float)):
            out[k] = pressure_from_bar(out[k], pu)
    out["flow_unit"], out["pressure_unit"] = fu, pu
    return out


def _cv_inputs(data, prefix="", default_sg=None):
    key = lambda name: f"{prefix}{name}" if prefix else name
    sg_input = _float(data, key("sg"), None)
    auto_sg = _bool(data, key("sg_auto"), sg_input is None)
    sg = float(default_sg) if auto_sg and default_sg is not None else (sg_input if sg_input is not None else 1.025)
    return {
        "sg": sg,
        "cvc": _float(data, key("cvc"), None),
        "aux_range": _float(data, key("aux_range"), 0.85),
        "max_eff_loss": _float(data, key("max_eff_loss"), 0.03),
    }


def _attach_cv(result, cv, prefix=""):
    for k, v in cv.items():
        result[f"{prefix}{k}" if prefix else k] = v


def _attach_membrane(result, stage, prefix):
    mapping = {
        "membrane_manufacturer": "membrane_manufacturer", "membrane_model": "membrane_model",
        "membrane_total_area_m2": "membrane_total_area_m2", "a_app_lmh_bar": "a_app_lmh_bar", "a_clean_lmh_bar": "a_clean_lmh_bar", "b_app_lmh": "b_app_lmh", "b_clean_lmh": "b_clean_lmh",
        "a_datasheet_lmh_bar": "a_datasheet_lmh_bar", "b_datasheet_lmh": "b_datasheet_lmh",
        "transport_reference_temperature_c": "transport_reference_temperature_c",
        "water_temp_coefficient_k": "water_temp_coefficient_k", "salt_temp_coefficient_k": "salt_temp_coefficient_k",
        "water_temperature_factor": "water_temperature_factor", "salt_temperature_factor": "salt_temperature_factor",
        "temperature_transport_basis": "temperature_transport_basis",
        "fouling_factor": "fouling_factor", "salt_passage_factor": "salt_passage_factor",
        "pressure_vessels": "pressure_vessels", "elements_per_vessel": "elements_per_vessel",
        "membrane_elements": "total_elements", "stage_dp_bar": "stage_dp", "dp_per_element_bar": "dp_per_element", "max_actual_dp_per_element_bar": "max_actual_dp_per_element",
        "datasheet_max_dp_per_element_bar": "datasheet_max_dp_per_element",
        "datasheet_max_stage_dp_bar": "datasheet_max_stage_dp", "dp_limit_fraction": "dp_limit_fraction",
        "vessel_feed_flow_m3h": "vessel_feed_flow", "vessel_reject_flow_m3h": "vessel_reject_flow",
        "datasheet_salt_rejection": "salt_rejection", "datasheet_salt_passage": "salt_passage",
        "observed_salt_rejection_pct": "observed_salt_rejection_pct", "observed_salt_passage_pct": "observed_salt_passage_pct",
        "permeate_flow": "permeate_flow", "reject_flow": "reject_flow_calc", "recovery": "recovery_calc",
        "flux_lmh": "flux_lmh", "avg_polarization_factor": "polarization_factor",
        "avg_polarization_factor_monovalent": "polarization_factor_monovalent",
        "avg_polarization_factor_divalent": "polarization_factor_divalent",
        "feed_tds_ppm": "feed_tds_ppm", "permeate_tds_ppm": "permeate_tds_ppm",
        "concentrate_tds_ppm": "concentrate_tds_ppm", "feed_osmotic_bar": "feed_osmotic",
        "concentrate_osmotic_bar": "concentrate_osmotic", "ndp_bar": "ndp", "iterations": "membrane_iterations",
        "feed_osmotic_coefficient": "feed_osmotic_coefficient", "concentrate_osmotic_coefficient": "concentrate_osmotic_coefficient",
        "feed_ionic_strength": "feed_ionic_strength", "concentrate_ionic_strength": "concentrate_ionic_strength",
        "temperature_c": "temperature_c", "osmotic_method": "osmotic_method", "osmotic_backend": "osmotic_backend",
        "water_mode": "water_mode", "reported_tds_ppm": "reported_tds_ppm", "reported_vs_species_tds_pct": "reported_vs_species_tds_pct", "feed_charge_imbalance_pct": "feed_charge_imbalance_pct",
        "concentrate_charge_imbalance_pct": "concentrate_charge_imbalance_pct", "osmotic_warning": "osmotic_warning",
        "nf_transport_model":"nf_transport_model", "nf_avg_rejection_mono_mono_pct":"nf_rejection_mono_mono_pct",
        "nf_avg_rejection_mixed_valence_pct":"nf_rejection_mixed_valence_pct",
        "nf_avg_rejection_divalent_divalent_pct":"nf_rejection_divalent_divalent_pct",
        "feed_composition_mg_l": "feed_composition_mg_l", "concentrate_composition_mg_l": "concentrate_composition_mg_l",
        "permeate_composition_mg_l": "permeate_composition_mg_l",
        "membrane_recipe":"membrane_recipe", "membrane_recipe_summary":"membrane_recipe_summary", "hybrid_membrane_design":"hybrid_membrane_design",
        "tail_element_chemistry":"tail_element_chemistry",
        "feed_ph":"feed_ph", "concentrate_ph":"concentrate_ph", "permeate_ph":"permeate_ph",
        "feed_total_alkalinity_mol_kg":"feed_total_alkalinity_mol_kg", "concentrate_total_alkalinity_mol_kg":"concentrate_total_alkalinity_mol_kg", "permeate_total_alkalinity_mol_kg":"permeate_total_alkalinity_mol_kg",
        "feed_total_inorganic_carbon_mol_kg":"feed_total_inorganic_carbon_mol_kg", "concentrate_total_inorganic_carbon_mol_kg":"concentrate_total_inorganic_carbon_mol_kg", "permeate_total_inorganic_carbon_mol_kg":"permeate_total_inorganic_carbon_mol_kg",
        "feed_alkalinity_mg_l_as_hco3":"feed_alkalinity_mg_l_as_hco3", "concentrate_alkalinity_mg_l_as_hco3":"concentrate_alkalinity_mg_l_as_hco3", "permeate_alkalinity_mg_l_as_hco3":"permeate_alkalinity_mg_l_as_hco3",
    }
    for src, dst in mapping.items():
        if src in stage:
            result[f"{prefix}{dst}"] = stage[src]

    # Preserve the representative pressure-vessel element profile for plotting.
    # Parallel vessels in a stage are hydraulically identical in this model, so
    # membrane position is the element position in series (1..8), not total
    # plant element count. Multi-stage reports concatenate these positions.
    result[f"{prefix}element_profile"] = [
        {
            "element": int(e["element"]),
            "flux_lmh": float(e["flux_lmh"]),
            "feed_flow_m3h": float(e.get("feed_flow_m3h", 0.0)),
            "permeate_flow_m3h": float(e.get("permeate_flow_m3h", 0.0)),
            "reject_flow_m3h": float(e.get("reject_flow_m3h", 0.0)),
            "permeate_tds_ppm": float(e.get("permeate_tds_ppm", 0.0)),
            "recovery": float(e.get("recovery", 0.0)),
            "ndp_bar": float(e.get("ndp_bar", 0.0)),
            "dp_bar": float(e.get("dp_bar", 0.0)),
            "polarization_factor": float(e["polarization_factor"]),
            "polarization_factor_monovalent": float(e.get("polarization_factor_monovalent", e["polarization_factor"])),
            "polarization_factor_divalent": float(e.get("polarization_factor_divalent", e["polarization_factor"])),
            "nf_rejection_mono_mono_pct": (100.0*float(e["nf_rejection_mono_mono"]) if e.get("nf_rejection_mono_mono") is not None else None),
            "nf_rejection_mixed_valence_pct": (100.0*float(e["nf_rejection_mixed_valence"]) if e.get("nf_rejection_mixed_valence") is not None else None),
            "nf_rejection_divalent_divalent_pct": (100.0*float(e["nf_rejection_divalent_divalent"]) if e.get("nf_rejection_divalent_divalent") is not None else None),
            "feed_pressure_bar": float(e["feed_pressure_bar"]),
            "reject_pressure_bar": float(e["reject_pressure_bar"]),
            "feed_tds_ppm": float(e["feed_tds_ppm"]),
            "reject_tds_ppm": float(e["reject_tds_ppm"]),
            "feed_osmotic_bar": float(e.get("feed_osmotic_bar", 0.0)),
            "membrane_surface_osmotic_bar": float(e.get("membrane_surface_osmotic_bar", 0.0)),
            "membrane_id": e.get("membrane_id"), "membrane_model": e.get("membrane_model"),
            "membrane_manufacturer": e.get("membrane_manufacturer"),
            "feed_composition_mg_l": e.get("feed_composition_mg_l"),
            "permeate_composition_mg_l": e.get("permeate_composition_mg_l"),
            "reject_composition_mg_l": e.get("reject_composition_mg_l"),
            "feed_ph": e.get("feed_ph"), "permeate_ph": e.get("permeate_ph"), "reject_ph": e.get("reject_ph"),
            "feed_alkalinity_mg_l_as_hco3": e.get("feed_alkalinity_mg_l_as_hco3"),
            "permeate_alkalinity_mg_l_as_hco3": e.get("permeate_alkalinity_mg_l_as_hco3"),
            "reject_alkalinity_mg_l_as_hco3": e.get("reject_alkalinity_mg_l_as_hco3"),
            "cumulative_permeate_in_flow_m3h": e.get("cumulative_permeate_in_flow_m3h"),
            "cumulative_permeate_in_composition_mg_l": e.get("cumulative_permeate_in_composition_mg_l"),
            "cumulative_permeate_in_ph": e.get("cumulative_permeate_in_ph"),
            "cumulative_permeate_in_alkalinity_mg_l_as_hco3": e.get("cumulative_permeate_in_alkalinity_mg_l_as_hco3"),
            "cumulative_permeate_out_flow_m3h": e.get("cumulative_permeate_out_flow_m3h"),
            "cumulative_permeate_out_composition_mg_l": e.get("cumulative_permeate_out_composition_mg_l"),
            "cumulative_permeate_out_ph": e.get("cumulative_permeate_out_ph"),
            "cumulative_permeate_out_alkalinity_mg_l_as_hco3": e.get("cumulative_permeate_out_alkalinity_mg_l_as_hco3"),
        }
        for e in stage.get("element_results", [])
    ]



def _attach_composite_permeate_carbon(result, s1, s2):
    if not (s1 and s2 and s1.get('permeate_composition_mg_l') and s2.get('permeate_composition_mg_l')):
        return
    try:
        temp=float(s1.get('temperature_c',25.0))
        mixed=mix_carbonate_streams([
            {'flow':s1.get('permeate_flow',0),'composition':s1['permeate_composition_mg_l'],'state':{'total_alkalinity_mol_kg':s1['permeate_total_alkalinity_mol_kg'],'total_inorganic_carbon_mol_kg':s1['permeate_total_inorganic_carbon_mol_kg']}},
            {'flow':s2.get('permeate_flow',0),'composition':s2['permeate_composition_mg_l'],'state':{'total_alkalinity_mol_kg':s2['permeate_total_alkalinity_mol_kg'],'total_inorganic_carbon_mol_kg':s2['permeate_total_inorganic_carbon_mol_kg']}},
        ],temp)
        result['composite_permeate_ph']=mixed['ph']
        result['composite_permeate_alkalinity_mg_l_as_hco3']=mixed['total_alkalinity_mg_l_as_hco3']
        result['composite_permeate_total_alkalinity_mol_kg']=mixed['total_alkalinity_mol_kg']
        result['composite_permeate_total_inorganic_carbon_mol_kg']=mixed['total_inorganic_carbon_mol_kg']
        result['composite_permeate_composition_mg_l']=mixed['composition']
    except (KeyError,ValueError,ZeroDivisionError):
        pass


def _stage_from_data(data, stage_no, q_feed, p_feed, feed_tds, feed_composition=None, feed_carbonate_state=None):
    recipe = data.get(f"membrane_recipe_{stage_no}")
    mid = data.get(f"membrane_{stage_no}")
    if (not mid) and isinstance(recipe,(list,tuple)) and recipe:
        mid = recipe[0]
    vessels = _float(data, f"vessels_{stage_no}", None)
    elements_per_vessel = _float(data, f"elements_per_vessel_{stage_no}", None)
    if (vessels is None or elements_per_vessel is None) and _float(data, f"elements_{stage_no}", None):
        vessels = _float(data, f"elements_{stage_no}")
        elements_per_vessel = 1.0
    pp_raw = _float(data, f"permeate_pressure_{stage_no}", None)
    if pp_raw is None:
        pp_raw = _float(data, "permeate_pressure", 0.0)
    pp = pressure_to_bar(pp_raw, data.get("pressure_unit", "bar"))
    temp_c = _float(data, "temperature_c", 25.0)
    water_mode = str(data.get("water_mode", "tds")).lower()
    ph = _float(data, "feed_ph", 7.6)
    if water_mode == "full" and feed_composition is None:
        feed_composition = composition_from_request(data)
        feed_tds = total_tds_mg_l(feed_composition)
    if water_mode == "full" and stage_no == 1 and feed_carbonate_state is None:
        feed_carbonate_state = data.get("_feed_carbonate_state")
    if not mid or not vessels or not elements_per_vessel:
        raise ValueError(f"Select a membrane, number of vessels and membranes per vessel for stage {stage_no}.")
    stage = membrane_stage(q_feed, p_feed, mid, vessels, elements_per_vessel, feed_tds, pp, temp_c, None,
                           feed_composition=feed_composition, feed_ph=ph, water_mode=water_mode,
                           fouling_factor=_float(data, "fouling_factor", 1.0),
                           salt_passage_factor=_float(data, "salt_passage_factor", 1.0),
                           feed_carbonate_state=feed_carbonate_state,
                           resolve_carbonate_streams=not _bool(data, "_solver_fast", False),
                           membrane_recipe=recipe)
    if water_mode == "full":
        reported = _float(data, "analysis_tds", None)
        if reported is not None:
            stage["reported_tds_ppm"] = reported
            stage["reported_vs_species_tds_pct"] = 100.0*(reported-stage["feed_tds_ppm"])/max(reported,1e-12)
    return stage


def _manual_stage_dp(data, stage_no, q_feed, q_reject):
    vessels = _float(data, f"vessels_{stage_no}", None)
    elements_per_vessel = _float(data, f"elements_per_vessel_{stage_no}", None)
    if not vessels or not elements_per_vessel:
        raise ValueError(f"Pressure vessels and membranes/vessel are required for stage {stage_no} pressure-drop calculation.")
    dp, dps, flows = clean_stage_pressure_drop(q_feed, q_reject, vessels, int(elements_per_vessel))
    mid = data.get(f"membrane_{stage_no}")
    m = get_membrane(mid) if mid else None
    return {"stage_dp_bar": dp, "dp_per_element_bar": dp/int(elements_per_vessel),
            "max_actual_dp_per_element_bar": max(dps), "element_results": flows,
            "pressure_vessels": vessels, "elements_per_vessel": int(elements_per_vessel),
            "membrane_elements": vessels*int(elements_per_vessel),
            "membrane_manufacturer": m["manufacturer"] if m else "",
            "membrane_model": m["model"] if m else "",
            "datasheet_max_dp_per_element_bar": 1.0,
            "datasheet_max_stage_dp_bar": int(elements_per_vessel)*1.0,
            "dp_limit_fraction": max(dps)/1.0,
            "vessel_feed_flow_m3h": q_feed/vessels, "vessel_reject_flow_m3h": q_reject/vessels}

def _single_state(data, pressure_shift_bar=0.0):
    fu, pu, getf, getp = common(data)
    qf = getf("feed_flow")
    pm = getp("membrane_pressure_1") + pressure_shift_bar
    pex = getp("pex")
    coupled = _bool(data, "membrane_coupling", False)
    stage = None
    if coupled:
        stage = _stage_from_data(data, 1, qf, pm, _float(data, "feed_tds", 35000.0))
        qr = stage["reject_flow"]
        pr = stage["reject_pressure_bar"]
    else:
        qr = getf("reject_flow_1")
        hd = _manual_stage_dp(data, 1, qf, qr)
        pr = pm - hd["stage_dp_bar"]
    sg_default = None
    if stage:
        sg_default = solution_specific_gravity(stage.get("concentrate_tds_ppm", _float(data,"feed_tds",35000.0)), stage.get("temperature_c", _float(data,"temperature_c",25.0)))
    cv = turbine_cv(qr, pr - pex, **_cv_inputs(data, default_sg=sg_default))
    return qf, pm, pr, qr, stage, cv


def _single_sensitivity(data, result):
    if not _bool(data, "membrane_coupling", False):
        return
    # Sensitivity is relative to the *converged* duty point.  It only needs
    # flow/Cv outputs, so use the inverse-solver fast chemistry path and avoid
    # repeating expensive carbonate stream reporting for +/-1 bar trials.
    trial_data = dict(data)
    trial_data["_solver_fast"] = True
    pu = data.get("pressure_unit", "bar")
    trial_data["membrane_pressure_1"] = pressure_from_bar(float(result["membrane_pressure_1"]), pu)
    for shift, label in [(BAR_PER_PSI * PSI_PER_BAR, "plus1"), (-BAR_PER_PSI * PSI_PER_BAR, "minus1")]:
        # Above expression intentionally equals +/-1 bar; written explicitly to keep unit basis clear.
        try:
            qf, pm, pr, qr, st, cv = _single_state(trial_data, shift)
            result[f"{label}_product_flow"] = st["permeate_flow"]
            result[f"{label}_reject_flow"] = qr
            result[f"{label}_cv_required"] = cv["cv_required"]
            result[f"{label}_recovery"] = st["recovery"]
        except ValueError:
            pass


def _single_stage_base(data):
    fu, pu, getf, getp = common(data)
    qf, pm, pr, qr, stage, cv = _single_state(data)
    pex, psuc = getp("pex"), getp("suction_pressure")
    pret_p = getp("pretreatment_discharge_pressure")
    peff, meff = float(data["pump_eff"]), float(data["motor_eff"])
    veff = _vfd_eff(data, "vfd_eff", "pump_no_vfd")
    pret_rec = float(data["pretreatment_recovery"])
    pret_peff, pret_meff = float(data.get("pretreatment_pump_eff", data.get("pretreatment_eff", 0.82))), float(data.get("pretreatment_motor_eff", 1.0 if "pretreatment_eff" in data else 0.95))
    pret_veff = (1.0 if "pretreatment_eff" in data and "pretreatment_vfd_eff" not in data else _vfd_eff(data, "pretreatment_vfd_eff", "pretreatment_no_vfd"))

    reject_ratio = _enforce_turbo_reject_ratio(qr, qf, "Single turbocharger")
    eff_state = _turbo_case_efficiency(data, qf, qr, pm, pr)
    base_eff = eff_state["overall_eff"]
    recovery1 = (qf - qr) / qf
    use_workbook = str(data.get("off_design_model","")).lower() in {"spreadsheet","locked","case_locked"}
    eff = base_eff if use_workbook else base_eff * cv["efficiency_factor"]
    turbine_dp = pr - pex
    boost = eff * (1 - recovery1) * turbine_dp
    pump_dp = pm - boost - psuc
    hydraulic_kw = 0.0277 * pump_dp * qf
    electric_kw = hydraulic_kw / peff / meff / veff
    qp = qf - qr
    if qp <= 0:
        raise ValueError("Calculated product flow is zero or negative.")
    sec = electric_kw / qp
    pret_kw = _pump_wire_power_kw(qf / pret_rec, pret_p, pret_peff, pret_meff, pret_veff)
    pret_sec = pret_kw / qp

    result = {
        "membrane_coupling": bool(stage), "base_turbo_eff": base_eff, "turbo_eff": eff,
        "turbine_component_eff": eff_state["turbine_eff"], "pump_component_eff": eff_state["pump_eff"],
        "turbo_efficiency_method": eff_state["method"], "design_overall_eff": eff_state["design_overall_eff"],
        "feed_flow": qf, "membrane_pressure_1": pm, "reject_pressure_1": pr, "pex": pex,
        "reject_flow_1": qr, "turbine_flow": qr, "product_flow": qp,
        "turbo_pump_flow": qf, "turbo_turbine_flow": qr, "turbo_reject_ratio": reject_ratio,
        "turbo_reject_ratio_status": turbo_reject_ratio_status(reject_ratio),
        "recovery": qp / qf, "turbine_dp": turbine_dp, "turbo_boost": boost,
        "turbo_pfin": pm - boost,
        "feed_pump_dp": pump_dp, "hydraulic_kw": hydraulic_kw, "electric_kw": electric_kw,
        "pretreatment_kw": pret_kw, "pump_sec": sec, "ro_sec": sec, "pretreatment_sec": pret_sec,
        "total_sec": sec + pret_sec, "product_m3d": qp * 24,
    }
    _attach_cv(result, cv)
    if stage:
        _attach_membrane(result, stage, "stage1_")
        # Sensitivity is a reporting feature, not part of the inverse root solve.
        # Skip the two extra membrane evaluations during solver trials and run it
        # once on the final converged duty point.
        if not _bool(data, "_solver_fast", False):
            _single_sensitivity(data, result)
    else:
        h = _manual_stage_dp(data, 1, qf, qr)
        for src, dst in [("pressure_vessels","pressure_vessels"),("elements_per_vessel","elements_per_vessel"),("membrane_elements","total_elements"),("stage_dp_bar","stage_dp"),("dp_per_element_bar","dp_per_element"),("max_actual_dp_per_element_bar","max_actual_dp_per_element"),("datasheet_max_dp_per_element_bar","datasheet_max_dp_per_element"),("dp_limit_fraction","dp_limit_fraction"),("vessel_feed_flow_m3h","vessel_feed_flow"),("vessel_reject_flow_m3h","vessel_reject_flow"),("membrane_manufacturer","membrane_manufacturer"),("membrane_model","membrane_model")]:
            result[f"stage1_{dst}"] = h[src]
    return display(result, fu, pu)



def _interstage_membrane_trial(data, qr1, feed_tds, feed_comp, pex, p2, pp_bar, maxp, feed_carbonate_state=None):
    """Return the membrane-only state for one independent Stage-2 pressure trial.

    This function is intentionally top-level/picklable so the direct interstage
    pressure search can distribute trial pressures across Windows worker
    processes. Turbo/Cv arithmetic is applied in the parent process so the
    locked design-duty equations remain identical to the reference path.
    """
    p2 = float(p2)
    if p2 <= float(pp_bar) + 0.2 or p2 > float(maxp):
        return None
    s2 = _stage_from_data(data, 2, float(qr1), p2, float(feed_tds), feed_comp, feed_carbonate_state)
    qr2, pr2 = s2["reject_flow"], s2["reject_pressure_bar"]
    rec2 = (float(qr1) - qr2) / max(float(qr1), 1e-12)
    tdp = pr2 - float(pex)
    if tdp <= 0:
        return None
    sg_default = solution_specific_gravity(
        s2.get("concentrate_tds_ppm", feed_tds),
        s2.get("temperature_c", _float(data, "temperature_c", 25.0)),
    )
    return {"p2": p2, "s2": s2, "qr2": qr2, "pr2": pr2, "rec2": rec2,
            "turbine_dp": tdp, "sg_default": sg_default}


def _solve_interstage_stage2(data, qf1, pr1, qr1, feed_tds, feed_comp, pex, feed_carbonate_state=None):
    """Solve Stage-2 feed pressure from the coupled interstage-turbo balance.

    Fast path: local smart bracketing around the current Stage-2 pressure, then
    a safeguarded secant iteration.  If a local bracket is not found, a broad
    conservative scan is used automatically.  The physical residual remains
        P2 - (Pr1 + Boost(P2)) = 0
    so the optimization changes only the numerical search, not the model.
    """
    # Efficiency is evaluated inside each Stage-2 trial because a locked design
    # duty depends on pump/turbine flow and pressure at that trial point.
    pu = data.get("pressure_unit", "bar")
    pp_user = _float(data, "permeate_pressure_1", None)
    if pp_user is None:
        pp_user = _float(data, "permeate_pressure_1", None)
    if pp_user is None:
        pp_user = _float(data, "permeate_pressure", 0.0)
    if pp_user is None:
        pp_user = 0.0
    pp_bar = pressure_to_bar(pp_user, pu)
    try:
        m2 = get_membrane(str(data.get("membrane_2", "")))
        maxp = float(m2.get("max_operating_pressure_bar", 120.0))
    except Exception:
        maxp = 120.0

    lo = max(pr1 + 0.05, pp_bar + 0.5)
    hi = maxp
    guess_user = _float(data, "membrane_pressure_2", None)
    if guess_user is None:
        guess_user = pressure_from_bar(min(lo+10, hi), pu)
    guess = pressure_to_bar(guess_user, pu)
    guess = min(max(guess, lo), hi)
    cache = {}
    eval_count = 0
    pressure_search_backend = "cpu-main"
    allow_cpu_pool = not _nested_cpu_disabled(data)
    allow_gpu = not _gpu_disabled(data)
    search_backend = "cpu-main"
    search_workers = 1
    gpu_backend = "not-used"
    gpu_device = None
    monitor_phase_marked = False

    def enrich_trial(trial, precomputed_cv=None):
        if trial is None:
            return None
        p2=trial["p2"]; s2=trial["s2"]; qr2=trial["qr2"]; pr2=trial["pr2"]
        rec2=trial["rec2"]; tdp=trial["turbine_dp"]; sg_default=trial["sg_default"]
        cv_inputs=_cv_inputs(data, default_sg=sg_default)
        if precomputed_cv is not None:
            cv_inputs["precomputed_cv_required"]=precomputed_cv
        cv=turbine_cv(qr2,tdp,**cv_inputs)
        eff_state=_turbo_case_efficiency(data,qr1,qr2,p2,pr2)
        base_eff=eff_state["overall_eff"]
        use_workbook=str(data.get("off_design_model","")).lower() in {"spreadsheet","locked","case_locked"}
        eff=base_eff if use_workbook else base_eff*cv["efficiency_factor"]
        boost=eff*(1.0-rec2)*tdp
        target_p2=pr1+boost
        return {"p2":p2,"s2":s2,"qr2":qr2,"pr2":pr2,"rec2":rec2,
                "turbine_dp":tdp,"cv":cv,"eff":eff,"boost":boost,
                "target_p2":target_p2,"residual":p2-target_p2,"base_eff":base_eff,
                "eff_state":eff_state}

    def state(p2):
        nonlocal eval_count
        p2=min(max(float(p2),lo),hi)
        key=round(p2,8)
        if key in cache:
            return cache[key]
        eval_count+=1
        try:
            trial=_interstage_membrane_trial(data,qr1,feed_tds,feed_comp,pex,p2,pp_bar,maxp,feed_carbonate_state)
            out=enrich_trial(trial)
            cache[key]=out
            return out
        except (ValueError,ZeroDivisionError,OverflowError):
            cache[key]=None
            return None

    def batch_states(points):
        """Evaluate Stage-2 candidates with independent CPU/GPU policies.

        Scenario Matrix workers suppress nested CPU pools but can still batch
        the candidate turbo Cv arithmetic on OpenCL.
        """
        nonlocal eval_count,search_backend,search_workers,gpu_backend,gpu_device,monitor_phase_marked
        pts=[]
        for value in points:
            p=min(max(float(value),lo),hi); key=round(p,8)
            if key not in cache and key not in {round(x,8) for x in pts}: pts.append(p)
        if not pts:
            return [cache.get(round(min(max(float(x),lo),hi),8)) for x in points]

        good=[]
        if len(pts) >= 2 and allow_cpu_pool:
            try:
                from compute_engine import parallel_interstage_trials
                payloads=[{"data":dict(data),"qr1":qr1,"feed_tds":feed_tds,"feed_comp":feed_comp,
                           "pex":pex,"p2":p,"pp_bar":pp_bar,"maxp":maxp,"feed_carbonate_state":feed_carbonate_state} for p in pts]
                batch=parallel_interstage_trials(payloads)
                search_backend=batch.get("backend","cpu-main"); search_workers=int(batch.get("workers",1) or 1)
                eval_count+=len(pts)
                for p,row in zip(pts,batch.get("results",[])):
                    trial=row.get("result") if row and row.get("ok") else None
                    if trial is not None: good.append((p,trial))
                    else: cache[round(p,8)]=None
            except Exception:
                search_backend="cpu-main"; search_workers=1
        else:
            search_backend="cpu-worker-sequential" if _nested_cpu_disabled(data) else "cpu-main"
            search_workers=1

        # If the parallel membrane sweep was unavailable/disabled, evaluate only
        # the membrane states here; delay Cv arithmetic so all valid trials can
        # still be vectorized together on CPU/OpenCL below.
        if not good and any(round(p,8) not in cache for p in pts):
            for p in pts:
                key=round(p,8)
                if key in cache: continue
                try:
                    trial=_interstage_membrane_trial(data,qr1,feed_tds,feed_comp,pex,p,pp_bar,maxp,feed_carbonate_state)
                except Exception:
                    trial=None
                eval_count += 1
                if trial is not None: good.append((p,trial))
                else: cache[key]=None

        cv_map={}
        if good:
            try:
                from compute_engine import turbo_metrics_batch, update_compute_run
                metrics=turbo_metrics_batch(
                    [qr1 for _ in good], [x[1]["qr2"] for x in good],
                    [x[1]["turbine_dp"] for x in good], [x[1]["sg_default"] for x in good],
                    preference=("gpu" if allow_gpu and len(good)>=2 else "cpu"),
                )
                gpu_backend=metrics.get("backend","cpu-vector"); gpu_device=metrics.get("device")
                for (p,_),cvv in zip(good,metrics.get("cv",[])): cv_map[round(p,8)]=cvv
                update_compute_run(
                    backend=search_backend+(" + opencl-gpu" if gpu_backend=="opencl-gpu" else " + cpu-vector"),
                    workers=search_workers,
                )
            except Exception:
                gpu_backend="fallback"
        for p,trial in good:
            cache[round(p,8)]=enrich_trial(trial,cv_map.get(round(p,8)))

        if not monitor_phase_marked:
            try:
                from compute_engine import update_compute_run
                update_compute_run(completed_delta=1,backend=search_backend+(" + opencl-gpu" if gpu_backend=="opencl-gpu" else ""),workers=search_workers)
            except Exception:
                pass
            monitor_phase_marked=True
        return [cache.get(round(min(max(float(x),lo),hi),8)) for x in points]

    def finalize_result(out,method,fallback_used,iterations=0):
        out.update(iterations=iterations,evaluations=eval_count,solver_method=method,
                   fallback_used=fallback_used,pressure_search_backend=search_backend,
                   pressure_search_workers=search_workers,gpu_screen_backend=gpu_backend,
                   gpu_screen_device=gpu_device)
        try:
            from compute_engine import update_compute_run
            backend=search_backend+(" + opencl-gpu" if gpu_backend=="opencl-gpu" else "")
            update_compute_run(completed_delta=1,backend=backend,workers=search_workers)
        except Exception:
            pass
        return out

    valid=[]
    step=max(0.5,0.025*max(guess,30.0))
    local_points=[guess]
    for k in range(5):
        span=step*(2**k)
        local_points.extend([guess-span,guess+span])
    local_points=[p for p in local_points if lo-1e-9<=p<=hi+1e-9]
    for x in batch_states(local_points):
        if x is not None: valid.append(x)
    first=cache.get(round(guess,8))
    if first is not None and abs(first["residual"])<=HYDRAULIC_PRESSURE_ABS_TOL_BAR:
        return finalize_result(first,"parallel smart bracket",False,0)

    bracket=None
    uniq=sorted({round(x["p2"],8):x for x in valid}.values(),key=lambda x:x["p2"])
    for a,b in zip(uniq,uniq[1:]):
        if a["residual"]*b["residual"]<=0:
            bracket=(a,b);break

    fallback=False
    if bracket is None:
        fallback=True
        broad_points=[lo+(hi-lo)*i/24.0 for i in range(25)]
        for x in batch_states(broad_points):
            if x is not None: valid.append(x)
        uniq=sorted({round(x["p2"],8):x for x in valid}.values(),key=lambda x:x["p2"])
        for a,b in zip(uniq,uniq[1:]):
            if a["residual"]*b["residual"]<=0:
                bracket=(a,b);break
        if bracket is None:
            if not uniq:
                raise ValueError("No valid Stage 2 pressure range was found for the coupled interstage turbo duty.")
            best=min(uniq,key=lambda x:abs(x["residual"]))
            if abs(best["residual"])<=0.05:
                return finalize_result(best,"parallel conservative close root",True,0)
            if best["residual"]<0 and best["p2"]>=0.98*maxp:
                raise ValueError(
                    f"The natural interstage turbo boost would require about {best['target_p2']:.1f} bar at Stage 2, "
                    f"above the selected membrane pressure limit of {maxp:.1f} bar. Reduce the duty/boost, use boost-control or bypass, "
                    "or select an appropriate UHPRO membrane."
                )
            raise ValueError("Stage 2 pressure could not be balanced with the interstage turbo boost at this duty point.")

    a,b=bracket
    if a["p2"] > b["p2"]:
        a,b=b,a
    final=min((a,b),key=lambda x:abs(x["residual"]))
    iterations=0
    for iterations in range(1,31):
        fa,fb=a["residual"],b["residual"]
        if abs(fa) <= HYDRAULIC_PRESSURE_ABS_TOL_BAR:
            final=a; break
        if abs(fb) <= HYDRAULIC_PRESSURE_ABS_TOL_BAR:
            final=b; break
        width=b["p2"]-a["p2"]
        if width <= HYDRAULIC_PRESSURE_ABS_TOL_BAR:
            final=min((a,b),key=lambda x:abs(x["residual"]))
            break
        if abs(fb-fa) > 1e-14:
            p=b["p2"]-fb*(b["p2"]-a["p2"])/(fb-fa)
        else:
            p=0.5*(a["p2"]+b["p2"])
        guard=0.08*width
        if not (a["p2"]+guard < p < b["p2"]-guard):
            p=0.5*(a["p2"]+b["p2"])
        mid=state(p)
        if mid is None:
            mid=state(0.5*(a["p2"]+b["p2"]))
            if mid is None:
                fallback=True
                continue
        final=mid
        fm=mid["residual"]
        if abs(fm) <= HYDRAULIC_PRESSURE_ABS_TOL_BAR:
            break
        if fa*fm <= 0:
            b=mid
        else:
            a=mid
    return finalize_result(final,"parallel smart bracket + safeguarded secant",fallback,iterations)

def _interstage_base(data):
    fu, pu, getf, getp = common(data)
    qf1 = getf("feed_flow")
    pm1 = getp("membrane_pressure_1")
    coupled = _bool(data, "membrane_coupling", False)
    solve_stage_pressures = coupled and _bool(data, "solve_stage_pressures", False)
    pm2_user = _float(data, "membrane_pressure_2", None)
    pm2 = pressure_to_bar(pm2_user, pu) if pm2_user is not None else None
    if pm2 is None and not solve_stage_pressures:
        raise ValueError("Enter the Stage 2 membrane feed pressure, or select a solve mode that calculates it.")
    pex, psuc, pret_p = getp("pex"), getp("suction_pressure"), getp("pretreatment_discharge_pressure")
    s1 = s2 = None
    if coupled:
        feed_tds = _float(data, "feed_tds", 35000.0)
        s1 = _stage_from_data(data, 1, qf1, pm1, feed_tds)
        qr1, pr1 = s1["reject_flow"], s1["reject_pressure_bar"]
        if solve_stage_pressures:
            st2 = _solve_interstage_stage2(data, qf1, pr1, qr1, s1["concentrate_tds_ppm"], s1.get("concentrate_composition_mg_l"), pex, {"total_alkalinity_mol_kg":s1.get("concentrate_total_alkalinity_mol_kg"),"total_inorganic_carbon_mol_kg":s1.get("concentrate_total_inorganic_carbon_mol_kg")})
            pm2, s2, qr2, pr2 = st2["p2"], st2["s2"], st2["qr2"], st2["pr2"]
        else:
            s2 = _stage_from_data(data, 2, qr1, pm2, s1["concentrate_tds_ppm"], s1.get("concentrate_composition_mg_l"), {"total_alkalinity_mol_kg":s1.get("concentrate_total_alkalinity_mol_kg"),"total_inorganic_carbon_mol_kg":s1.get("concentrate_total_inorganic_carbon_mol_kg")})
            qr2, pr2 = s2["reject_flow"], s2["reject_pressure_bar"]
    else:
        qr1, qr2 = getf("reject_flow_1"), getf("reject_flow_2")
        h1 = _manual_stage_dp(data, 1, qf1, qr1); pr1 = pm1 - h1["stage_dp_bar"]
        h2 = _manual_stage_dp(data, 2, qr1, qr2); pr2 = pm2 - h2["stage_dp_bar"]

    reject_ratio = _enforce_turbo_reject_ratio(qr2, qr1, "Interstage turbocharger")
    peff, meff = float(data["pump_eff"]), float(data["motor_eff"])
    veff = _vfd_eff(data, "vfd_eff", "pump_no_vfd")
    pret_rec = float(data["pretreatment_recovery"])
    pret_peff, pret_meff = float(data.get("pretreatment_pump_eff", data.get("pretreatment_eff", 0.82))), float(data.get("pretreatment_motor_eff", 1.0 if "pretreatment_eff" in data else 0.95))
    pret_veff = (1.0 if "pretreatment_eff" in data and "pretreatment_vfd_eff" not in data else _vfd_eff(data, "pretreatment_vfd_eff", "pretreatment_no_vfd"))
    if solve_stage_pressures:
        base_eff = st2["base_eff"]
        eff_state = st2.get("eff_state") or _turbo_case_efficiency(data, qr1, st2["qr2"], st2["p2"], st2["pr2"])
        rec2, turbine_dp, cv, eff, boost = st2["rec2"], st2["turbine_dp"], st2["cv"], st2["eff"], st2["boost"]
    else:
        rec2 = (qr1 - qr2) / qr1
        turbine_dp = pr2 - pex
        sg_default = None
        if s2:
            sg_default = solution_specific_gravity(s2.get("concentrate_tds_ppm",_float(data,"feed_tds",35000.0)), s2.get("temperature_c",_float(data,"temperature_c",25.0)))
        cv = turbine_cv(qr2, turbine_dp, **_cv_inputs(data, default_sg=sg_default))
        eff_state = _turbo_case_efficiency(data, qr1, qr2, pm2, pr2)
        base_eff = eff_state["overall_eff"]
        use_workbook = str(data.get("off_design_model","")).lower() in {"spreadsheet","locked","case_locked"}
        eff = base_eff if use_workbook else base_eff * cv["efficiency_factor"]
        boost = eff * (1 - rec2) * turbine_dp
    interstage_discharge = pr1 + boost
    pump_dp = pm1 - psuc
    hydraulic_kw = pump_dp * qf1 / 36.0
    electric_kw = hydraulic_kw / peff / meff / veff
    qp = qf1 - qr2
    sec = electric_kw / qp
    pret_kw = _pump_wire_power_kw(qf1 / pret_rec, pret_p, pret_peff, pret_meff, pret_veff)
    pret_sec = pret_kw / qp

    result = {
        "membrane_coupling": coupled, "base_turbo_eff": base_eff, "turbo_eff": eff,
        "turbine_component_eff": eff_state["turbine_eff"], "pump_component_eff": eff_state["pump_eff"],
        "turbo_efficiency_method": eff_state["method"], "design_overall_eff": eff_state["design_overall_eff"],
        "feed_flow": qf1, "membrane_pressure_1": pm1, "reject_pressure_1": pr1,
        "membrane_pressure_2": pm2, "reject_pressure_2": pr2, "pex": pex,
        "reject_flow_1": qr1, "reject_flow_2": qr2, "turbine_flow": qr2,
        "turbo_pump_flow": qr1, "turbo_turbine_flow": qr2, "turbo_reject_ratio": reject_ratio,
        "turbo_reject_ratio_status": turbo_reject_ratio_status(reject_ratio),
        "product_flow": qp, "recovery": qp / qf1, "stage1_recovery": (qf1 - qr1) / qf1,
        "stage2_recovery": rec2, "turbine_dp": turbine_dp, "interstage_boost": boost,
        "turbo_pfin": pr1,
        "interstage_discharge_pressure": interstage_discharge, "feed_pump_dp": pump_dp,
        "stage2_pressure_solved": bool(solve_stage_pressures),
        "stage2_pressure_solve_iterations": (st2.get("iterations",0) if solve_stage_pressures else 0),
        "stage2_pressure_solve_evaluations": (st2.get("evaluations",0) if solve_stage_pressures else 0),
        "stage2_solver_method": (st2.get("solver_method","") if solve_stage_pressures else ""),
        "stage2_solver_fallback_used": (st2.get("fallback_used",False) if solve_stage_pressures else False),
        "stage2_pressure_search_backend": (st2.get("pressure_search_backend","cpu-main") if solve_stage_pressures else "cpu-main"),
        "stage2_pressure_search_workers": (st2.get("pressure_search_workers",1) if solve_stage_pressures else 1),
        "stage2_gpu_screen_backend": (st2.get("gpu_screen_backend","not-used") if solve_stage_pressures else "not-used"),
        "stage2_gpu_screen_device": (st2.get("gpu_screen_device") if solve_stage_pressures else None),
        "hydraulic_kw": hydraulic_kw, "electric_kw": electric_kw, "pretreatment_kw": pret_kw,
        "pump_sec": sec, "ro_sec": sec, "pretreatment_sec": pret_sec, "total_sec": sec + pret_sec,
        "product_m3d": qp * 24,
    }
    _attach_cv(result, cv)
    if coupled:
        _attach_membrane(result, s1, "stage1_")
        _attach_membrane(result, s2, "stage2_")
        _attach_composite_permeate_carbon(result, s1, s2)
    else:
        for no, h in [(1,h1),(2,h2)]:
            for src, dst in [("pressure_vessels","pressure_vessels"),("elements_per_vessel","elements_per_vessel"),("membrane_elements","total_elements"),("stage_dp_bar","stage_dp"),("dp_per_element_bar","dp_per_element"),("max_actual_dp_per_element_bar","max_actual_dp_per_element"),("datasheet_max_dp_per_element_bar","datasheet_max_dp_per_element"),("dp_limit_fraction","dp_limit_fraction"),("vessel_feed_flow_m3h","vessel_feed_flow"),("vessel_reject_flow_m3h","vessel_reject_flow"),("membrane_manufacturer","membrane_manufacturer"),("membrane_model","membrane_model")]:
                result[f"stage{no}_{dst}"] = h[src]
    return display(result, fu, pu)


def _biturbo_base(data):
    fu, pu, getf, getp = common(data)
    qf1 = getf("feed_flow")
    pm1 = getp("membrane_pressure_1")
    coupled = _bool(data, "membrane_coupling", False)
    solve_stage_pressures = coupled and _bool(data, "solve_stage_pressures", False)
    pm2_user = _float(data, "membrane_pressure_2", None)
    pm2 = pressure_to_bar(pm2_user, pu) if pm2_user is not None else None
    if pm2 is None and not solve_stage_pressures:
        raise ValueError("Enter the Stage 2 membrane feed pressure, or select a solve mode that calculates it.")
    target = getp("target_interstage_boost")
    pex, psuc, pret_p = getp("pex"), getp("suction_pressure"), getp("pretreatment_discharge_pressure")
    s1 = s2 = None
    if coupled:
        feed_tds = _float(data, "feed_tds", 35000.0)
        s1 = _stage_from_data(data, 1, qf1, pm1, feed_tds)
        qr1, pr1 = s1["reject_flow"], s1["reject_pressure_bar"]
        if solve_stage_pressures:
            pm2 = pr1 + target
        s2 = _stage_from_data(data, 2, qr1, pm2, s1["concentrate_tds_ppm"], s1.get("concentrate_composition_mg_l"), {"total_alkalinity_mol_kg":s1.get("concentrate_total_alkalinity_mol_kg"),"total_inorganic_carbon_mol_kg":s1.get("concentrate_total_inorganic_carbon_mol_kg")})
        qr2, pr2 = s2["reject_flow"], s2["reject_pressure_bar"]
    else:
        qr1, qr2 = getf("reject_flow_1"), getf("reject_flow_2")
        h1 = _manual_stage_dp(data, 1, qf1, qr1); pr1 = pm1 - h1["stage_dp_bar"]
        h2 = _manual_stage_dp(data, 2, qr1, qr2); pr2 = pm2 - h2["stage_dp_bar"]

    peff, meff = float(data["pump_eff"]), float(data["motor_eff"])
    veff = _vfd_eff(data, "vfd_eff", "pump_no_vfd")
    pret_rec = float(data["pretreatment_recovery"])
    pret_peff, pret_meff = float(data.get("pretreatment_pump_eff", data.get("pretreatment_eff", 0.82))), float(data.get("pretreatment_motor_eff", 1.0 if "pretreatment_eff" in data else 0.95))
    pret_veff = (1.0 if "pretreatment_eff" in data and "pretreatment_vfd_eff" not in data else _vfd_eff(data, "pretreatment_vfd_eff", "pretreatment_no_vfd"))
    rec1 = (qf1 - qr1) / qf1
    rec2 = (qr1 - qr2) / qr1
    inter_reject_ratio = _enforce_turbo_reject_ratio(qr2, qr1, "BiTurbo interstage turbocharger")
    feed_reject_ratio = _enforce_turbo_reject_ratio(qr1, qf1, "BiTurbo feed turbocharger")
    inter_eff_state = _turbo_case_efficiency(data, qr1, qr2, pm2, pr2, "inter_")
    inter_base_eff = inter_eff_state["overall_eff"]
    inter_workbook = str(data.get("inter_off_design_model",data.get("off_design_model",""))).lower() in {"spreadsheet","locked","case_locked"}
    turbine_dp_inter_base = target / max(1e-9,(1 - rec2 * inter_base_eff))
    inter_sg_default = solution_specific_gravity((s2 or {}).get("concentrate_tds_ppm",_float(data,"feed_tds",35000.0)), (s2 or {}).get("temperature_c",_float(data,"temperature_c",25.0))) if coupled else None
    inter_cv = turbine_cv(qr2, turbine_dp_inter_base, **_cv_inputs(data, "inter_", inter_sg_default))
    inter_eff = inter_base_eff if inter_workbook else inter_base_eff * inter_cv["efficiency_factor"]
    turbine_dp_inter = target / max(1e-9,(1 - rec2 * inter_eff))
    inter_cv = turbine_cv(qr2, turbine_dp_inter, **_cv_inputs(data, "inter_", inter_sg_default))
    inter_eff = inter_base_eff if inter_workbook else inter_base_eff * inter_cv["efficiency_factor"]
    turbine_dp_inter = target / max(1e-9,(1 - rec2 * inter_eff))
    brine_discharge = pr1 - turbine_dp_inter
    feed_turbine_dp = brine_discharge - pex
    if feed_turbine_dp <= 0:
        raise ValueError("Feed turbine ΔP is not positive. Check target interstage boost and pressure inputs.")
    feed_eff_state = _turbo_case_efficiency(data, qf1, qr1, pm1, brine_discharge, "feed_")
    feed_base_eff = feed_eff_state["overall_eff"]
    feed_workbook = str(data.get("feed_off_design_model",data.get("off_design_model",""))).lower() in {"spreadsheet","locked","case_locked"}
    feed_sg_default = solution_specific_gravity((s1 or {}).get("concentrate_tds_ppm",_float(data,"feed_tds",35000.0)), (s1 or {}).get("temperature_c",_float(data,"temperature_c",25.0))) if coupled else None
    feed_cv = turbine_cv(qr1, feed_turbine_dp, **_cv_inputs(data, "feed_", feed_sg_default))
    # First place the component efficiencies on the same pre-derate basis as the
    # overall efficiency.  A Cv efficiency multiplier is an overall multiplier,
    # so split it symmetrically across the turbine and pump components.
    feed_pre_scale = 1.0 if feed_workbook else feed_cv["efficiency_factor"]
    # BiTurbo feed-turbo penalty is an ABSOLUTE percentage-point derate applied
    # only after the normal design/off-design/Cv efficiency calculation.  The
    # component efficiencies are then re-scaled so their product exactly equals
    # the derated overall efficiency.
    feed_biturbo_penalty = 0.03 if str(data.get("curve","cfd")).lower()=="cfd" else 0.05
    feed_derate = derate_turbo_component_efficiencies(
        feed_eff_state["turbine_eff"], feed_eff_state["pump_eff"],
        feed_biturbo_penalty, pre_scale_factor=feed_pre_scale
    )
    feed_eff_pre_derate = feed_derate["overall_eff_pre_derate"]
    feed_eff = feed_derate["overall_eff_net"]
    feed_boost = feed_turbine_dp * (1 - rec1) * feed_eff

    pump_dp = pm1 - feed_boost - psuc
    hydraulic_kw = 0.0277 * pump_dp * qf1
    electric_kw = hydraulic_kw / peff / meff / veff
    qp = qf1 - qr2
    sec = electric_kw / qp
    pret_kw = _pump_wire_power_kw(qf1 / pret_rec, pret_p, pret_peff, pret_meff, pret_veff)
    pret_sec = pret_kw / qp

    result = {
        "membrane_coupling": coupled, "base_turbo_eff": inter_base_eff,
        "turbo_eff": inter_eff, "feed_turbo_eff": feed_eff,
        "feed_turbo_eff_before_biturbo_derate": feed_eff_pre_derate,
        "feed_turbo_biturbo_derate_fraction": feed_biturbo_penalty,
        "feed_turbo_biturbo_derate_percentage_points": 100.0*feed_biturbo_penalty,
        "inter_turbine_component_eff": inter_eff_state["turbine_eff"], "inter_pump_component_eff": inter_eff_state["pump_eff"],
        "feed_turbine_component_eff_before_biturbo_derate": feed_derate["turbine_eff_pre_derate"],
        "feed_pump_component_eff_before_biturbo_derate": feed_derate["pump_eff_pre_derate"],
        "feed_turbine_component_eff": feed_derate["turbine_eff_net"],
        "feed_pump_component_eff": feed_derate["pump_eff_net"],
        "feed_turbo_component_derate_factor": feed_derate["component_derate_factor"],
        "inter_turbo_efficiency_method": inter_eff_state["method"], "feed_turbo_efficiency_method": feed_eff_state["method"],
        "feed_flow": qf1, "membrane_pressure_1": pm1, "reject_pressure_1": pr1,
        "membrane_pressure_2": pm2, "reject_pressure_2": pr2, "pex": pex,
        "reject_flow_1": qr1, "reject_flow_2": qr2,
        "interstage_turbine_flow": qr2, "feed_turbine_flow": qr1,
        "inter_turbo_pump_flow": qr1, "inter_turbo_turbine_flow": qr2,
        "inter_turbo_reject_ratio": inter_reject_ratio, "inter_turbo_reject_ratio_status": turbo_reject_ratio_status(inter_reject_ratio),
        "feed_turbo_pump_flow": qf1, "feed_turbo_turbine_flow": qr1,
        "feed_turbo_reject_ratio": feed_reject_ratio, "feed_turbo_reject_ratio_status": turbo_reject_ratio_status(feed_reject_ratio),
        "product_flow": qp, "recovery": qp / qf1, "stage1_recovery": rec1,
        "stage2_recovery": rec2, "interstage_boost": target,
        "stage2_pressure_solved": bool(coupled and _bool(data, "solve_stage_pressures", False)),
        "inter_turbo_pfin": pr1, "feed_turbo_pfin": pm1 - feed_boost,
        "interstage_turbine_dp": turbine_dp_inter, "brine_discharge_pressure": brine_discharge,
        "feed_turbine_dp": feed_turbine_dp, "feed_turbo_boost": feed_boost,
        "feed_pump_dp": pump_dp, "hydraulic_kw": hydraulic_kw, "electric_kw": electric_kw,
        "pretreatment_kw": pret_kw, "pump_sec": sec, "ro_sec": sec, "pretreatment_sec": pret_sec,
        "total_sec": sec + pret_sec, "product_m3d": qp * 24,
    }
    _attach_cv(result, inter_cv, "inter_")
    _attach_cv(result, feed_cv, "feed_")
    if coupled:
        _attach_membrane(result, s1, "stage1_")
        _attach_membrane(result, s2, "stage2_")
        _attach_composite_permeate_carbon(result, s1, s2)
    else:
        for no, h in [(1,h1),(2,h2)]:
            for src, dst in [("pressure_vessels","pressure_vessels"),("elements_per_vessel","elements_per_vessel"),("membrane_elements","total_elements"),("stage_dp_bar","stage_dp"),("dp_per_element_bar","dp_per_element"),("max_actual_dp_per_element_bar","max_actual_dp_per_element"),("datasheet_max_dp_per_element_bar","datasheet_max_dp_per_element"),("dp_limit_fraction","dp_limit_fraction"),("vessel_feed_flow_m3h","vessel_feed_flow"),("vessel_reject_flow_m3h","vessel_reject_flow"),("membrane_manufacturer","membrane_manufacturer"),("membrane_model","membrane_model")]:
                result[f"stage{no}_{dst}"] = h[src]
    return display(result, fu, pu)



# Pressure-exchanger reference data. Legacy passive correlations are transcribed
# from the user-supplied ERI PX PowerModel Selector workbook (PX-OEM table).
PX_LEGACY_MODELS = {
    "PX-220": {"min_gpm": 140.0, "max_gpm": 220.0, "allow_min_gpm": 137.2},
    "PX-260": {"min_gpm": 180.0, "max_gpm": 260.0, "allow_min_gpm": 176.4},
    "PX-Q260": {"min_gpm": 180.0, "max_gpm": 260.0, "allow_min_gpm": 176.4},
    "PX-300": {"min_gpm": 200.0, "max_gpm": 300.0, "allow_min_gpm": 196.0},
    "PX-Q300": {"min_gpm": 200.0, "max_gpm": 300.0, "allow_min_gpm": 196.0},
    # Canonical Total RO Design neutral IDs. Legacy PX-* IDs remain accepted
    # only for backward compatibility with previously saved projects.
    "IC220": {"min_gpm": 140.0, "max_gpm": 220.0, "allow_min_gpm": 137.2},
    "IC260": {"min_gpm": 180.0, "max_gpm": 260.0, "allow_min_gpm": 176.4},
    "IC300": {"min_gpm": 200.0, "max_gpm": 300.0, "allow_min_gpm": 196.0},
    # Neutral high-capacity screening entries requested for Total RO Design.
    # Only the nominal maximum unit flow is embedded; hydraulic losses remain
    # user-editable generic screening assumptions rather than vendor claims.
    "IC600": {"min_gpm": 0.0, "max_gpm": 600.0, "allow_min_gpm": 0.0},
    "IC660": {"min_gpm": 0.0, "max_gpm": 660.0, "allow_min_gpm": 0.0},
}

IC_NEUTRAL_LABELS = {
    "PX-220":"IC220", "PX-260":"IC260", "PX-Q260":"IC260",
    "PX-300":"IC300", "PX-Q300":"IC300", "IC220":"IC220", "IC260":"IC260", "IC300":"IC300",
    "IC600":"IC600", "IC660":"IC660",
}
IC_CORRELATION_ALIASES={"IC220":"PX-220","IC260":"PX-Q260","IC300":"PX-Q300"}


def _px_legacy_losses(model, unit_flow_m3h, hp_pressure_bar, temp_c=25.0):
    """Return legacy ERI PowerModel-style HP/LP dP, lubrication and mixing.

    Correlations are directly transcribed from the PX-OEM sheet supplied by the
    user. They are retained as a legacy/reference mode rather than represented
    as current vendor guarantees.
    """
    model = IC_CORRELATION_ALIASES.get(model,model)
    q = flow_from_m3h(unit_flow_m3h, "gpm")
    p_psi = hp_pressure_bar * PSI_PER_BAR
    if model == "PX-220":
        lub_m3h = (0.0099*unit_flow_m3h + 0.00658*hp_pressure_bar + 0.00245*temp_c - 0.373)
        hpdp_psi = 0.00032*q*q + 0.00329*q
        lpdp_psi = 0.00022*q*q + 0.0017*q
        mix = 0.06
    elif model in {"PX-260", "PX-Q260"}:
        lub_m3h = (0.0099*unit_flow_m3h + 0.00658*hp_pressure_bar + 0.00245*temp_c - 0.4188)
        if model == "PX-Q260":
            hpdp_psi = 0.00031*q*q - 0.03931*q + 4.55053
            lpdp_psi = 0.0002*q*q - 0.01596*q
        else:
            # Workbook formula is written in m3/h and converted to psi.
            hpdp_psi = (0.000293*unit_flow_m3h**2 + 0.00209*unit_flow_m3h) * 14.5
            lpdp_psi = (0.000208*unit_flow_m3h**2 + 0.0005*unit_flow_m3h) * 14.5
        mix = 0.06
    elif model in {"PX-300", "PX-Q300"}:
        lub_gpm = 0.00815*q + 0.003*p_psi + 4.403*0.00245*temp_c - 2.54
        lub_m3h = flow_to_m3h(max(0.0, lub_gpm), "gpm")
        hpdp_psi = 0.0704*q - 9.1055
        lpdp_psi = 0.0704*q - 9.1055
        mix = max(0.0, -0.0002*q + 0.1)
    else:
        raise ValueError("Unknown isobaric chamber model.")
    return {
        "hp_dp_bar": max(0.0, hpdp_psi * BAR_PER_PSI),
        "lp_dp_bar": max(0.0, lpdp_psi * BAR_PER_PSI),
        "lubrication_m3h_per_unit": max(0.0, lub_m3h),
        "mixing_fraction": max(0.0, min(0.20, mix)),
    }


def _select_legacy_px(q_brine_m3h, requested="auto"):
    q_total_gpm = flow_from_m3h(q_brine_m3h, "gpm")
    candidates = [requested] if requested != "auto" else ["IC300", "IC260", "IC220"]
    best = None
    for rank, model in enumerate(candidates):
        spec = PX_LEGACY_MODELS[model]
        qty = max(1, math.ceil(q_total_gpm / spec["max_gpm"]))
        unit = q_total_gpm / qty
        within = spec["allow_min_gpm"] < unit <= spec["max_gpm"]
        penalty = (0 if within else 1000) + qty + abs(0.85 - unit/spec["max_gpm"])
        item = (penalty, rank, model, qty, unit, within)
        if best is None or item < best:
            best = item
    _, _, model, qty, unit_gpm, within = best
    return model, qty, flow_to_m3h(unit_gpm, "gpm"), within


def _px_device_state(data, q_brine_m3h, brine_pressure_bar):
    architecture = str(data.get("px_architecture", "passive")).lower()
    temp_c = _float(data, "temperature_c", 25.0)
    if architecture == "motorized":
        # Danfoss MPE 70: active, motor-controlled ERD. Published operating
        # envelope: 50-70 m3/h, HP dP <=0.66 bar, LP dP <=0.74 bar, 2.2 kW
        # motor; typical operating power 0.8 kW at 875 rpm / 60 bar.
        qty = max(1, math.ceil(q_brine_m3h / 70.0))
        unit = q_brine_m3h / qty
        pressure_unit = data.get("pressure_unit", "bar")
        hpdp = pressure_to_bar(_float(data, "mpe_hp_dp", 0.66), pressure_unit)
        lpdp = pressure_to_bar(_float(data, "mpe_lp_dp", 0.74), pressure_unit)
        mix = _float(data, "mpe_mixing", 0.02)
        typical_motor = _float(data, "mpe_motor_power", 0.8)
        # Engineering interpolation around the published typical point; capped
        # by the 2.2-kW nameplate. The displayed result is explicitly marked as
        # an estimate, not a vendor performance guarantee.
        per_motor = typical_motor * (unit/70.0) * max(brine_pressure_bar, 1.0)/60.0
        per_motor = max(0.0, min(2.2, per_motor))
        return {
            "architecture": "motorized", "manufacturer": "Isobaric Chamber", "model": "Active / motorized Isobaric Chamber",
            "qty": qty, "unit_flow_m3h": unit, "min_flow_m3h": 50.0, "max_flow_m3h": 70.0,
            "within_flow_range": 50.0 <= unit <= 70.0,
            "hp_dp_bar": hpdp, "lp_dp_bar": lpdp,
            "lubrication_m3h_per_unit": 0.0,
            "mixing_fraction": max(0.0, min(0.20, mix)),
            "motor_kw_per_unit": per_motor, "motor_kw_total": per_motor*qty,
            "motor_power_is_estimate": True,
        }
    requested = str(data.get("px_model", "auto"))
    model, qty, unit, within = _select_legacy_px(q_brine_m3h, requested)
    if model in {"IC600","IC660"}:
        pu=data.get("pressure_unit","bar")
        hpdp=pressure_to_bar(_float(data,"px_generic_hp_dp",pressure_from_bar(0.8,pu)),pu)
        lpdp=pressure_to_bar(_float(data,"px_generic_lp_dp",pressure_from_bar(0.8,pu)),pu)
        losses={"hp_dp_bar":max(0.0,hpdp),"lp_dp_bar":max(0.0,lpdp),
                "lubrication_m3h_per_unit":0.0,
                "mixing_fraction":max(0.0,min(0.20,_float(data,"px_generic_mixing",0.02)))}
        model_basis="generic high-capacity IC screening assumptions; verify project/vendor hydraulics"
    else:
        losses = _px_legacy_losses(model, unit, brine_pressure_bar, temp_c)
        model_basis="legacy correlation retained under neutral Total RO Design naming"
    spec = PX_LEGACY_MODELS[model]
    return {
        "architecture": "passive", "manufacturer": "Isobaric Chamber", "model": IC_NEUTRAL_LABELS.get(model,model),
        "qty": qty, "unit_flow_m3h": unit,
        "min_flow_m3h": flow_to_m3h(spec["allow_min_gpm"], "gpm"),
        "max_flow_m3h": flow_to_m3h(spec["max_gpm"], "gpm"),
        "within_flow_range": within,
        **losses, "motor_kw_per_unit": 0.0, "motor_kw_total": 0.0,
        "motor_power_is_estimate": False, "model_basis":model_basis,
    }


def _pressure_exchanger_base(data):
    """Single-stage SWRO + isobaric pressure exchanger calculation.

    The membrane is solved element-by-element. PX mixing is then coupled back
    into the membrane-feed salinity until the feed salinity / reject flow loop
    converges. Passive PX hydraulic correlations follow the user-supplied ERI
    PowerModel workbook; motorized mode represents Danfoss MPE 70 with editable
    published-envelope parameters.
    """
    fu, pu, getf, getp = common(data)
    qf = getf("feed_flow")
    pm = getp("membrane_pressure_1")
    psuc = getp("suction_pressure")
    # PX low-pressure/feed inlet is the same common low-pressure header as the HP pump inlet.
    lp_in = psuc
    px_lp_outlet_pressure = pressure_to_bar(_float(data, "px_lp_outlet_pressure", 1.5), pu)
    if px_lp_outlet_pressure < 1.5 - 1e-9:
        raise ValueError("PX brine exit backpressure must be at least 1.5 bar. Increase PX brine exit backpressure and recalculate.")
    if px_lp_outlet_pressure > lp_in + 1e-9:
        raise ValueError("PX brine exit backpressure cannot exceed the PX/HP-pump low-pressure inlet pressure. Increase HP pump inlet pressure or reduce PX exit backpressure.")
    pret_p = getp("pretreatment_discharge_pressure")
    water_mode = str(data.get("water_mode", "tds")).lower()
    base_comp = composition_from_request(data) if water_mode == "full" else None
    feed_tds = total_tds_mg_l(base_comp) if water_mode == "full" else _float(data, "feed_tds", 35000.0)
    coupled = _bool(data, "membrane_coupling", True)
    peff, meff = float(data["pump_eff"]), float(data["motor_eff"])
    veff = _vfd_eff(data, "vfd_eff", "pump_no_vfd")
    ceff, cmeff = float(data["circ_pump_eff"]), float(data["circ_motor_eff"])
    cveff = _vfd_eff(data, "circ_vfd_eff", "circ_no_vfd")
    pret_rec = float(data["pretreatment_recovery"])
    pret_peff, pret_meff = float(data.get("pretreatment_pump_eff", data.get("pretreatment_eff", 0.82))), float(data.get("pretreatment_motor_eff", 1.0 if "pretreatment_eff" in data else 0.95))
    pret_veff = (1.0 if "pretreatment_eff" in data and "pretreatment_vfd_eff" not in data else _vfd_eff(data, "pretreatment_vfd_eff", "pretreatment_no_vfd"))

    # Numerical coupling state. Warm starts are compatibility-checked and only
    # influence the initial iterate; engineering equations/tolerances are unchanged.
    signature = water_state_signature(data)
    warm = data.get("_px_warm_state") or _PX_STATE_CACHE.predictor(pm, signature)
    eff_feed_tds = feed_tds
    eff_comp = normalize_composition(base_comp) if water_mode == "full" else None
    warm_used = False
    if isinstance(warm, dict) and warm.get("signature") in (None, signature):
        try:
            wt=float(warm.get("effective_feed_tds", feed_tds))
            if math.isfinite(wt) and 0.5*feed_tds <= wt <= 2.5*max(feed_tds,1.0):
                eff_feed_tds=wt; warm_used=True
            wc=warm.get("effective_composition_mg_l")
            if water_mode == "full" and isinstance(wc, dict):
                candidate={k:max(0.0,float(wc.get(k,0.0))) for k in SPECIES}
                if total_tds_mg_l(candidate)>0: eff_comp=candidate
        except Exception:
            warm_used=False
    stage = None
    px_coupling_iterations = 0
    px_coupling_method = "not required" if not coupled else "Anderson accelerated"
    px_coupling_fallback = False
    px_trace = SolverTrace(px_coupling_method)

    def coupled_iteration(max_iter, alpha_start, adaptive=True, accelerated=True):
        nonlocal eff_feed_tds, eff_comp, stage, px_coupling_iterations, px_coupling_method
        prev_resid = None
        alpha = alpha_start
        mixer=AndersonMixer(memory=4)
        last_accelerated=False
        for it in range(1, max_iter + 1):
            px_coupling_iterations += 1
            if coupled:
                stage = _stage_from_data(data, 1, qf, pm, eff_feed_tds, eff_comp)
                qr, pr, qp = stage["reject_flow"], stage["reject_pressure_bar"], stage["permeate_flow"]
                brine_tds = stage["concentrate_tds_ppm"]
                brine_comp = stage.get("concentrate_composition_mg_l")
            else:
                qr = getf("reject_flow_1")
                h = _manual_stage_dp(data, 1, qf, qr)
                pr = pm - h["stage_dp_bar"]
                qp = qf - qr
                brine_tds = feed_tds / max(1.0-qp/qf, 1e-9)
                brine_comp = None
            dev = _px_device_state(data, qr, pr)
            lub = dev["lubrication_m3h_per_unit"] * dev["qty"]
            px_lp_flow = max(0.0, qr - lub)
            hpp_flow = max(0.0, qf - px_lp_flow)
            px_hp_tds = feed_tds + dev["mixing_fraction"] * (brine_tds - feed_tds)
            if water_mode == "full" and base_comp is not None and brine_comp is not None:
                px_hp_comp = {k: base_comp[k] + dev["mixing_fraction"]*(brine_comp[k]-base_comp[k]) for k in SPECIES}
                new_eff_comp = mix_compositions(base_comp, hpp_flow, px_hp_comp, px_lp_flow)
                new_eff_tds = total_tds_mg_l(new_eff_comp)
            else:
                px_hp_comp = None
                new_eff_comp = None
                new_eff_tds = (hpp_flow*feed_tds + px_lp_flow*px_hp_tds) / max(qf, 1e-12)
            resid = new_eff_tds - eff_feed_tds
            coupling_tol = 0.10 if _bool(data, "_solver_fast", False) else 0.01
            px_trace.add(px_coupling_iterations, abs(resid), method=("Anderson" if last_accelerated else "adaptive relaxation"))
            if not coupled or abs(resid) < coupling_tol:
                eff_feed_tds = new_eff_tds
                if new_eff_comp is not None: eff_comp = new_eff_comp
                return True, (qr, pr, qp, brine_tds, brine_comp, dev, lub, px_lp_flow, hpp_flow, px_hp_tds, px_hp_comp)

            # If the previous accelerated proposal worsened the residual, discard
            # its history and take a bounded line-search/trust-region style step.
            if prev_resid is not None and last_accelerated and abs(resid) > 1.15*abs(prev_resid):
                mixer.reset(); last_accelerated=False
                alpha=max(0.25,min(alpha,0.50)); px_trace.fallback("bounded line search")

            if adaptive and prev_resid is not None:
                if resid * prev_resid < 0: alpha = max(0.25, alpha * 0.55)
                elif abs(resid) < 0.70 * abs(prev_resid): alpha = min(0.82, alpha * 1.12)
                elif abs(resid) > 1.05 * abs(prev_resid): alpha = max(0.30, alpha * 0.70)

            proposal=None
            if accelerated:
                if new_eff_comp is not None and eff_comp is not None:
                    x=[eff_comp[k] for k in SPECIES]; gx=[new_eff_comp[k] for k in SPECIES]
                    cand=mixer.propose(x,gx)
                    if cand is not None:
                        # Trust region: permit extrapolation, but not more than 50%
                        # beyond the current fixed-point displacement per species.
                        bounded=[]
                        for a,b,c in zip(x,gx,cand):
                            span=abs(b-a); lo=max(0.0,min(a,b)-0.5*span); hi=max(a,b)+0.5*span
                            bounded.append(min(max(c,lo),hi))
                        proposal=bounded
                else:
                    cand=mixer.propose([eff_feed_tds],[new_eff_tds])
                    if cand is not None:
                        span=abs(new_eff_tds-eff_feed_tds); lo=max(0.0,min(eff_feed_tds,new_eff_tds)-0.5*span); hi=max(eff_feed_tds,new_eff_tds)+0.5*span
                        proposal=[min(max(cand[0],lo),hi)]

            if proposal is not None:
                if new_eff_comp is not None and eff_comp is not None:
                    eff_comp={k:max(0.0,proposal[i]) for i,k in enumerate(SPECIES)}
                    eff_feed_tds=total_tds_mg_l(eff_comp)
                else:
                    eff_feed_tds=max(0.0,proposal[0])
                last_accelerated=True
            else:
                eff_feed_tds = (1.0-alpha)*eff_feed_tds + alpha*new_eff_tds
                if new_eff_comp is not None:
                    eff_comp = {k:max(0.0,(1.0-alpha)*eff_comp[k]+alpha*new_eff_comp[k]) for k in SPECIES}
                last_accelerated=False
            prev_resid = resid
        return False, None

    fast_px_trial = _bool(data, "_solver_fast", False)
    # Pressure-search candidates only need a stable product-flow estimate.  Use a
    # shorter PX/feed-salinity coupling during those candidate evaluations; the
    # accepted pressure is always recalculated afterward with the full reporting
    # tolerance and fallback.
    ok, state = coupled_iteration(8 if fast_px_trial else 24, 0.62, adaptive=True, accelerated=True)
    if not ok and coupled:
        px_coupling_fallback = True
        px_coupling_method = "fast conservative fallback" if fast_px_trial else "conservative fallback"
        eff_feed_tds = feed_tds
        eff_comp = normalize_composition(base_comp) if water_mode == "full" else None
        stage = None
        px_trace.fallback("adaptive relaxation")
        ok, state = coupled_iteration(20 if fast_px_trial else 80, 0.45, adaptive=False, accelerated=False)
    if not ok:
        raise ValueError("Isobaric Chamber / membrane salinity coupling did not converge, including conservative fallback.")
    qr, pr, qp, brine_tds, brine_comp, dev, lub, px_lp_flow, hpp_flow, px_hp_tds, px_hp_comp = state

    px_hp_out_pressure = pr - dev["hp_dp_bar"]
    px_lp_out_pressure = px_lp_outlet_pressure
    actual_px_lp_dp = max(0.0, lp_in - px_lp_out_pressure)
    circ_flow = px_lp_flow
    circ_dp = max(0.0, pm - px_hp_out_pressure)
    hpp_dp = max(0.0, pm - psuc)
    hpp_hyd_kw = hpp_flow*hpp_dp/36.0
    circ_hyd_kw = circ_flow*circ_dp/36.0
    hpp_vcmp = None; circ_vcmp = None
    pump_basis = str(data.get("pump_curve_basis","auto")).lower()
    pump_density = 1000.0 * solution_specific_gravity(eff_feed_tds, _float(data,"temperature_c",25.0))
    if pump_basis in {"vcmp","vcmp_auto","database"} and hpp_flow > 1e-12 and hpp_dp > 1e-12:
        hsel=select_vcmp_pump(hpp_flow,hpp_dp,density_kg_m3=pump_density,motor_eff=meff,vfd_eff=veff,
            min_vfd_hz=float(data.get("vcmp_min_vfd_hz",40.0) or 40.0),max_vfd_hz=float(data.get("vcmp_max_vfd_hz",60.0) or 60.0),
            flow_margin=float(data.get("vcmp_flow_margin",0.05) or 0.0),head_margin=float(data.get("vcmp_head_margin",0.05) or 0.0),
            reduced_impeller_penalty_pp=float(data.get("vcmp_reduced_impeller_eta_penalty_pp",2.0) or 0.0),
            low_speed_derate_pp_per_10pct=float(data.get("vcmp_low_speed_eta_derate_pp_per_10pct",0.0) or 0.0),reference_rpm_60=data.get("vcmp_reference_rpm_60") or None,top_n=5)
        if hsel.get("ok"): hpp_vcmp=hsel["selected"]
    if pump_basis in {"vcmp","vcmp_auto","database"} and circ_flow > 1e-12 and circ_dp > 1e-12:
        csel=select_vcmp_pump(circ_flow,circ_dp,density_kg_m3=pump_density,motor_eff=cmeff,vfd_eff=cveff,
            min_vfd_hz=float(data.get("vcmp_min_vfd_hz",40.0) or 40.0),max_vfd_hz=float(data.get("vcmp_max_vfd_hz",60.0) or 60.0),
            flow_margin=float(data.get("vcmp_flow_margin",0.05) or 0.0),head_margin=float(data.get("vcmp_head_margin",0.05) or 0.0),
            reduced_impeller_penalty_pp=float(data.get("vcmp_reduced_impeller_eta_penalty_pp",2.0) or 0.0),
            low_speed_derate_pp_per_10pct=float(data.get("vcmp_low_speed_eta_derate_pp_per_10pct",0.0) or 0.0),reference_rpm_60=data.get("vcmp_reference_rpm_60") or None,top_n=5)
        if csel.get("ok"): circ_vcmp=csel["selected"]
    hpp_kw = float(hpp_vcmp["wire_kw"]) if hpp_vcmp is not None else hpp_hyd_kw/peff/meff/veff
    circ_kw = float(circ_vcmp["wire_kw"]) if circ_vcmp is not None else (circ_hyd_kw/ceff/cmeff/cveff if circ_flow > 0 else 0.0)
    motor_kw = dev["motor_kw_total"]
    pret_kw = _pump_wire_power_kw(qf/pret_rec, pret_p, pret_peff, pret_meff, pret_veff)
    ro_kw = hpp_kw + circ_kw + motor_kw
    ro_sec = ro_kw/max(qp, 1e-12)
    total_kw = ro_kw + pret_kw
    total_sec = total_kw/max(qp, 1e-12)

    # ERI PowerModel-style isobaric efficiency from energy-out / energy-in.
    hp_in_energy = qr*pr
    lp_in_energy = px_lp_flow*lp_in
    hp_out_energy = px_lp_flow*px_hp_out_pressure
    lp_out_energy = qr*px_lp_out_pressure
    px_eff = (hp_out_energy + lp_out_energy) / max(hp_in_energy + lp_in_energy, 1e-12)
    recovered_kw = max(0.0, hp_out_energy - px_lp_flow*lp_in)/36.0

    result = {
        "membrane_coupling": coupled, "feed_flow": qf, "raw_feed_tds": feed_tds, "water_mode": water_mode,
        "membrane_pressure_1": pm, "reject_pressure_1": pr,
        "reject_flow_1": qr, "product_flow": qp, "recovery": qp/qf,
        "effective_membrane_feed_tds": eff_feed_tds,
        "px_architecture": dev["architecture"], "px_manufacturer": dev["manufacturer"], "px_model": dev["model"],
        "px_qty": dev["qty"], "px_unit_flow": dev["unit_flow_m3h"],
        "px_min_unit_flow": dev["min_flow_m3h"], "px_max_unit_flow": dev["max_flow_m3h"],
        "px_within_flow_range": dev["within_flow_range"],
        "px_hp_dp": dev["hp_dp_bar"], "px_lp_dp": actual_px_lp_dp, "px_model_lp_dp": dev["lp_dp_bar"],
        "px_hp_in_pressure": pr, "px_hp_out_pressure": px_hp_out_pressure,
        "px_lp_in_pressure": lp_in, "px_lp_out_pressure": px_lp_out_pressure,
        "px_lubrication_flow": lub, "px_lp_flow": px_lp_flow,
        "px_mixing": dev["mixing_fraction"], "px_feed_tds_after_mixing": px_hp_tds,
        "px_overall_eff": px_eff, "px_recovered_kw": recovered_kw,
        "px_motor_kw": motor_kw, "px_motor_kw_per_unit": dev["motor_kw_per_unit"],
        "px_motor_power_is_estimate": dev["motor_power_is_estimate"],
        "hpp_flow": hpp_flow, "hpp_dp": hpp_dp, "hpp_hydraulic_kw": hpp_hyd_kw, "electric_kw": hpp_kw,
        "circ_flow": circ_flow, "circ_dp": circ_dp, "circ_hydraulic_kw": circ_hyd_kw, "circ_kw": circ_kw,
        "px_hpp_pump_source":"vcmp_database" if hpp_vcmp is not None else "manual_efficiency_fallback",
        "px_hpp_pump_family":hpp_vcmp.get("product_family") if hpp_vcmp else None,
        "px_hpp_pump_stage_config":hpp_vcmp.get("stage_config") if hpp_vcmp else None,
        "px_hpp_pump_frequency_hz":hpp_vcmp.get("frequency_hz") if hpp_vcmp else None,
        "px_hpp_pump_efficiency":hpp_vcmp.get("pump_efficiency") if hpp_vcmp else peff,
        "px_hpp_pump_shaft_torque_nm":hpp_vcmp.get("shaft_torque_nm") if hpp_vcmp else None,
        "px_hpp_pump_speed_rpm":hpp_vcmp.get("speed_rpm") if hpp_vcmp else None,
        "px_booster_pump_source":"vcmp_database" if circ_vcmp is not None else "manual_efficiency_fallback",
        "px_booster_pump_family":circ_vcmp.get("product_family") if circ_vcmp else None,
        "px_booster_pump_stage_config":circ_vcmp.get("stage_config") if circ_vcmp else None,
        "px_booster_pump_frequency_hz":circ_vcmp.get("frequency_hz") if circ_vcmp else None,
        "px_booster_pump_efficiency":circ_vcmp.get("pump_efficiency") if circ_vcmp else ceff,
        "px_booster_pump_shaft_torque_nm":circ_vcmp.get("shaft_torque_nm") if circ_vcmp else None,
        "px_booster_pump_speed_rpm":circ_vcmp.get("speed_rpm") if circ_vcmp else None,
        "vcmp_mechanical_seal_note":"VCMP use on PX/interstage booster duty requires verification of a suitable high-pressure mechanical seal and pressure rating.",
        "pretreatment_kw": pret_kw, "ro_electric_kw": ro_kw, "total_electric_kw": total_kw,
        "pump_sec": hpp_kw/max(qp,1e-12), "px_aux_sec": (circ_kw+motor_kw)/max(qp,1e-12),
        "ro_sec": ro_sec, "pretreatment_sec": pret_kw/max(qp,1e-12), "total_sec": total_sec,
        "product_m3d": qp*24,
        "px_coupling_iterations": px_coupling_iterations,
        "px_coupling_method": px_coupling_method,
        "px_coupling_fallback": px_coupling_fallback,
        "px_warm_start_used": warm_used,
        "solver_diagnostics": px_trace.as_dict(0.10 if fast_px_trial else 0.01),
        "_px_solver_state": {
            "signature": signature,
            "effective_feed_tds": eff_feed_tds,
            "effective_composition_mg_l": dict(eff_comp or {}),
            "thermodynamic": water_state_snapshot(pressure_bar=pm, flow_m3h=qf, temperature_c=_float(data,"temperature_c",25.0),
                density_kg_l=solution_specific_gravity(eff_feed_tds,_float(data,"temperature_c",25.0)),
                tds_mg_l=eff_feed_tds, composition=eff_comp or {}, extra={"px_lp_flow_m3h":px_lp_flow,"hpp_flow_m3h":hpp_flow}),
        },
    }
    _PX_STATE_CACHE.put(pm, signature, result["_px_solver_state"], abs(new_eff_tds-eff_feed_tds) if 'new_eff_tds' in locals() else None)
    if stage:
        _attach_membrane(result, stage, "stage1_")
    else:
        for src, dst in [("pressure_vessels","pressure_vessels"),("elements_per_vessel","elements_per_vessel"),("membrane_elements","total_elements"),("stage_dp_bar","stage_dp"),("dp_per_element_bar","dp_per_element"),("max_actual_dp_per_element_bar","max_actual_dp_per_element"),("datasheet_max_dp_per_element_bar","datasheet_max_dp_per_element"),("dp_limit_fraction","dp_limit_fraction"),("vessel_feed_flow_m3h","vessel_feed_flow"),("vessel_reject_flow_m3h","vessel_reject_flow"),("membrane_manufacturer","membrane_manufacturer"),("membrane_model","membrane_model")]:
            result[f"stage1_{dst}"] = h[src]
    return display(result, fu, pu)





def _pump_curve_screening(data, duty_flow_m3h, duty_dp_bar, static_dp_bar, eta_bep, motor_eff, vfd_eff, density_kg_m3=998.0):
    """HPP pump-curve screening with VCMP database support.

    ``pump_curve_basis='vcmp_auto'`` uses the user-supplied 431-configuration
    vertical-multistage pump database and VFD affinity-law model. If no single
    database curve can cover the duty within the configured envelope, Total RO
    Design falls back to the legacy normalized preliminary curve and retains the
    entered pump efficiency. ``auto`` and ``manual`` preserve the legacy behavior
    for old project files and regression compatibility.
    """
    requested_basis = str(data.get('pump_curve_basis','auto')).lower()
    fu, pu = data.get('flow_unit','m3/h'), data.get('pressure_unit','bar')
    if requested_basis in {'vcmp','vcmp_auto','database'}:
        sel = select_vcmp_pump(
            duty_flow_m3h, duty_dp_bar, density_kg_m3=density_kg_m3,
            motor_eff=motor_eff, vfd_eff=vfd_eff,
            min_vfd_hz=float(data.get('vcmp_min_vfd_hz',40.0) or 40.0),
            max_vfd_hz=float(data.get('vcmp_max_vfd_hz',60.0) or 60.0),
            flow_margin=float(data.get('vcmp_flow_margin',0.05) or 0.0),
            head_margin=float(data.get('vcmp_head_margin',0.05) or 0.0),
            reduced_impeller_penalty_pp=float(data.get('vcmp_reduced_impeller_eta_penalty_pp',2.0) or 0.0),
            low_speed_derate_pp_per_10pct=float(data.get('vcmp_low_speed_eta_derate_pp_per_10pct',0.0) or 0.0),
            reference_rpm_60=data.get('vcmp_reference_rpm_60') or None,
            top_n=5,
        )
        if sel.get('ok'):
            op = sel['selected']
            static_dp = max(0.0, min(float(static_dp_bar), duty_dp_bar*0.98))
            ksys = max(0.0,(duty_dp_bar-static_dp)/max(duty_flow_m3h*duty_flow_m3h,1e-30))
            raw_points = vcmp_curve_points(
                op['source_id'], op['speed_ratio'], density_kg_m3=density_kg_m3,
                motor_eff=motor_eff, vfd_eff=vfd_eff,
                reduced_impeller_penalty_pp=float(data.get('vcmp_reduced_impeller_eta_penalty_pp',2.0) or 0.0),
                low_speed_derate_pp_per_10pct=float(data.get('vcmp_low_speed_eta_derate_pp_per_10pct',0.0) or 0.0),
                reference_rpm_60=data.get('vcmp_reference_rpm_60') or None,
                samples=25,
            )
            points=[]
            for pt in raw_points:
                q=float(pt['flow_m3h']); pdp=float(pt['pump_dp_bar']); sdp=static_dp+ksys*q*q
                points.append({
                    **pt,
                    'flow_m3h': flow_from_m3h(q,fu),
                    'pump_dp_bar': pressure_from_bar(pdp,pu),
                    'system_dp_bar': pressure_from_bar(sdp,pu),
                })
            br=float(op.get('flow_bep_ratio') or 0.0)
            if br and 0.80 <= br <= 1.10: zone='preferred'
            elif br and br < 0.80: zone='left_of_bep'
            elif br: zone='right_of_bep'
            else: zone='database_curve'
            return {
                'pump_curve_basis':'vcmp_auto', 'pump_curve_source':'vcmp_database',
                'pump_curve_is_typical':False, 'pump_curve_points':points,
                'pump_curve_points_are_display_units':True,
                'pump_database_records':sel.get('database_records',0),
                'pump_database_selection_basis':sel.get('selection_basis'),
                'pump_database_fallback':False,
                'pump_selected_family':op['product_family'],
                'pump_selected_stage_config':op['stage_config'],
                'pump_selected_source_id':op['source_id'],
                'pump_selected_reduced_impellers':op['reduced_impellers'],
                'pump_operating_frequency_hz':op['frequency_hz'],
                'pump_operating_speed_ratio':op['speed_ratio'],
                'pump_operating_speed_rpm':op.get('speed_rpm'),
                'pump_reference_rpm_60':op.get('reference_rpm_60'),
                'pump_shaft_torque_nm':op.get('shaft_torque_nm'),
                'pump_required_head_m':op['required_head_m'],
                'pump_generated_head_m':op['actual_head_m'],
                'pump_generated_dp':op['actual_dp_bar'],
                'pump_shutoff_dp':op.get('shutoff_dp_bar'),
                'pump_shutoff_head_m':op.get('shutoff_head_m'),
                'pump_rpm_basis':op.get('rpm_basis'),
                'pump_head_margin_pct':op['head_margin_pct'],
                'pump_min_speed_limited':op['min_speed_limited'],
                'pump_duty_flow':duty_flow_m3h,'pump_duty_dp':duty_dp_bar,
                'pump_operating_flow':duty_flow_m3h,'pump_operating_dp':duty_dp_bar,
                'pump_operating_bep_flow_ratio':br if br else None,
                'pump_operating_efficiency':op['pump_efficiency'],
                'pump_operating_zone':zone,'pump_operating_status':'ok',
                'pump_operating_wire_kw':op['wire_kw'],
                'pump_operating_shaft_kw':op['shaft_kw'],
                'pump_operating_hydraulic_kw':op['hydraulic_kw'],
                'pump_operating_overall_wire_efficiency':op['overall_wire_efficiency'],
                'pump_database_top_options':sel.get('options',[]),
                'pump_vcmp_min_vfd_hz':sel.get('min_vfd_hz'),
                'pump_vcmp_max_vfd_hz':sel.get('max_vfd_hz'),
                'pump_vcmp_flow_margin':sel.get('flow_margin'),
                'pump_vcmp_head_margin':sel.get('head_margin'),
            }
        # No catalog curve covers the duty. Continue with the legacy preliminary
        # curve so the calculation still runs, but make the fallback explicit.
        vcmp_reason = sel.get('reason') or 'No VCMP database curve covers this duty.'
        requested_basis = 'auto'
    else:
        vcmp_reason = None

    # Legacy normalized typical centrifugal-pump curve vs local RO system curve.
    basis = requested_basis
    if basis not in {'auto','manual'}: basis='auto'
    if basis == 'manual':
        q_bep_user = _float(data,'pump_bep_flow',None); dp_bep_user = _float(data,'pump_bep_dp',None)
        if q_bep_user is None or dp_bep_user is None:
            raise ValueError('Manual pump-curve screening requires BEP flow and BEP differential pressure.')
        q_bep = flow_to_m3h(q_bep_user, fu); dp_bep = pressure_to_bar(dp_bep_user, pu)
    else:
        q_bep = duty_flow_m3h; dp_bep = duty_dp_bar
    if q_bep <= 0 or dp_bep <= 0: raise ValueError('Pump BEP flow and differential pressure must be greater than zero.')
    shutoff_ratio = float(data.get('pump_shutoff_head_ratio',1.18) or 1.18)
    if not 1.05 <= shutoff_ratio <= 1.40: raise ValueError('Typical pump shutoff-head ratio must be between 1.05 and 1.40 × BEP head.')
    static_dp = max(0.0, min(float(static_dp_bar), duty_dp_bar*0.98))
    ksys = max(0.0,(duty_dp_bar-static_dp)/max(duty_flow_m3h*duty_flow_m3h,1e-30))
    a = shutoff_ratio-1.0
    def pump_dp(q):
        x=q/q_bep
        return dp_bep*(1.0+a*(1.0-x*x))
    def sys_dp(q): return static_dp+ksys*q*q
    lo, hi = 0.0, max(1.6*q_bep,1.25*duty_flow_m3h)
    flo, fhi = pump_dp(lo)-sys_dp(lo), pump_dp(hi)-sys_dp(hi)
    if flo*fhi > 0:
        qop=None; dpop=None; status='no_intersection'
    else:
        for _ in range(80):
            mid=.5*(lo+hi); fm=pump_dp(mid)-sys_dp(mid)
            if abs(fm)<1e-8 or hi-lo<1e-8*max(1.0,q_bep): break
            if flo*fm<=0: hi=mid; fhi=fm
            else: lo=mid; flo=fm
        qop=.5*(lo+hi); dpop=.5*(pump_dp(qop)+sys_dp(qop)); status='ok'
    points=[]
    for j in range(15):
        q=1.4*q_bep*j/14.0; x=q/q_bep
        eta=max(0.45*eta_bep,eta_bep*(1.0-1.55*(x-1.0)**2))
        points.append({'flow_m3h':q,'pump_dp_bar':max(0.0,pump_dp(q)),'system_dp_bar':sys_dp(q),'efficiency':eta})
    out={'pump_curve_basis':basis,'pump_curve_source':'typical_screening','pump_curve_is_typical':True,'pump_curve_points':points,
         'pump_bep_flow':q_bep,'pump_bep_dp':dp_bep,'pump_shutoff_head_ratio':shutoff_ratio,
         'pump_system_static_dp':static_dp,'pump_duty_flow':duty_flow_m3h,'pump_duty_dp':duty_dp_bar,
         'pump_operating_status':status}
    if vcmp_reason:
        out.update({'pump_database_fallback':True,'pump_database_fallback_reason':vcmp_reason})
    if qop is not None:
        x=qop/q_bep; eta=max(0.45*eta_bep,eta_bep*(1.0-1.55*(x-1.0)**2))
        if 0.80 <= x <= 1.10: zone='preferred'
        elif x < 0.80: zone='left_of_bep'
        else: zone='right_of_bep'
        out.update({'pump_operating_flow':qop,'pump_operating_dp':dpop,'pump_operating_bep_flow_ratio':x,
                    'pump_operating_efficiency':eta,'pump_operating_zone':zone,
                    'pump_operating_wire_kw':_pump_wire_power_kw(qop,dpop,eta,motor_eff,vfd_eff)})
    return out

# ---- Shared v18.1 calculation conditioning -----------------------------------------

def _attach_prepared_feed_carbonate_state(data):
    """Solve the unchanged full-water feed carbonate state once per request.

    In inverse pressure/recovery mode the membrane engine evaluates the same
    feed chemistry at several candidate pressures.  Carbonate equilibrium does
    not depend on feed pressure in this model, so recomputing it at every trial
    is duplicate work.  This cached state is request-local and is invalidated by
    ``_prepare_calculation_data`` whenever water chemistry or acid dosing changes.
    """
    d=data
    if str(d.get("water_mode","tds")).lower() != "full":
        d.pop("_feed_carbonate_state",None)
        return d
    existing=d.get("_feed_carbonate_state")
    if isinstance(existing,dict) and existing.get("_prepared_feed_state"):
        return d
    comp=composition_from_request(d)
    temp=float(_float(d,"temperature_c",25.0) or 25.0)
    ph=float(_float(d,"feed_ph",8.0) or 8.0)
    ta=analytical_alkalinity_mol_kg(comp,temp)
    state=dict(solve_carbonate_state(comp,temp,ph=ph,total_alkalinity_mol_kg=ta))
    state["_prepared_feed_state"]=True
    state["_source_temperature_c"]=temp
    state["_source_ph"]=ph
    d["_feed_carbonate_state"]=state
    return d


def _prepare_calculation_data(data):
    """Clone the request and apply configured acid dosing only at calculation time.

    The Water Quality UI stores the untreated analytical water.  If acid dosing is
    enabled, the counter-ion, pH, alkalinity and TDS are updated on this calculation
    copy.  This makes every N/N-1 and hydraulic-envelope case report its own mass
    rate while keeping the source-water analysis unchanged.
    """
    d = dict(data)
    if d.get("_acid_dosing_result") is not None:
        return _attach_prepared_feed_carbonate_state(d)
    # Never trust a feed-state cache carried with raw user inputs; calculate it
    # again after any acid/water conditioning below. Internal solver trials carry
    # ``_acid_dosing_result`` and reuse the already prepared state above.
    d.pop("_feed_carbonate_state",None)
    enabled = _bool(d, "acid_enabled", False)
    acid = str(d.get("acid_type", "none") or "none").lower()
    if not enabled or acid in {"", "none", "off"}:
        d.pop("_acid_dosing_result", None)
        return _attach_prepared_feed_carbonate_state(d)
    if str(d.get("water_mode", "full")).lower() != "full":
        raise ValueError("Acid dosing requires Full water chemistry mode so alkalinity and counter-ion addition can be calculated.")
    comp = composition_from_request(d)
    fu = d.get("flow_unit", "m3/h")
    q_user = _float(d, "feed_flow", None)
    q_m3h = flow_to_m3h(q_user, fu) if q_user not in (None, "") else None
    dose = acid_dose_to_target_ph(
        comp, _float(d, "temperature_c", 25.0), _float(d, "feed_ph", 8.0),
        _float(d, "acid_target_ph", 7.0), acid,
        _float(d, "acid_solution_strength_pct", None),
        _float(d, "acid_solution_density_kg_l", None), q_m3h
    )
    for ion, value in dose["composition"].items():
        d[f"ion_{ion}"] = float(value)
    d["feed_ph"] = float(dose["resulting_ph"])
    d["feed_tds"] = total_tds_mg_l(dose["composition"])
    d["analysis_tds"] = d["feed_tds"]
    d["_acid_dosing_result"] = dose
    return _attach_prepared_feed_carbonate_state(d)

def _attach_acid_dosing(result, prepared):
    dose = prepared.get("_acid_dosing_result")
    if dose:
        result["acid_dosing_enabled"] = True
        result["acid_dosing"] = dict(dose)
        result["acid_type"] = dose.get("acid_type")
        result["acid_dose_mg_l"] = dose.get("pure_acid_mg_l")
        result["acid_commercial_l_m3"] = dose.get("commercial_solution_l_m3")
        result["acid_pure_kg_h"] = dose.get("pure_acid_kg_h")
        result["acid_pure_kg_d"] = dose.get("pure_acid_kg_d")
        result["acid_commercial_l_h"] = dose.get("commercial_solution_l_h")
        result["acid_commercial_l_d"] = (float(dose.get("commercial_solution_l_h") or 0.0) * 24.0) if dose.get("commercial_solution_l_h") is not None else None
        result["acid_adjusted_feed_composition_mg_l"] = dict(dose.get("composition") or {})
        result["acid_adjusted_feed_tds_mg_l"] = total_tds_mg_l(dose.get("composition") or {})
        result["acid_adjusted_feed_ph"] = dose.get("resulting_ph")
        result["acid_adjusted_feed_alkalinity_mg_l_as_hco3"] = dose.get("resulting_alkalinity_mg_l_as_hco3")
    else:
        result["acid_dosing_enabled"] = False
    return result

def _interstage_equipment(data, stage_no):
    raw = str(data.get(f"interstage_equipment_{stage_no}", "") or "").strip().lower().replace("+", "_")
    aliases = {"booster":"pump", "booster_pump":"pump", "turbocharger":"turbo", "turbo_pump":"turbo_pump",
               "pump_turbo":"turbo_pump", "turbo_and_pump":"turbo_pump", "nothing":"none"}
    raw = aliases.get(raw, raw)
    if raw in {"none","pump","turbo","turbo_pump"}:
        return raw
    # Backward compatibility: an entered boost in an old project represented a booster pump.
    return "pump" if (_float(data, f"interstage_boost_{stage_no}", 0.0) or 0.0) > 0 else "none"

def _interstage_boost_bar(data, stage_no, pressure_unit):
    eq = _interstage_equipment(data, stage_no)
    if eq == "none":
        return 0.0
    boost = pressure_to_bar(_float(data, f"interstage_boost_{stage_no}", 0.0) or 0.0, pressure_unit)
    if boost < 0:
        raise ValueError(f"Stage {stage_no} interstage boost cannot be negative.")
    return boost


INTERSTAGE_CONTROL_MODES = {"manual", "balance_flux", "balance_polarization", "target_recovery"}
INTERSTAGE_BALANCE_BASES = {"lead", "average"}

def _interstage_control_mode(data):
    raw = str(data.get("interstage_control_objective", "manual") or "manual").strip().lower()
    aliases = {"balance_cp":"balance_polarization", "polarization":"balance_polarization",
               "flux":"balance_flux", "recovery":"target_recovery"}
    raw = aliases.get(raw, raw)
    return raw if raw in INTERSTAGE_CONTROL_MODES else "manual"

def _interstage_balance_basis(data):
    raw = str(data.get("interstage_balance_basis", "average") or "average").strip().lower()
    return raw if raw in INTERSTAGE_BALANCE_BASES else "average"

def _small_linear_solve(a, b):
    """Solve a tiny dense linear system with pivoted Gaussian elimination."""
    n=len(b); m=[list(map(float,row))+[float(b[i])] for i,row in enumerate(a)]
    for k in range(n):
        pivot=max(range(k,n), key=lambda i: abs(m[i][k]))
        if abs(m[pivot][k]) < 1e-10:
            raise ValueError("Interstage control Jacobian is singular near the requested operating point.")
        if pivot != k: m[k],m[pivot]=m[pivot],m[k]
        d=m[k][k]
        for j in range(k,n+1): m[k][j]/=d
        for i in range(n):
            if i==k: continue
            f=m[i][k]
            if abs(f)<1e-18: continue
            for j in range(k,n+1): m[i][j]-=f*m[k][j]
    return [m[i][n] for i in range(n)]

def _stage_balance_metric(result, stage_no, objective, basis):
    if objective == "balance_flux":
        if basis == "lead":
            prof=result.get(f"stage{stage_no}_element_profile") or []
            if not prof: raise ValueError(f"Stage {stage_no} lead-element flux is unavailable for balancing.")
            return float(prof[0]["flux_lmh"])
        return float(result[f"stage{stage_no}_flux_lmh"])
    if objective == "balance_polarization":
        if basis == "lead":
            prof=result.get(f"stage{stage_no}_element_profile") or []
            if not prof: raise ValueError(f"Stage {stage_no} lead-element polarization factor is unavailable for balancing.")
            return float(prof[0]["polarization_factor"])
        return float(result[f"stage{stage_no}_polarization_factor"])
    raise ValueError("Unknown interstage balance objective.")



def _target_recovery_fraction_for_seed(data):
    """Return the requested overall recovery fraction for a fast hydraulic seed.

    This helper is deliberately algebraic.  It does not replace the authoritative
    membrane solve; it only supplies a physically informed initial condition for
    the nonlinear interstage-pressure controller.
    """
    fu=data.get("flow_unit","m3/h")
    q0=flow_to_m3h(_float(data,"feed_flow",0.0) or 0.0,fu)
    if q0 <= 0:
        return None
    raw=_float(data,"target_recovery",None)
    if raw is not None:
        r=raw/100.0 if raw>1 else raw
        if 0 < r <= 0.95:
            return r
    q=_float(data,"target_product_flow",None)
    if q is not None:
        qp=flow_to_m3h(q,fu)
        r=qp/q0
        if 0 < r <= 0.95:
            return r
    return None


def _stage_active_area_for_seed(data, stage_no):
    """Active membrane area represented by one stage for boost-seed allocation."""
    vessels=max(1,int(round(_float(data,f"vessels_{stage_no}",1) or 1)))
    epv=max(1,min(8,int(round(_float(data,f"elements_per_vessel_{stage_no}",7) or 7))))
    mid=str(data.get(f"membrane_{stage_no}") or data.get("membrane_1") or "")
    try:
        area=float(get_membrane(mid).get("area_m2") or get_membrane(mid).get("active_area_m2") or 37.0)
    except Exception:
        area=37.0
    return vessels*epv*area


def _interstage_osmotic_boost_seeds(data, adjustable):
    """Physics-based initial interstage boost estimates.

    Rule of thumb approved for CalcOsPower:
        boost seed ~= increase in feed osmotic pressure since the last hydraulic
        energy input (HPP / booster / turbo).

    Stage permeate is provisionally apportioned by active membrane area, which is
    the equal-flux first approximation.  The subsequent full nonlinear solve then
    refines pressure for actual pressure losses, membrane transport/fouling,
    temperature, permeate backpressure and the selected flux/CP/recovery target.
    """
    n=_multistage_count(data)
    adjustable=set(int(i) for i in adjustable)
    fu=data.get("flow_unit","m3/h")
    q0=flow_to_m3h(_float(data,"feed_flow",0.0) or 0.0,fu)
    target_r=_target_recovery_fraction_for_seed(data)
    feed_tds=max(0.0,_float(data,"feed_tds",_float(data,"analysis_tds",0.0)) or 0.0)
    temp=_float(data,"temperature_c",25.0) or 25.0
    if q0<=0 or target_r is None or feed_tds<=0:
        return {"boost_seed_bar":{},"stage_feed_osmotic_bar":{},"energy_anchor_stage":{},"basis":"unavailable"}

    areas=[_stage_active_area_for_seed(data,i) for i in range(1,n+1)]
    total_area=max(sum(areas),1e-12)
    total_perm=q0*target_r
    # Equal-flux first approximation: stage production is proportional to area.
    # Re-normalize progressively so no provisional stage removes an impossible
    # fraction of the remaining feed.
    qin=q0; remaining_perm=total_perm; remaining_area=total_area
    stage_pi={}; stage_qin={}; stage_tds={}
    for i,area in enumerate(areas,1):
        stage_qin[i]=qin
        tds=feed_tds*q0/max(qin,1e-12)  # near-total salt rejection is sufficient for a seed
        stage_tds[i]=tds
        stage_pi[i]=float(_osmotic_for_concentration(tds,temp,feed_tds,None)["osmotic_bar"])
        if i<n:
            share=remaining_perm*area/max(remaining_area,1e-12)
            # The seed is only a predictor; keep its provisional stage recovery
            # away from singular concentration factors.
            qp=max(0.0,min(share,0.78*qin))
        else:
            qp=max(0.0,min(remaining_perm,0.78*qin))
        qin=max(qin-qp,0.02*q0)
        remaining_perm=max(0.0,remaining_perm-qp)
        remaining_area=max(0.0,remaining_area-area)

    seeds={}; anchors={}; anchor_stage=1; anchor_pi=stage_pi.get(1,0.0)
    # The HPP is the first hydraulic-energy anchor.  Every non-Nothing device
    # resets the anchor after its pressure input, even if its final pressure is
    # later refined by the nonlinear controller.
    for i in range(2,n+1):
        current_pi=stage_pi.get(i,anchor_pi)
        if i in adjustable:
            seeds[i]=max(0.0,current_pi-anchor_pi)
            anchors[i]=anchor_stage
        if _interstage_equipment(data,i)!="none":
            anchor_stage=i; anchor_pi=current_pi

    return {"boost_seed_bar":seeds,"stage_feed_osmotic_bar":stage_pi,
            "stage_feed_tds_mg_l":stage_tds,"energy_anchor_stage":anchors,
            "basis":"delta osmotic pressure since last hydraulic-energy input"}

def _solve_interstage_control(data):
    """Resolve non-manual interstage pressure targets without changing process physics.

    The unknowns are the controllable interstage pressure increases.  Flux and
    polarization modes equalize either the lead-element value or the stage-average
    value across all stages.  Target-recovery mode solves the requested downstream
    stage recoveries.  Finite-difference Newton steps are bounded and backtracked;
    intermediate evaluations temporarily allocate the same pressure via pumps so
    turbo energy sufficiency cannot hide the membrane/hydraulic root.
    """
    objective=_interstage_control_mode(data)
    if objective == "manual": return dict(data), {}
    n=_multistage_count(data); pu=data.get("pressure_unit","bar")
    adjustable=[i for i in range(2,n+1) if _interstage_equipment(data,i)!="none"]
    if not adjustable:
        raise ValueError("The selected interstage control objective requires at least one controllable interstage device.")
    basis=_interstage_balance_basis(data)
    if objective in {"balance_flux","balance_polarization"} and len(adjustable) != n-1:
        raise ValueError("Balancing flux or polarization across all stages requires a controllable pump/turbo device between every membrane stage.")
    if objective == "target_recovery":
        targets=[]
        for i in adjustable:
            raw=_float(data,f"interstage_target_recovery_{i}",None)
            if raw is None:
                raise ValueError(f"Enter the target Stage {i} recovery before using target-recovery interstage control.")
            t=raw/100.0 if raw>1 else raw
            if not 0.01 < t < 0.90:
                raise ValueError(f"Stage {i} target recovery must be between 1% and 90%.")
            targets.append(t)
    else:
        targets=None

    seed_info=_interstage_osmotic_boost_seeds(data, adjustable)
    seed_map=seed_info.get("boost_seed_bar",{})
    # Auto-select seed semantics:
    #   entered boost > 0 bar -> engineer's desired boost is the primary seed;
    #   entered boost = 0 bar -> no user bias, use the physics-based osmotic-rise seed.
    # The entered value is never a fixed constraint in a non-manual control mode.
    # If an entered positive seed proves poor, the bounded solver can still move freely.
    user_seed_map={}
    seed_source={}
    x=[]
    for i in adjustable:
        entered=float(_interstage_boost_bar(data,i,pu))
        user_seed_map[i]=entered
        osmotic=float(seed_map.get(i,0.0) or 0.0)
        if entered > 1e-9:
            chosen=entered
            seed_source[i]="user desired boost"
        elif osmotic > 0.0:
            chosen=osmotic
            seed_source[i]="automatic osmotic-rise seed (0 bar = auto)"
        else:
            chosen=0.0
            seed_source[i]="zero fallback; osmotic predictor unavailable"
        x.append(chosen)
    max_boost=max(5.0,float(data.get("interstage_control_max_boost_bar",40.0) or 40.0))
    x=[min(max(v,0.0),max_boost) for v in x]
    initial_seed=list(x)
    tol = 0.05 if objective=="balance_flux" else (0.002 if objective=="balance_polarization" else 0.0015)
    evals=0

    def evaluate(vec):
        nonlocal evals
        trial=dict(data); trial["_interstage_control_resolved"]=True; trial["_solver_fast"]=True
        for pos,val in zip(adjustable,vec):
            trial[f"interstage_boost_{pos}"]=pressure_from_bar(float(val),pu)
            # The membrane boundary only depends on pressure increase.  During
            # root finding use an electric booster so turbo-pool insufficiency
            # does not invalidate an otherwise valid hydraulic root.
            trial[f"interstage_equipment_{pos}"]="pump"
        r=_multistage_base(trial); evals+=1
        if objective in {"balance_flux","balance_polarization"}:
            metrics=[_stage_balance_metric(r,i,objective,basis) for i in range(1,n+1)]
            residual=[metrics[i]-metrics[0] for i in range(1,n)]
        else:
            metrics=[float(r[f"stage{i}_recovery"]) for i in adjustable]
            residual=[m-t for m,t in zip(metrics,targets)]
        return r, residual, metrics

    best_r,best_res,best_metrics=evaluate(x)
    def merit(res): return math.sqrt(sum(v*v for v in res))
    best_merit=merit(best_res); iterations=0; fallback=False
    for iterations in range(1,9):
        if max((abs(v) for v in best_res), default=0.0) <= tol: break
        m=len(x); J=[[0.0]*m for _ in range(m)]
        for j in range(m):
            h=max(0.15,0.02*max(1.0,abs(x[j])))
            xp=list(x); xp[j]=min(max_boost,x[j]+h)
            if abs(xp[j]-x[j])<1e-9:
                xp[j]=max(0.0,x[j]-h)
            _,rp,_=evaluate(xp); den=xp[j]-x[j]
            if abs(den)<1e-12: raise ValueError("Interstage control could not form a finite-difference step.")
            for i in range(m): J[i][j]=(rp[i]-best_res[i])/den
        try:
            dx=_small_linear_solve(J,[-v for v in best_res])
        except ValueError:
            fallback=True
            dx=[-math.copysign(min(1.0,max(0.25,abs(v)*2.0)),v) if abs(v)>tol else 0.0 for v in best_res]
        # Bound an individual Newton correction to 6 bar per iteration.
        dx=[max(-6.0,min(6.0,v)) for v in dx]
        accepted=False; step=1.0
        while step>=1/32:
            cand=[min(max_boost,max(0.0,a+step*d)) for a,d in zip(x,dx)]
            rr,res,metrics=evaluate(cand); mm=merit(res)
            if mm < best_merit*(1-1e-4*step) or mm <= tol:
                x,best_r,best_res,best_metrics,best_merit=cand,rr,res,metrics,mm; accepted=True; break
            step*=0.5
        if not accepted:
            fallback=True
            # Conservative coordinate search around the best state.
            found=False
            for j in range(len(x)):
                for sign in (-1.0,1.0):
                    cand=list(x); cand[j]=min(max_boost,max(0.0,x[j]+sign*0.5))
                    rr,res,metrics=evaluate(cand); mm=merit(res)
                    if mm < best_merit:
                        x,best_r,best_res,best_metrics,best_merit=cand,rr,res,metrics,mm; found=True; break
                if found: break
            if not found: break
    if max((abs(v) for v in best_res), default=0.0) > max(tol*3,0.01 if objective=="balance_flux" else 0.005):
        raise ValueError("Interstage control objective did not converge within the bounded pressure range. Review stage array sizing, recovery targets or the selected control objective.")
    resolved=dict(data); resolved["_interstage_control_resolved"]=True
    for pos,val in zip(adjustable,x): resolved[f"interstage_boost_{pos}"]=pressure_from_bar(val,pu)
    meta={
        "interstage_control_objective":objective, "interstage_control_balance_basis":basis,
        "interstage_control_iterations":iterations, "interstage_control_evaluations":evals,
        "interstage_control_residual":best_merit, "interstage_control_fallback_used":fallback,
        "interstage_control_method":"osmotic-rise seed + bounded finite-difference Newton + backtracking",
        "interstage_control_seed_basis":seed_info.get("basis"),
        "interstage_control_seed_boost_bar":{str(pos):float(val) for pos,val in zip(adjustable,initial_seed)},
        "interstage_control_user_seed_boost_bar":{str(pos):float(user_seed_map.get(pos,0.0)) for pos in adjustable},
        "interstage_control_seed_source":{str(pos):seed_source.get(pos,"") for pos in adjustable},
        "interstage_control_zero_seed_means_auto":True,
        "interstage_control_seed_stage_feed_osmotic_bar":seed_info.get("stage_feed_osmotic_bar",{}),
        "interstage_control_seed_energy_anchor_stage":seed_info.get("energy_anchor_stage",{}),
    }
    if objective in {"balance_flux","balance_polarization"}: meta["interstage_control_stage_metrics"]=best_metrics
    for pos,val in zip(adjustable,x): meta[f"interstage_control_boost_bar_{pos}"]=val
    return resolved, meta

def _select_generic_px_bank(q_total_m3h, min_unit_m3h, max_unit_m3h, requested_qty=1, auto=True):
    q=max(0.0,float(q_total_m3h)); qmin=max(0.0,float(min_unit_m3h or 0.0)); qmax=max(0.0,float(max_unit_m3h or 0.0))
    requested=max(1,int(float(requested_qty or 1)))
    if auto and qmax>0:
        qty=max(1,int(math.ceil(q/qmax)))
        # Prefer the largest operating count that remains above the minimum;
        # this reduces unit loading without violating turndown.
        feasible=[k for k in range(1,qty+1) if q/k<=qmax+1e-9 and (qmin<=0 or q/k>=qmin-1e-9)]
        if feasible: qty=max(feasible)
    else:
        qty=requested
    unit=q/max(qty,1)
    within=(qmax<=0 or unit<=qmax+1e-9) and (qmin<=0 or unit>=qmin-1e-9)
    return qty,unit,within


def _select_legacy_px_bank(q_total_m3h, model, requested_qty=1, auto=True):
    """Size a fixed isobaric chamber model bank and report whether an integer count is feasible.

    Automatic sizing chooses the minimum operating count required by the model's
    maximum unit-flow limit.  It then checks the minimum unit-flow limit.  When
    total IC branch flow is below the one-unit minimum, adding more units can
    only reduce unit flow, so one operating unit is retained and the bank is
    explicitly marked infeasible rather than implying that auto-sizing failed.
    """
    if model not in PX_LEGACY_MODELS:
        raise ValueError(f"Unknown isobaric chamber model: {model}")
    q=max(0.0,float(q_total_m3h))
    spec=PX_LEGACY_MODELS[model]
    qmin=flow_to_m3h(spec["allow_min_gpm"],"gpm")
    qmax=flow_to_m3h(spec["max_gpm"],"gpm")
    requested=max(1,int(float(requested_qty or 1)))
    if auto:
        qty=max(1,int(math.ceil(q/max(qmax,1e-12))))
    else:
        qty=requested
    unit=q/max(qty,1)
    within=(unit>=qmin-1e-9) and (unit<=qmax+1e-9)
    if within:
        reason="automatic IC model bank sizing" if auto else "manual IC model bank quantity"
    elif auto and q<qmin-1e-9:
        reason=(f"No feasible operating-unit count for {model}: total IC branch flow is below the one-unit minimum. "
                "One unit is retained because adding units would reduce flow per unit further.")
    elif auto:
        reason=(f"No feasible integer operating-unit count for {model} satisfies both minimum and maximum unit-flow limits at this duty.")
    else:
        reason="manual IC model bank quantity is outside the selected model flow envelope"
    return qty,unit,within,qmin,qmax,reason


def _resolve_single_manual_max_turbo(data):
    """For one turbo-only interstage location, solve the maximum recoverable boost.

    This is intentionally limited to an unambiguous single turbo position.
    Multiple turbo positions share one final-reject energy pool and therefore
    continue to use the selected global control objective / requested boosts.
    """
    if _interstage_control_mode(data) != "manual" or _bool(data,"_manual_turbo_max_resolved",False):
        return dict(data), {}
    n=_multistage_count(data); positions=[]
    for i in range(2,n+1):
        if _interstage_equipment(data,i) in {"turbo","turbo_pump"} and _bool(data,f"interstage_maximize_turbo_energy_{i}",False): positions.append(i)
    if len(positions)!=1: return dict(data), {}
    pos=positions[0]; pu=data.get("pressure_unit","bar"); eq=_interstage_equipment(data,pos); requested_boost=max(0.0,_interstage_boost_bar(data,pos,pu)); boost=requested_boost; iters=0
    for iters in range(1,8):
        trial=dict(data); trial["_manual_turbo_max_resolved"]=True; trial["_solver_fast"]=True
        trial[f"interstage_boost_{pos}"]=pressure_from_bar(boost,pu); trial[f"interstage_equipment_{pos}"]="pump"
        r=_multistage_base(trial)
        # Result flows are displayed in the same requested unit; convert explicitly.
        qtr=flow_to_m3h(float(r["reject_flow_final"]), data.get("flow_unit","m3/h"))
        qpf=flow_to_m3h(float(r[f"reject_flow_{pos-1}"]), data.get("flow_unit","m3/h"))
        rr=_enforce_turbo_reject_ratio(qtr,qpf,f"Stage {pos-1} → {pos} turbocharger")
        pfin=pressure_to_bar(float(r[f"reject_pressure_{n}"]),pu)
        back=pressure_to_bar(_float(data,"multistage_turbo_backpressure",1.5) or 1.5,pu)
        eta=max(0.05,min(0.95,float(data.get("multistage_turbo_efficiency",0.80) or 0.80)))
        avail_kw=qtr*max(0.0,pfin-back)/36.0*eta
        new_boost=avail_kw*36.0/max(qpf,1e-12)
        new_boost=max(0.0,min(40.0,new_boost))
        if abs(new_boost-boost)<0.05:
            boost=new_boost; break
        boost=0.55*boost+0.45*new_boost
    turbo_max_boost=boost
    total_boost = turbo_max_boost if eq=="turbo" else max(requested_boost,turbo_max_boost)
    resolved=dict(data); resolved["_manual_turbo_max_resolved"]=True; resolved[f"interstage_boost_{pos}"]=pressure_from_bar(total_boost,pu)
    return resolved,{"interstage_manual_max_turbo_stage":pos,"interstage_manual_max_turbo_boost_bar":turbo_max_boost,"interstage_manual_total_boost_bar":total_boost,"interstage_manual_requested_boost_bar":requested_boost,"interstage_manual_max_turbo_equipment":eq,"interstage_manual_max_turbo_iterations":iters}

# ---- v17.3 free single-to-multistage RO plant designer -----------------------------

def _multistage_count(data):
    raw = _float(data, "stage_count", 2)
    n = int(raw or 2)
    if n != raw or not (1 <= n <= 4):
        raise ValueError("RO Plant Designer supports 1, 2, 3 or 4 membrane stages.")
    return n


def _multistage_auto_basis(data):
    """Validate Auto Design inputs and return the coupled sizing basis.

    v0.19 sizes from the requested production and design flux first, then converts
    that active-area requirement into whole pressure vessels.  Hybrid vessels are
    handled position-by-position: the active area and hydraulic datasheet limits
    come from the actual membrane recipe loaded in each stage rather than from a
    single representative element.
    """
    d=dict(data); n=_multistage_count(d)
    if not _bool(d,"membrane_coupling",True):
        raise ValueError("Auto Design requires RO membrane coupling to be ON.")
    fu=d.get("flow_unit","m3/h")
    # Auto Design is plant-capacity driven. Feed flow and Stage-1 pressure are
    # outputs, not independent setpoints. The required plant production is split
    # across the operating trains, then the train feed is derived from recovery.
    target_r=_target_recovery_fraction_for_seed(d)
    if target_r is None or not 0<target_r<=0.95:
        raise ValueError("Auto Design recovery must be greater than 0 and no more than 95% for the initial array sizing pass.")
    operating_trains=max(1,int(round(_float(d,"operating_trains",1) or 1)))
    required_capacity_m3d=_float(d,"required_capacity_m3d",0.0) or 0.0
    if required_capacity_m3d<=0:
        raise ValueError("Required plant product capacity is mandatory and must be greater than zero for Auto Design.")
    train_product_m3h=required_capacity_m3d/(24.0*operating_trains)
    q0=train_product_m3h/target_r
    if q0<=0:
        raise ValueError("Auto Design could not derive a positive train feed flow from plant capacity and recovery.")
    d["solve_basis"]="recovery"
    d["target_recovery"]=target_r*100.0
    d["target_product_flow"]=flow_from_m3h(train_product_m3h,fu)
    d["feed_flow"]=flow_from_m3h(q0,fu)
    # Ignore any stale manual Stage-1 pressure carried by an older project. The
    # coupled membrane solver will calculate the minimum required pressure.
    d["membrane_pressure_1"]=""
    max_flux=float(d.get("max_design_flux_lmh",14.0) or 14.0)
    if not 4.0<=max_flux<=30.0:
        raise ValueError("Maximum design flux must be between 4 and 30 LMH.")
    epv=[]; area_per_vessel=[]; membrane_ids=[]; membrane_recipes=[]; membrane_records=[]; hydraulic_limits=[]
    temp=float(_float(d,"temperature_c",25.0) or 25.0)
    for i in range(1,n+1):
        mid=str(d.get(f"membrane_{i}") or "")
        if not mid: raise ValueError(f"Select a Stage {i} membrane before running Auto Design.")
        e=int(_float(d,f"elements_per_vessel_{i}",7) or 7)
        if not 1<=e<=8: raise ValueError(f"Stage {i} membranes per vessel must be from 1 to 8.")
        recipe=_normalize_membrane_recipe(mid,e,d.get(f"membrane_recipe_{i}"))
        records=[get_membrane(x) for x in recipe]
        areas=[float(mm.get("area_m2") or mm.get("active_area_m2") or 0.0) for mm in records]
        if any(a<=0 for a in areas):
            raise ValueError(f"Stage {i} membrane active area is unavailable for Auto Design.")

        def _flow_limit(record, keys):
            for key in keys:
                raw=record.get(key)
                if raw not in (None,""):
                    try:
                        value=float(raw)
                        if value>0: return value,"membrane catalog"
                    except (TypeError,ValueError):
                        pass
            diam=float(record.get("diameter_in") or 8.0)
            # Conservative hydraulic screening defaults used only when a verified
            # membrane-specific flow envelope is not cataloged.  They are not
            # represented as manufacturer guarantees and are exposed in results.
            if diam>=7.0:
                return (17.0 if keys[0].startswith("max") else 3.0),"8-inch screening default"
            if diam>=3.5:
                return (3.6 if keys[0].startswith("max") else 0.7),"4-inch screening default"
            scale=max(0.08,(diam/8.0)**2)
            return ((17.0 if keys[0].startswith("max") else 3.0)*scale),"diameter-scaled screening default"

        max_feed,max_feed_basis=_flow_limit(records[0],["max_feed_flow_m3h","max_feed_m3h","max_feed_flow"])
        min_tail,min_tail_basis=_flow_limit(records[-1],["min_concentrate_flow_m3h","min_reject_flow_m3h","min_concentrate_m3h"])
        max_dp_by_position=[float(mm.get("max_dp_per_element_bar",1.0) or 1.0) for mm in records]
        max_pressure=min(_membrane_pressure_limit_bar(mm,temp) for mm in records)
        hydraulic_limits.append({
            "max_first_element_feed_m3h":max_feed,
            "min_tail_concentrate_m3h":min_tail,
            "max_feed_basis":max_feed_basis,
            "min_tail_basis":min_tail_basis,
            "max_dp_by_position_bar":max_dp_by_position,
            "max_stage_feed_pressure_bar":max_pressure,
        })
        epv.append(e); area_per_vessel.append(sum(areas)); membrane_ids.append(mid)
        membrane_recipes.append(recipe); membrane_records.append(records)

    required_area=train_product_m3h*1000.0/max_flux
    feed_tds=max(0.0,_float(d,"feed_tds",_float(d,"analysis_tds",0.0)) or 0.0)
    source=str(d.get("source_water_type","") or "").lower()
    bw_context=(feed_tds<=15000.0 or source in {"well","surface","municipal_secondary"}) and source not in {"seawater","seawater_well"}
    max_element_flux=float(d.get("auto_max_element_flux_lmh") or max(max_flux*1.55,max_flux+4.0))
    max_tail_beta=float(d.get("auto_max_tail_beta") or 1.20)
    if max_element_flux<max_flux:
        max_element_flux=max_flux
    if not 1.01<=max_tail_beta<=2.0:
        raise ValueError("Auto Design maximum tail-element beta must be between 1.01 and 2.00.")
    return {"data":d,"n":n,"q0":q0,"target_r":target_r,"max_flux":max_flux,
            "required_capacity_m3d":required_capacity_m3d,"operating_trains":operating_trains,
            "train_product_m3h":train_product_m3h,
            "max_element_flux_lmh":max_element_flux,"max_tail_beta":max_tail_beta,
            "required_area_m2":required_area,"epv":epv,"area_per_vessel":area_per_vessel,
            "membrane_ids":membrane_ids,"membrane_recipes":membrane_recipes,"membrane_records":membrane_records,
            "hydraulic_limits":hydraulic_limits,"bwro_tail_beta_priority":bool(bw_context)}

def _auto_array_ratio_seeds(n):
    """Established array-ratio seeds; ratios are starting geometries, not rules."""
    if n==1: return [("1:1",[1.0])]
    if n==2: return [("2:1",[2.0,1.0]),("3:2",[3.0,2.0])]
    if n==3: return [("3:2:1",[3.0,2.0,1.0]),("4:2:1",[4.0,2.0,1.0]),
                     ("35:20:10",[35.0,20.0,10.0])]
    return [("4:3:2:1",[4.0,3.0,2.0,1.0])]


def _auto_counts_from_ratio(basis, ratio, area_factor=1.0):
    target=basis["required_area_m2"]*min(2.0,max(0.75,float(area_factor)))
    denom=sum(float(r)*a for r,a in zip(ratio,basis["area_per_vessel"]))
    scale=target/max(denom,1e-12)
    return [max(1,int(math.ceil(scale*float(r)))) for r in ratio]


def _auto_equal_recovery_counts(basis):
    n=basis["n"]; qin=basis["q0"]
    stage_r=1.0-(1.0-basis["target_r"])**(1.0/n)
    counts=[]
    for i in range(n):
        qp=qin*stage_r
        area=qp*1000.0/basis["max_flux"]
        counts.append(max(1,int(math.ceil(area/basis["area_per_vessel"][i]))))
        qin*=1.0-stage_r
    return counts


def _auto_tree_counts(counts):
    """Return whole-vessel counts that monotonically narrow downstream.

    A user ratio is only a starting shape.  If integer rounding or local search
    creates a downstream stage wider than its upstream stage, grow the upstream
    stage(s) rather than shrinking downstream crossflow capacity.
    """
    out=[max(1,int(round(float(v)))) for v in counts]
    for i in range(len(out)-2,-1,-1):
        if out[i] < out[i+1]: out[i]=out[i+1]
    return out


def _auto_provisional_stage_duties(basis, counts):
    """Cheap hydraulic duty estimate used before the membrane pressure solver.

    The requested product is apportioned at a common provisional flux over the
    actual active area in each candidate stage.  This is deliberately a
    screening approximation: candidates that pass are still checked by the full
    element-by-element membrane model before they can be selected.
    """
    counts=_auto_tree_counts(counts)
    stage_areas=[counts[i]*basis["area_per_vessel"][i] for i in range(basis["n"])]
    total_area=max(sum(stage_areas),1e-12)
    target_product=basis["q0"]*basis["target_r"]
    provisional_flux=target_product*1000.0/total_area
    qin=basis["q0"]; rows=[]
    for i in range(basis["n"]):
        qp=min(stage_areas[i]*provisional_flux/1000.0, qin*0.90)
        qout=max(qin-qp,qin*1e-9)
        vessels=counts[i]; epv=basis["epv"][i]
        vessel_feed=qin/max(vessels,1)
        vessel_reject=qout/max(vessels,1)
        # Equivalent uniform element recovery is adequate for a prefilter beta
        # estimate.  The full solver later uses the true element profile.
        element_factor=(max(vessel_reject,1e-12)/max(vessel_feed,1e-12))**(1.0/max(epv,1))
        element_recovery=max(0.0,min(0.95,1.0-element_factor))
        beta_est=math.exp(0.7*element_recovery)
        rows.append({
            "stage":i+1,"qin_m3h":qin,"qp_m3h":qp,"qout_m3h":qout,
            "area_m2":stage_areas[i],"avg_flux_lmh":qp*1000.0/max(stage_areas[i],1e-12),
            "vessel_feed_m3h":vessel_feed,"vessel_reject_m3h":vessel_reject,
            "tail_beta_estimate":beta_est,
        })
        qin=qout
    return rows


def _auto_early_feasibility(candidate,basis):
    """Reject obviously impossible tree arrays before a pressure convergence run."""
    counts=[int(candidate[f"vessels_{i}"]) for i in range(1,basis["n"]+1)]
    reasons=[]; diag=[]
    if counts != _auto_tree_counts(counts):
        reasons.append("pressure-vessel array does not narrow monotonically downstream")
    area=sum(counts[i]*basis["area_per_vessel"][i] for i in range(basis["n"]))
    if area < basis["required_area_m2"]*0.985:
        reasons.append(f"active membrane area {area:.0f} m² is below the {basis['required_area_m2']:.0f} m² design-flux requirement")
    duties=_auto_provisional_stage_duties(basis,counts)
    for i,row in enumerate(duties):
        lim=basis["hydraulic_limits"][i]
        stage=i+1; stage_reasons=[]
        if row["vessel_feed_m3h"] > lim["max_first_element_feed_m3h"]*1.001:
            stage_reasons.append(
                f"first-element feed {row['vessel_feed_m3h']:.2f} m³/h exceeds {lim['max_first_element_feed_m3h']:.2f} m³/h"
            )
        if row["vessel_reject_m3h"] < lim["min_tail_concentrate_m3h"]*0.999:
            stage_reasons.append(
                f"tail concentrate {row['vessel_reject_m3h']:.2f} m³/h is below {lim['min_tail_concentrate_m3h']:.2f} m³/h"
            )
        if row["avg_flux_lmh"] > basis["max_flux"]*1.08:
            stage_reasons.append(
                f"provisional average flux {row['avg_flux_lmh']:.2f} LMH exceeds the {basis['max_flux']:.2f} LMH design target"
            )
        dp_fraction=0.0
        try:
            _,dps,_=clean_stage_pressure_drop(row["qin_m3h"],row["qout_m3h"],counts[i],basis["epv"][i])
            limits=lim["max_dp_by_position_bar"]
            dp_fraction=max((dp/max(float(limits[min(j,len(limits)-1)]),1e-12) for j,dp in enumerate(dps)),default=0.0)
            if dp_fraction>1.05:
                stage_reasons.append(f"clean pressure-drop estimate uses {dp_fraction*100:.0f}% of an element ΔP limit")
        except (ValueError,ZeroDivisionError):
            stage_reasons.append("clean pressure-drop estimate is not hydraulically valid")
        entered_pressure=_float(candidate,f"membrane_pressure_{stage}",None)
        if entered_pressure not in (None,""):
            try:
                pbar=pressure_to_bar(float(entered_pressure),candidate.get("pressure_unit","bar"))
                if pbar>lim["max_stage_feed_pressure_bar"]+1e-9:
                    stage_reasons.append(
                        f"entered feed pressure {pbar:.2f} bar exceeds membrane limit {lim['max_stage_feed_pressure_bar']:.2f} bar"
                    )
            except (TypeError,ValueError):
                pass
        if stage_reasons:
            reasons.extend([f"Stage {stage}: {x}" for x in stage_reasons])
        diag.append({**row,
            "max_first_element_feed_m3h":lim["max_first_element_feed_m3h"],
            "min_tail_concentrate_m3h":lim["min_tail_concentrate_m3h"],
            "feed_flow_limit_basis":lim["max_feed_basis"],"tail_flow_limit_basis":lim["min_tail_basis"],
            "estimated_dp_limit_fraction":dp_fraction,
        })
    return {"ok":not reasons,"reasons":reasons,"stages":diag,"area_m2":area}


def _auto_full_feasibility(result,basis):
    """Apply exact element-profile constraints after the detailed membrane solve."""
    reasons=[]; rows=[]
    counts=[int(round(float(result.get(f"stage{i}_pressure_vessels",0) or 0))) for i in range(1,basis["n"]+1)]
    if any(v<=0 for v in counts):
        counts=[int(round(float(result.get(f"auto_vessels_{i}",0) or 0))) for i in range(1,basis["n"]+1)]
    if counts and counts != _auto_tree_counts(counts):
        reasons.append("final pressure-vessel array does not narrow monotonically downstream")
    for i in range(1,basis["n"]+1):
        lim=basis["hydraulic_limits"][i-1]
        prof=result.get(f"stage{i}_element_profile") or []
        first_feed=float(prof[0].get("feed_flow_m3h",result.get(f"stage{i}_vessel_feed_flow",0.0)) or 0.0) if prof else float(result.get(f"stage{i}_vessel_feed_flow",0.0) or 0.0)
        tail_conc=float(prof[-1].get("reject_flow_m3h",result.get(f"stage{i}_vessel_reject_flow",0.0)) or 0.0) if prof else float(result.get(f"stage{i}_vessel_reject_flow",0.0) or 0.0)
        max_element_flux=max((float(e.get("flux_lmh",0.0) or 0.0) for e in prof),default=float(result.get(f"stage{i}_flux_lmh",0.0) or 0.0))
        tail_beta=float(prof[-1].get("polarization_factor",1.0) or 1.0) if prof else float(result.get(f"stage{i}_polarization_factor",1.0) or 1.0)
        avg_flux=float(result.get(f"stage{i}_flux_lmh",0.0) or 0.0)
        dp_fraction=float(result.get(f"stage{i}_dp_limit_fraction",0.0) or 0.0)
        feed_pressure=(float(prof[0].get("feed_pressure_bar",0.0) or 0.0) if prof else float(result.get(f"membrane_pressure_{i}",0.0) or 0.0))
        stage_reasons=[]
        if first_feed>lim["max_first_element_feed_m3h"]*1.001:
            stage_reasons.append(f"first-element feed {first_feed:.2f} m³/h exceeds {lim['max_first_element_feed_m3h']:.2f} m³/h")
        if tail_conc<lim["min_tail_concentrate_m3h"]*0.999:
            stage_reasons.append(f"tail concentrate {tail_conc:.2f} m³/h is below {lim['min_tail_concentrate_m3h']:.2f} m³/h")
        if avg_flux>basis["max_flux"]*1.005:
            stage_reasons.append(f"average flux {avg_flux:.2f} LMH exceeds {basis['max_flux']:.2f} LMH")
        if max_element_flux>basis["max_element_flux_lmh"]*1.005:
            stage_reasons.append(f"maximum element flux {max_element_flux:.2f} LMH exceeds screening limit {basis['max_element_flux_lmh']:.2f} LMH")
        if dp_fraction>1.001:
            stage_reasons.append(f"element pressure drop reaches {dp_fraction*100:.1f}% of datasheet limit")
        if tail_beta>basis["max_tail_beta"]*1.005:
            stage_reasons.append(f"tail beta {tail_beta:.3f} exceeds {basis['max_tail_beta']:.3f}")
        if feed_pressure>lim["max_stage_feed_pressure_bar"]+1e-6:
            stage_reasons.append(f"feed pressure {feed_pressure:.2f} bar exceeds membrane limit {lim['max_stage_feed_pressure_bar']:.2f} bar")
        reasons.extend([f"Stage {i}: {x}" for x in stage_reasons])
        rows.append({
            "stage":i,"first_element_feed_m3h":first_feed,"max_first_element_feed_m3h":lim["max_first_element_feed_m3h"],
            "tail_concentrate_m3h":tail_conc,"min_tail_concentrate_m3h":lim["min_tail_concentrate_m3h"],
            "max_element_flux_lmh":max_element_flux,"avg_flux_lmh":avg_flux,"tail_beta":tail_beta,
            "dp_limit_fraction":dp_fraction,"feed_pressure_bar":feed_pressure,"max_feed_pressure_bar":lim["max_stage_feed_pressure_bar"],
            "feed_flow_limit_basis":lim["max_feed_basis"],"tail_flow_limit_basis":lim["min_tail_basis"],
        })
    return {"ok":not reasons,"reasons":reasons,"stages":rows}


def _multistage_auto_candidates(data):
    """Build a compact set of physically credible array seeds for coupled solving."""
    basis=_multistage_auto_basis(data); d=basis["data"]; n=basis["n"]
    raw=[]
    # Include the historic equal-stage-recovery area allocation as a neutral seed.
    raw.append(("equal-stage-recovery",_auto_equal_recovery_counts(basis)))
    for label,ratio in _auto_array_ratio_seeds(n):
        # Nominal area and a modest guard candidate.  The final solver grows any
        # stage that still violates the selected maximum average flux.
        for factor in (1.00,1.06):
            raw.append((label if factor==1 else f"{label} +6% area guard",_auto_counts_from_ratio(basis,ratio,factor)))
    # Preserve a sensible existing array as another seed when the user is refining
    # a previously solved Auto Design rather than starting from blank fields.
    existing=[max(1,int(round(_float(d,f"vessels_{i}",1) or 1))) for i in range(1,n+1)]
    if sum(existing)>n: raw.append(("existing editable array",existing))

    seen=set(); candidates=[]
    for label,counts in raw:
        counts=_auto_tree_counts(counts)
        key=tuple(counts)
        if key in seen: continue
        seen.add(key); c=dict(d)
        for i,v in enumerate(counts,1): c[f"vessels_{i}"]=int(v)
        c["_auto_seed_ratio_label"]=label
        candidates.append(c)
    return candidates,basis


def _multistage_auto_recovery_candidates(data,basis,exclude=None):
    """Generate wider tree arrays when the nominal Auto Design seeds cannot solve.

    This is the recovery path for errors such as “requested permeate flow is
    outside the solvable range at the current configuration.”  It deliberately
    changes membrane surface area and pressure-vessel distribution together.
    """
    d=dict(basis.get("data") or data); exclude=set(exclude or ()); raw=[]
    factors=(1.00,1.08,1.16,1.28,1.42,1.60)
    # Keep the equal-stage-recovery family in the recovery search as well, then
    # add the user-specified tree/funnel seed families with progressively more
    # active area.
    eq=_auto_tree_counts(_auto_equal_recovery_counts(basis))
    for factor in factors:
        if factor==1.0: counts=eq
        else: counts=_auto_tree_counts([max(1,int(math.ceil(v*factor))) for v in eq])
        raw.append((f"recovery search · equal-stage-recovery · {factor*100:.0f}% area",counts))
    for label,ratio in _auto_array_ratio_seeds(basis["n"]):
        for factor in factors:
            raw.append((f"recovery search · {label} · {factor*100:.0f}% area",_auto_tree_counts(_auto_counts_from_ratio(basis,ratio,factor))))
    seen=set(exclude); out=[]
    for label,counts in raw:
        key=tuple(counts)
        if key in seen: continue
        seen.add(key); c=dict(d)
        for i,v in enumerate(counts,1): c[f"vessels_{i}"]=int(v)
        c["_auto_seed_ratio_label"]=label
        out.append(c)
    return out


def _auto_design_metrics(result,basis):
    n=basis["n"]; flux=[]; tails=[]
    for i in range(1,n+1):
        flux.append(float(result.get(f"stage{i}_flux_lmh",0.0) or 0.0))
        prof=result.get(f"stage{i}_element_profile") or []
        tails.append(float(prof[-1].get("polarization_factor",1.0)) if prof else float(result.get(f"stage{i}_polarization_factor",1.0) or 1.0))
    max_flux=max(flux or [0.0]); flux_excess=max(0.0,max_flux/basis["max_flux"]-1.0)
    area=float(result.get("total_membrane_area_m2",0.0) or 0.0)
    area_ratio=area/max(basis["required_area_m2"],1e-12)
    beta_max=max(tails or [1.0]); beta_spread=max(tails or [1.0])-min(tails or [1.0])
    flux_spread=max(flux or [0.0])-min(flux or [0.0])
    sec=float(result.get("total_sec",1e6) or 1e6)
    if basis["bwro_tail_beta_priority"]:
        # BWRO selection is explicitly tail-beta driven after satisfying the
        # maximum-flux constraint.  A small area guard prevents unconstrained
        # oversizing from winning solely by lowering beta.
        merit=beta_max + 0.08*max(0.0,area_ratio-1.0) + 0.01*beta_spread + 0.002*sec
    else:
        merit=max(0.0,area_ratio-1.0) + 0.015*flux_spread + 0.002*sec
    return {"fluxes":flux,"tail_betas":tails,"max_flux_lmh":max_flux,"flux_excess":flux_excess,
            "area_m2":area,"area_ratio":area_ratio,"tail_beta_max":beta_max,"tail_beta_spread":beta_spread,
            "flux_spread_lmh":flux_spread,"total_sec":sec,"merit":merit,
            "feasible_flux":flux_excess<=0.005}


def _auto_candidate_sort_key(row,basis):
    m=row["metrics"]
    # A flux-compliant candidate always outranks a violating one.  Within the
    # feasible set BWRO uses beta-driven merit; other waters favor compact area.
    return (0 if m["feasible_flux"] else 1, m["flux_excess"], m["merit"], m["area_ratio"], m["total_sec"])


def _screen_auto_candidate(candidate,basis):
    raise_if_cancelled()
    early=_auto_early_feasibility(candidate,basis)
    if not early["ok"]:
        return {"input":candidate,"result":None,"metrics":None,
                "error":"Hydraulic prefilter rejected array: "+"; ".join(early["reasons"][:4]),
                "early_rejected":True,"early_feasibility":early,"full_feasibility":None}
    trial=dict(candidate); trial["_solver_fast"]=True
    # Auto Design screening must remain a fixed-array calculation.  The candidate
    # already contains the vessel counts being evaluated; pressure-root workers
    # must not recursively enter Auto Design again.  The flag also permits the
    # inverse solver to use a narrower screening bracket and retain fast/report-
    # suppressed chemistry until the one authoritative final calculation.
    trial["_auto_candidate_screen"]=True
    try:
        r=_with_tridirectional_solve(trial,_multistage_base)
        raise_if_cancelled()
        full=_auto_full_feasibility(r,basis)
        if not full["ok"]:
            return {"input":candidate,"result":None,"metrics":None,
                    "error":"Detailed hydraulic feasibility rejected array: "+"; ".join(full["reasons"][:4]),
                    "early_rejected":False,"early_feasibility":early,"full_feasibility":full}
        return {"input":candidate,"result":r,"metrics":_auto_design_metrics(r,basis),"error":None,
                "early_rejected":False,"early_feasibility":early,"full_feasibility":full}
    except (KeyError,ValueError,ZeroDivisionError) as exc:
        return {"input":candidate,"result":None,"metrics":None,"error":str(exc),
                "early_rejected":False,"early_feasibility":early,"full_feasibility":None}


def _multistage_autosize(data):
    """Compatibility entry: return the best *seed* array plus sizing metadata.

    v18.3.8 performs the actual joint array/boost optimization in
    ``_multistage_core``.  This function remains available to callers/tests that
    expect the historic two-value interface.
    """
    d=dict(data)
    if str(d.get("design_mode","manual")).lower()!="auto": return d,[]
    candidates,basis=_multistage_auto_candidates(d)
    chosen=candidates[0]
    sizing=[]
    for i in range(1,basis["n"]+1):
        vessels=int(chosen[f"vessels_{i}"]); epv=basis["epv"][i-1]
        sizing.append({"stage":i,"max_design_flux_lmh":basis["max_flux"],"elements_per_vessel":epv,
                       "pressure_vessels":vessels,"total_elements":vessels*epv,
                       "seed_ratio":chosen.get("_auto_seed_ratio_label")})
    return chosen,sizing


def _multistage_base(data):
    """Sequential 1-4 stage membrane-train design with stage-specific membranes.

    Stage n+1 receives the actual calculated Stage n concentrate flow, ionic
    composition, TA/CT state and reject pressure plus an optional booster ΔP.
    This is deliberately a membrane-plant calculation; ERD-specific energy
    transfer remains in the dedicated Turbo / Isobaric / BiTurbo workspaces.
    """
    if not _bool(data, "membrane_coupling", True):
        raise ValueError("RO Plant Designer requires RO membrane coupling to be ON.")
    n = _multistage_count(data)
    if not _bool(data, "_interstage_control_resolved", False) and _interstage_control_mode(data) != "manual":
        resolved, control_meta = _solve_interstage_control(data)
        final = _multistage_base(resolved)
        final.update(control_meta)
        return final
    if not _bool(data,"_manual_turbo_max_resolved",False) and _interstage_control_mode(data)=="manual":
        resolved, max_meta = _resolve_single_manual_max_turbo(data)
        if max_meta:
            final=_multistage_base(resolved); final.update(max_meta); return final
    fu, pu, getf, getp = common(data)
    q0 = getf("feed_flow")
    p1 = getp("membrane_pressure_1")
    if q0 <= 0:
        raise ValueError("Feed flow must be greater than zero.")
    suction = getp("suction_pressure")
    pret_p = getp("pretreatment_discharge_pressure")
    pp1_raw = _float(data, "permeate_pressure_1", None)
    if pp1_raw is None:
        pp1_raw = _float(data, "permeate_pressure", 0.0)
    pp = pressure_to_bar(pp1_raw, pu)
    if p1 <= pp:
        raise ValueError("Stage 1 feed pressure must be above permeate backpressure.")

    stages = []
    qin, pin = q0, p1
    feed_tds = _float(data, "feed_tds", 35000.0)
    feed_comp = None
    feed_carbon = None
    total_perm = 0.0
    for i in range(1, n + 1):
        raise_if_cancelled()
        if i > 1:
            boost = _interstage_boost_bar(data, i, pu)
            pin = stages[-1]["reject_pressure_bar"] + boost
            qin = stages[-1]["reject_flow"]
            feed_tds = stages[-1]["concentrate_tds_ppm"]
            feed_comp = stages[-1].get("concentrate_composition_mg_l")
            if stages[-1].get("concentrate_total_alkalinity_mol_kg") is not None:
                feed_carbon = {
                    "total_alkalinity_mol_kg": stages[-1]["concentrate_total_alkalinity_mol_kg"],
                    "total_inorganic_carbon_mol_kg": stages[-1]["concentrate_total_inorganic_carbon_mol_kg"],
                }
        st = _stage_from_data(data, i, qin, pin, feed_tds, feed_comp, feed_carbon)
        stages.append(st)
        total_perm += st["permeate_flow"]

    qreject = stages[-1]["reject_flow"]
    recovery = total_perm / q0
    if total_perm <= 0 or recovery <= 0 or recovery >= 0.95:
        raise ValueError("The multistage membrane calculation produced an invalid overall recovery.")

    # Gross train pumping energy: HPP plus any interstage booster pumps.
    peff = float(data.get("pump_eff", 0.85)); meff = float(data.get("motor_eff", 0.97))
    veff = _vfd_eff(data, "vfd_eff", "pump_no_vfd")
    hpp_dp = p1 - suction
    if hpp_dp <= 0:
        raise ValueError("HP pump discharge pressure must be above its inlet pressure.")
    # New v0.19 pump database path: when the Plant Design pump-curve basis is
    # VCMP auto, use the selected real 60 Hz regression + affinity-law VFD
    # efficiency. If no single VCMP curve covers the duty, preserve the entered
    # pump efficiency as a fallback.
    feed_density_kg_m3 = 1000.0 * solution_specific_gravity(float(stages[0].get("feed_tds_ppm", feed_tds) or feed_tds), _float(data,"temperature_c",25.0))
    static_dp = max(0.0, float(stages[0].get("feed_osmotic_bar",0.0)) + pp - suction)
    pump_curve = _pump_curve_screening(data, q0, hpp_dp, static_dp, peff, meff, veff, feed_density_kg_m3)
    if pump_curve.get("pump_curve_source") == "vcmp_database" and pump_curve.get("pump_operating_status") == "ok":
        peff = float(pump_curve["pump_operating_efficiency"])
        hpp_kw = float(pump_curve["pump_operating_wire_kw"])
    else:
        hpp_kw = _pump_wire_power_kw(q0, hpp_dp, peff, meff, veff)
    booster_eff = float(data.get("booster_pump_eff", peff)); booster_motor = float(data.get("booster_motor_eff", meff))
    booster_vfd = _vfd_eff(data, "booster_vfd_eff", "booster_no_vfd")
    booster_kw = 0.0
    for i in range(2, n + 1):
        boost = _interstage_boost_bar(data, i, pu)
        q_stage = stages[i-2]["reject_flow"]
        # Electrical allocation is completed below after the final-brine hydraulic
        # energy pool is known.  Keep the legacy all-pump value for comparison.
        booster_kw += _pump_wire_power_kw(q_stage, boost, booster_eff, booster_motor, booster_vfd)

    # Generalized interstage equipment allocation.  Requested boost sets the
    # hydraulic stage boundary; its source can be a pump, turbocharger, or a
    # turbocharger supplemented by a booster pump.  Turbo hydraulic energy is
    # drawn from one common final-brine pool so multiple interstage turbines do
    # not double-count the same reject energy.
    final_reject_pressure = float(stages[-1]["reject_pressure_bar"])
    turbo_backpressure = pressure_to_bar(_float(data, "multistage_turbo_backpressure", 1.5) or 1.5, pu)
    turbo_eta = max(0.05, min(0.95, float(data.get("multistage_turbo_efficiency", 0.80) or 0.80)))
    gross_reject_hydraulic_kw = qreject * max(0.0, final_reject_pressure - turbo_backpressure) / 36.0
    turbo_pool_kw = gross_reject_hydraulic_kw * turbo_eta
    turbo_pool_initial_kw = turbo_pool_kw
    actual_booster_kw = 0.0
    interstage_energy = []
    for i in range(n, 1, -1):
        eq = _interstage_equipment(data, i)
        boost = _interstage_boost_bar(data, i, pu)
        q_stage = float(stages[i-2]["reject_flow"])
        required_hyd_kw = q_stage * boost / 36.0
        turbo_hyd_kw = 0.0
        pump_hyd_kw = required_hyd_kw
        downstream_recovery = float(stages[i-1]["recovery"])
        # Canonical turbocharger nomenclature: Qtr is the final reject/brine flow
        # through the turbine side and Qpf is the flow being boosted on the pump
        # side at this interstage location.  Do not substitute stage recovery for
        # this ratio: multistage arrangements can have materially different Qtr/Qpf.
        q_pump_side = q_stage
        q_turbine_side = float(qreject)
        reject_ratio = turbo_reject_ratio(q_turbine_side, q_pump_side)
        suitability = turbo_reject_ratio_status(reject_ratio)
        pump_side_tds = float(stages[i-1].get("feed_tds_ppm", 0.0) or 0.0)
        if eq in {"turbo", "turbo_pump"} and required_hyd_kw > 0:
            _enforce_turbo_reject_ratio(q_turbine_side, q_pump_side, f"Stage {i-1} → {i} turbocharger")
            turbo_hyd_kw = min(required_hyd_kw, turbo_pool_kw)
            turbo_pool_kw -= turbo_hyd_kw
            pump_hyd_kw = required_hyd_kw - turbo_hyd_kw
            if eq == "turbo" and pump_hyd_kw > max(0.25, 0.005*required_hyd_kw):
                raise ValueError(
                    f"Stage {i} turbocharger has insufficient reject hydraulic energy for the requested {boost:.2f} bar boost. "
                    "Select Turbo + Booster Pump, reduce the boost/recovery, or revise the stage split."
                )
        if eq == "none":
            pump_hyd_kw = 0.0; turbo_hyd_kw = 0.0
        if eq == "pump":
            pump_hyd_kw = required_hyd_kw
        booster_sel = None
        pump_dp_required = (pump_hyd_kw * 36.0 / q_stage) if q_stage > 1e-12 else 0.0
        if pump_hyd_kw > 1e-12 and str(data.get("pump_curve_basis","auto")).lower() in {"vcmp","vcmp_auto","database"}:
            booster_density = 1000.0 * solution_specific_gravity(pump_side_tds, _float(data,"temperature_c",25.0))
            vsel = select_vcmp_pump(
                q_stage, pump_dp_required, density_kg_m3=booster_density,
                motor_eff=booster_motor, vfd_eff=booster_vfd,
                min_vfd_hz=float(data.get("vcmp_min_vfd_hz",40.0) or 40.0),
                max_vfd_hz=float(data.get("vcmp_max_vfd_hz",60.0) or 60.0),
                flow_margin=float(data.get("vcmp_flow_margin",0.05) or 0.0),
                head_margin=float(data.get("vcmp_head_margin",0.05) or 0.0),
                reduced_impeller_penalty_pp=float(data.get("vcmp_reduced_impeller_eta_penalty_pp",2.0) or 0.0),
                low_speed_derate_pp_per_10pct=float(data.get("vcmp_low_speed_eta_derate_pp_per_10pct",0.0) or 0.0),
                reference_rpm_60=data.get("vcmp_reference_rpm_60") or None, top_n=5)
            if vsel.get("ok"):
                booster_sel = vsel["selected"]
        if booster_sel is not None:
            pump_wire_kw = float(booster_sel["wire_kw"])
        else:
            pump_wire_kw = pump_hyd_kw / max(booster_eff*booster_motor*booster_vfd, 1e-12)
        actual_booster_kw += pump_wire_kw
        item = {
            "stage": i, "equipment": eq, "boost_bar": boost, "flow_m3h": q_stage,
            "required_hydraulic_kw": required_hyd_kw, "turbo_hydraulic_kw": turbo_hyd_kw,
            "booster_hydraulic_kw": pump_hyd_kw, "booster_wire_kw": pump_wire_kw,
            "downstream_stage_recovery": downstream_recovery, "reject_ratio": reject_ratio,
            "turbo_pump_flow": q_pump_side, "turbo_turbine_flow": q_turbine_side,
            "turbo_pump_side_tds_mg_l": pump_side_tds,
            "turbo_suitability": suitability,
            "booster_pump_source": "vcmp_database" if booster_sel is not None else "manual_efficiency_fallback",
        }
        if booster_sel is not None:
            item.update({
                "booster_pump_family": booster_sel["product_family"],
                "booster_pump_stage_config": booster_sel["stage_config"],
                "booster_pump_frequency_hz": booster_sel["frequency_hz"],
                "booster_pump_efficiency": booster_sel["pump_efficiency"],
                "booster_pump_generated_dp_bar": booster_sel["actual_dp_bar"],
                "booster_pump_shaft_kw": booster_sel["shaft_kw"],
                "booster_pump_shaft_torque_nm": booster_sel.get("shaft_torque_nm"),
            })
        interstage_energy.append(item)
    booster_kw = actual_booster_kw

    pret_rec = float(data.get("pretreatment_recovery", 0.85))
    pret_peff = float(data.get("pretreatment_pump_eff", 0.82)); pret_meff = float(data.get("pretreatment_motor_eff", 0.95))
    pret_veff = _vfd_eff(data, "pretreatment_vfd_eff", "pretreatment_no_vfd")
    pret_kw = _pump_wire_power_kw(q0 / max(pret_rec, 1e-12), pret_p, pret_peff, pret_meff, pret_veff)
    ro_kw = hpp_kw + booster_kw

    result = {
        "membrane_coupling": True, "plant_designer": True, "stage_count": n,
        "design_mode": str(data.get("design_mode", "manual")).lower(),
        "feed_flow": q0, "product_flow": total_perm, "product_m3d": total_perm * 24.0,
        "recovery": recovery, "reject_flow_final": qreject,
        "membrane_pressure_1": p1, "suction_pressure": suction,
        "hpp_dp": hpp_dp, "hpp_flow": q0, "hpp_kw": hpp_kw,
        "hpp_electrical_power_kw": hpp_kw, "hpp_hydraulic_power_kw": max(0.0, q0 * hpp_dp / 36.0),
        "hpp_pump_efficiency_used": peff, "hpp_motor_efficiency_used": meff, "hpp_vfd_efficiency_used": veff,
        "feed_osmotic_pressure_bar": float(stages[0].get("feed_osmotic_bar", 0.0)),
        "final_concentrate_osmotic_pressure_bar": float(stages[-1].get("concentrate_osmotic_bar", 0.0)),
        "booster_kw": booster_kw, "electric_kw": ro_kw,
        "hydraulic_kw": max(0.0, q0 * hpp_dp / 36.0),
        "pretreatment_kw": pret_kw, "ro_sec": ro_kw / total_perm, "ro_gross_sec": ro_kw / total_perm,
        "pump_sec": ro_kw / total_perm, "pretreatment_sec": pret_kw / total_perm,
        "total_sec": (ro_kw + pret_kw) / total_perm,
        "total_pressure_vessels": sum(float(x["pressure_vessels"]) for x in stages),
        "total_membrane_elements": sum(float(x["membrane_elements"]) for x in stages),
        "total_membrane_area_m2": sum(float(x["membrane_total_area_m2"]) for x in stages),
    }
    result.update(pump_curve)
    result["multistage_turbo_available_hydraulic_kw"] = turbo_pool_initial_kw
    result["multistage_turbo_unused_hydraulic_kw"] = turbo_pool_kw
    result["multistage_reject_hydraulic_kw_gross"] = gross_reject_hydraulic_kw
    result["multistage_turbo_efficiency_assumed"] = turbo_eta
    result["multistage_turbo_backpressure"] = turbo_backpressure
    for item in interstage_energy:
        i = item["stage"]
        for key, value in item.items():
            if key != "stage": result[f"stage{i}_interstage_{key}"] = value

    perm_streams = []
    perm_comp = None; perm_q = 0.0
    for i, st in enumerate(stages, start=1):
        result[f"membrane_pressure_{i}"] = p1 if i == 1 else stages[i-2]["reject_pressure_bar"] + _interstage_boost_bar(data, i, pu)
        result[f"reject_pressure_{i}"] = st["reject_pressure_bar"]
        result[f"reject_flow_{i}"] = st["reject_flow"]
        result[f"stage{i}_recovery"] = st["recovery"]
        result[f"stage{i}_permeate_flow"] = st["permeate_flow"]
        if i > 1:
            result[f"interstage_boost_{i}"] = _interstage_boost_bar(data, i, pu)
        _attach_membrane(result, st, f"stage{i}_")
        c = st.get("permeate_composition_mg_l")
        if c:
            perm_comp = c if perm_comp is None else mix_compositions(perm_comp, perm_q, c, st["permeate_flow"])
            perm_q += st["permeate_flow"]
        if c and st.get("permeate_total_alkalinity_mol_kg") is not None:
            perm_streams.append({"flow": st["permeate_flow"], "composition": c,
                                 "state": {"total_alkalinity_mol_kg": st["permeate_total_alkalinity_mol_kg"],
                                           "total_inorganic_carbon_mol_kg": st["permeate_total_inorganic_carbon_mol_kg"]}})
    if perm_comp is not None:
        result["composite_permeate_composition_mg_l"] = perm_comp
        result["composite_permeate_tds_ppm"] = total_tds_mg_l(perm_comp)
    if perm_streams and not _bool(data, "_solver_fast", False):
        try:
            mixed = mix_carbonate_streams(perm_streams, float(stages[0].get("temperature_c", 25.0)))
            result["composite_permeate_ph"] = mixed["ph"]
            result["composite_permeate_alkalinity_mg_l_as_hco3"] = mixed["total_alkalinity_mg_l_as_hco3"]
            result["composite_permeate_total_alkalinity_mol_kg"] = mixed["total_alkalinity_mol_kg"]
            result["composite_permeate_total_inorganic_carbon_mol_kg"] = mixed["total_inorganic_carbon_mol_kg"]
            result["composite_permeate_composition_mg_l"] = mixed["composition"]
            result["composite_permeate_tds_ppm"] = total_tds_mg_l(mixed["composition"])
        except (KeyError, ValueError, ZeroDivisionError):
            pass

    # Plant train / N-1 capacity summary. This is kept algebraic so it works for
    # manual and Auto Design arrays and does not distort the membrane calculation.
    operating = int(_float(data, "operating_trains", 1) or 1)
    standby = int(_float(data, "standby_trains", 0) or 0)
    if operating < 1 or standby < 0:
        raise ValueError("Plant configuration requires at least one operating train and zero or more standby trains.")
    installed = operating + standby
    train_m3d = total_perm * 24.0
    normal_m3d = operating * train_m3d
    installed_m3d = installed * train_m3d
    nminus1_trains = max(0, installed - 1)
    nminus1_m3d = nminus1_trains * train_m3d
    required = _float(data, "required_capacity_m3d", None)
    result.update({"operating_trains": operating, "standby_trains": standby, "installed_trains": installed,
                   "train_product_capacity_m3d": train_m3d, "normal_operating_capacity_m3d": normal_m3d,
                   "installed_capacity_m3d": installed_m3d, "n_minus_one_available_trains": nminus1_trains,
                   "n_minus_one_capacity_m3d": nminus1_m3d})
    if required is not None and required > 0:
        result["required_capacity_m3d"] = required
        result["n_minus_one_capacity_margin_m3d"] = nminus1_m3d - required
        result["n_minus_one_meets_required"] = nminus1_m3d + 1e-9 >= required

    return display(result, fu, pu)



def _multistage_px_base(data):
    """General 1-4 stage BWRO/SWRO isobaric pressure-exchanger architecture.

    The final-stage concentrate is the IC high-pressure inlet.  The incoming feed
    branch is pressure-exchanged and recombined with the HPP branch.  If the IC
    outlet is below the Stage-1 header, a booster is calculated; if it is above
    the header (common when interstage boosting leaves excess final-brine
    pressure), CalcOsPower inserts a throttling/control duty and reports the
    dissipated hydraulic power.  The excess pressure is never credited as extra
    IC efficiency.
    """
    d = dict(data)
    fu, pu, getf, getp = common(d)
    q0 = getf("feed_flow")
    suction = getp("suction_pressure")
    base_comp = composition_from_request(d) if str(d.get("water_mode", "full")).lower() == "full" else None
    raw_tds = total_tds_mg_l(base_comp) if base_comp is not None else _float(d, "feed_tds", 0.0)
    mixing = max(0.0, min(0.20, float(d.get("bwpx_mixing_fraction", 0.02) or 0.0)))
    flow_eff = max(0.50, min(1.05, float(d.get("bwpx_flow_balance_eff", 0.98) or 0.98)))
    pressure_eff = max(0.50, min(0.999, float(d.get("bwpx_pressure_transfer_eff", 0.96) or 0.96)))
    hp_out = pressure_to_bar(_float(d, "bwpx_brine_backpressure", 1.5) or 1.5, pu)
    if hp_out < 0:
        raise ValueError("Isobaric brine outlet/backpressure cannot be negative.")

    # Iterate the small salinity feedback created by IC mixing into the Stage-1 feed.
    # Warm starts carry local chemistry/thermohydraulic metadata from compatible
    # nearby duties; Anderson acceleration only changes the iterate proposal.
    calc_data = dict(d)
    result = None
    signature = water_state_signature(d)
    p_coordinate = pressure_to_bar(float(d.get("membrane_pressure_1", pressure_from_bar(60.0, pu)) or pressure_from_bar(60.0,pu)), pu)
    warm = d.get("_px_warm_state") or _PX_STATE_CACHE.predictor(p_coordinate, signature)
    effective_comp = base_comp
    warm_used=False
    if base_comp is not None and isinstance(warm,dict) and warm.get("signature") in (None,signature):
        wc=warm.get("effective_composition_mg_l")
        if isinstance(wc,dict):
            try:
                candidate={k:max(0.0,float(wc.get(k,0.0))) for k in SPECIES}
                if total_tds_mg_l(candidate)>0:
                    effective_comp=candidate; warm_used=True
                    for ion,value in candidate.items(): calc_data[f"ion_{ion}"]=float(value)
                    calc_data["feed_tds"]=total_tds_mg_l(candidate)
            except Exception: warm_used=False
    iterations = 0
    fast_px_trial = _bool(d, "_solver_fast", False)
    max_coupling_passes = 3 if fast_px_trial else 12
    coupling_tol = 0.25 if fast_px_trial else 0.05
    mixer=AndersonMixer(memory=4); trace=SolverTrace("Anderson accelerated")
    prev_resid=None; last_accelerated=False; alpha=0.65
    for iterations in range(1, max_coupling_passes + 1):
        trial = dict(calc_data); trial["_solver_fast"] = True
        result = _multistage_base(trial)
        q_brine = flow_to_m3h(float(result["reject_flow_final"]), fu)
        q_lp = min(q0, max(0.0, q_brine * flow_eff))
        if base_comp is None or q_lp <= 0: break
        n = int(result.get("stage_count", _multistage_count(d)))
        brine_comp = result.get(f"stage{n}_concentrate_composition_mg_l")
        if not brine_comp: break
        px_branch = mix_compositions(base_comp, max(0.0, 1.0-mixing), brine_comp, mixing)
        q_hpp = max(0.0, q0-q_lp)
        new_comp = mix_compositions(base_comp, q_hpp, px_branch, q_lp)
        old_tds = total_tds_mg_l(effective_comp or base_comp); new_tds = total_tds_mg_l(new_comp)
        resid=new_tds-old_tds; trace.add(iterations,abs(resid),method=("Anderson" if last_accelerated else "adaptive relaxation"))
        if abs(resid) < coupling_tol:
            effective_comp=new_comp
            for ion,value in new_comp.items(): calc_data[f"ion_{ion}"]=float(value)
            calc_data["feed_tds"]=new_tds
            break
        if prev_resid is not None and last_accelerated and abs(resid)>1.15*abs(prev_resid):
            mixer.reset(); trace.fallback("bounded line search"); alpha=max(0.30,min(alpha,0.50)); last_accelerated=False
        if prev_resid is not None:
            if resid*prev_resid<0: alpha=max(0.25,alpha*0.55)
            elif abs(resid)<0.70*abs(prev_resid): alpha=min(0.82,alpha*1.12)
            elif abs(resid)>1.05*abs(prev_resid): alpha=max(0.30,alpha*0.70)
        x=[effective_comp[k] for k in SPECIES]; gx=[new_comp[k] for k in SPECIES]
        cand=mixer.propose(x,gx); proposal=None
        if cand is not None:
            proposal=[]
            for a,b,c in zip(x,gx,cand):
                span=abs(b-a); lo=max(0.0,min(a,b)-0.5*span); hi=max(a,b)+0.5*span; proposal.append(min(max(c,lo),hi))
        if proposal is not None:
            effective_comp={k:max(0.0,proposal[i]) for i,k in enumerate(SPECIES)}; last_accelerated=True
        else:
            effective_comp={k:max(0.0,(1.0-alpha)*effective_comp[k]+alpha*new_comp[k]) for k in SPECIES}; last_accelerated=False
        for ion,value in effective_comp.items(): calc_data[f"ion_{ion}"]=float(value)
        calc_data["feed_tds"]=total_tds_mg_l(effective_comp); prev_resid=resid
    # Candidate evaluations used by the smart pressure solver do not need the
    # expensive full-detail chemistry pass.  The accepted pressure is always
    # recalculated by _solve_pressure_for_product/_recovery without _solver_fast.
    if fast_px_trial:
        final_fast = dict(calc_data)
        final_fast["_solver_fast"] = True
        result = _multistage_base(final_fast)
    else:
        calc_data.pop("_solver_fast", None)
        result = _multistage_base(calc_data)
    q_brine = flow_to_m3h(float(result["reject_flow_final"]), fu)
    p_brine = pressure_to_bar(float(result[f"reject_pressure_{int(result.get('stage_count',1))}"]), pu)
    p1 = pressure_to_bar(float(result["membrane_pressure_1"]), pu)
    q_product = flow_to_m3h(float(result["product_flow"]), fu)
    q_lp = min(q0, max(0.0, q_brine * flow_eff))
    q_hpp = max(0.0, q0 - q_lp)
    source_dp = max(0.0, p_brine - hp_out)
    lp_out = suction + pressure_eff * source_dp
    balance = lp_out - p1
    # The header pressure-match tolerance is not an independent setting.  Per
    # the CalcOsPower hydraulic convention it is linked to the HPP inlet
    # pressure (common low-pressure feed header).
    tol = max(0.05, suction)
    booster_dp = 0.0; throttle_dp = 0.0; control = "direct"
    if balance < -tol:
        control = "booster"; booster_dp = -balance
    elif balance > tol:
        control = "throttle"; throttle_dp = balance
    peff = float(d.get("pump_eff", 0.85)); meff = float(d.get("motor_eff", 0.97)); veff = _vfd_eff(d, "vfd_eff", "pump_no_vfd")
    ceff = float(d.get("circ_pump_eff", d.get("booster_pump_eff", 0.82))); cmeff = float(d.get("circ_motor_eff", d.get("booster_motor_eff", 0.96))); cveff = _vfd_eff(d, "circ_vfd_eff", "circ_no_vfd")
    hpp_vcmp = None; pxb_vcmp = None
    pump_basis = str(d.get("pump_curve_basis","auto")).lower()
    eff_tds_for_pump = total_tds_mg_l(effective_comp) if effective_comp else raw_tds
    pump_density = 1000.0 * solution_specific_gravity(eff_tds_for_pump, _float(d,"temperature_c",25.0))
    if pump_basis in {"vcmp","vcmp_auto","database"} and q_hpp > 1e-12 and p1 > suction:
        hsel=select_vcmp_pump(q_hpp,max(0.0,p1-suction),density_kg_m3=pump_density,motor_eff=meff,vfd_eff=veff,
            min_vfd_hz=float(d.get("vcmp_min_vfd_hz",40.0) or 40.0),max_vfd_hz=float(d.get("vcmp_max_vfd_hz",60.0) or 60.0),
            flow_margin=float(d.get("vcmp_flow_margin",0.05) or 0.0),head_margin=float(d.get("vcmp_head_margin",0.05) or 0.0),
            reduced_impeller_penalty_pp=float(d.get("vcmp_reduced_impeller_eta_penalty_pp",2.0) or 0.0),
            low_speed_derate_pp_per_10pct=float(d.get("vcmp_low_speed_eta_derate_pp_per_10pct",0.0) or 0.0),reference_rpm_60=d.get("vcmp_reference_rpm_60") or None,top_n=5)
        if hsel.get("ok"): hpp_vcmp=hsel["selected"]
    if pump_basis in {"vcmp","vcmp_auto","database"} and q_lp > 1e-12 and booster_dp > 1e-12:
        bsel=select_vcmp_pump(q_lp,booster_dp,density_kg_m3=pump_density,motor_eff=cmeff,vfd_eff=cveff,
            min_vfd_hz=float(d.get("vcmp_min_vfd_hz",40.0) or 40.0),max_vfd_hz=float(d.get("vcmp_max_vfd_hz",60.0) or 60.0),
            flow_margin=float(d.get("vcmp_flow_margin",0.05) or 0.0),head_margin=float(d.get("vcmp_head_margin",0.05) or 0.0),
            reduced_impeller_penalty_pp=float(d.get("vcmp_reduced_impeller_eta_penalty_pp",2.0) or 0.0),
            low_speed_derate_pp_per_10pct=float(d.get("vcmp_low_speed_eta_derate_pp_per_10pct",0.0) or 0.0),reference_rpm_60=d.get("vcmp_reference_rpm_60") or None,top_n=5)
        if bsel.get("ok"): pxb_vcmp=bsel["selected"]
    hpp_kw = float(hpp_vcmp["wire_kw"]) if hpp_vcmp is not None else _pump_wire_power_kw(q_hpp, max(0.0, p1-suction), peff, meff, veff)
    px_booster_kw = float(pxb_vcmp["wire_kw"]) if pxb_vcmp is not None else _pump_wire_power_kw(q_lp, booster_dp, ceff, cmeff, cveff)
    interstage_kw = float(result.get("booster_kw", 0.0) or 0.0)
    ro_kw = hpp_kw + interstage_kw + px_booster_kw
    pret_kw = float(result.get("pretreatment_kw", 0.0) or 0.0)
    source_hyd_kw = q_brine * source_dp / 36.0
    transferred_kw = q_lp * max(0.0, lp_out-suction) / 36.0
    throttle_kw = q_lp * throttle_dp / 36.0
    px_eff = transferred_kw / source_hyd_kw if source_hyd_kw > 1e-12 else 0.0
    bwpx_model=str(d.get("bwpx_model","Generic BWRO Isobaric Chamber"))
    auto_bank=_bool(d,"bwpx_auto_size",True)
    if bwpx_model in PX_LEGACY_MODELS:
        px_qty,px_unit_m3h,px_within,px_min_m3h,px_max_m3h,px_bank_reason = _select_legacy_px_bank(
            q_lp,bwpx_model,d.get("bwpx_qty",1),auto_bank)
        px_bank_basis="legacy model flow envelope · auto-sized" if auto_bank else "legacy model flow envelope · manual quantity"
    else:
        raw_min=_float(d,"bwpx_min_unit_flow",None); raw_max=_float(d,"bwpx_max_unit_flow",None)
        px_min_m3h=flow_to_m3h(raw_min,fu) if raw_min is not None and raw_min>0 else 0.0
        px_max_m3h=flow_to_m3h(raw_max,fu) if raw_max is not None and raw_max>0 else 0.0
        px_qty,px_unit_m3h,px_within=_select_generic_px_bank(q_lp,px_min_m3h,px_max_m3h,d.get("bwpx_qty",1),auto_bank)
        px_bank_basis=("user-entered generic unit flow envelope · auto-sized" if auto_bank else "user-entered generic unit flow envelope · manual quantity") if px_max_m3h>0 else "manual generic quantity; no unit maximum entered"
        px_bank_reason=("generic unit-flow envelope satisfied" if px_within else "generic IC/PX bank quantity is outside the entered unit-flow envelope")
    result.update({
        "is_brackish_multistage_px": True, "px_architecture":"multistage_isobaric", "px_model": IC_NEUTRAL_LABELS.get(bwpx_model,bwpx_model),
        "px_qty": px_qty, "px_unit_flow": flow_from_m3h(px_unit_m3h, fu),
        "px_min_unit_flow": flow_from_m3h(px_min_m3h,fu) if px_min_m3h>0 else 0.0,
        "px_max_unit_flow": flow_from_m3h(px_max_m3h,fu) if px_max_m3h>0 else 0.0, "px_within_flow_range": px_within,
        "px_bank_sizing_basis":px_bank_basis, "px_bank_auto_size":auto_bank,
        "px_bank_auto_feasible":bool(px_within) if auto_bank else None, "px_bank_sizing_reason":px_bank_reason,
        "px_hp_in_pressure": pressure_from_bar(p_brine, pu), "px_hp_out_pressure": pressure_from_bar(hp_out, pu), "px_hp_dp": pressure_from_bar(source_dp, pu),
        "px_lp_in_pressure": pressure_from_bar(suction, pu), "px_lp_out_pressure": pressure_from_bar(lp_out, pu), "px_lp_dp": pressure_from_bar(max(0.0,lp_out-suction), pu),
        "px_lp_flow": flow_from_m3h(q_lp, fu), "px_mixing": mixing, "px_overall_eff": px_eff, "px_pressure_transfer_efficiency":pressure_eff,
        "px_flow_balance_efficiency":flow_eff, "px_lubrication_flow":0.0, "px_motor_kw":0.0,
        "px_recovered_kw": transferred_kw, "px_source_hydraulic_kw":source_hyd_kw,
        "px_hydraulic_control":control, "px_header_pressure_required":pressure_from_bar(p1, pu), "px_pressure_balance":pressure_from_bar(balance, pu),
        "px_header_tolerance":pressure_from_bar(tol,pu), "px_header_tolerance_source":"HPP inlet pressure",
        "px_booster_required": control=="booster", "px_throttle_required":control=="throttle",
        "circ_flow": flow_from_m3h(q_lp, fu), "circ_dp":pressure_from_bar(booster_dp, pu), "circ_kw":px_booster_kw,
        "px_throttle_dp":pressure_from_bar(throttle_dp, pu), "px_throttle_dissipation_kw":throttle_kw,
        "hpp_flow":flow_from_m3h(q_hpp, fu), "hpp_kw":hpp_kw, "booster_kw":interstage_kw + px_booster_kw,
        "electric_kw":ro_kw, "ro_sec":ro_kw/max(q_product,1e-12), "pump_sec":ro_kw/max(q_product,1e-12),
        "total_sec":(ro_kw+pret_kw)/max(q_product,1e-12), "px_aux_sec":px_booster_kw/max(q_product,1e-12),
        "raw_feed_tds":raw_tds, "effective_membrane_feed_tds":total_tds_mg_l(effective_comp) if effective_comp else raw_tds,
        "px_feed_tds_after_mixing": total_tds_mg_l(effective_comp) if effective_comp else raw_tds,
        "px_coupling_iterations":iterations,
        "px_coupling_method":"Anderson accelerated" if not trace.fallbacks else "Anderson + safeguarded fallback",
        "px_warm_start_used":warm_used,
        "solver_diagnostics":trace.as_dict(coupling_tol),
        "_px_solver_state":{"signature":signature,"effective_feed_tds":total_tds_mg_l(effective_comp) if effective_comp else raw_tds,
            "effective_composition_mg_l":dict(effective_comp or {}),
            "thermodynamic":water_state_snapshot(pressure_bar=p1,flow_m3h=q0,temperature_c=_float(d,"temperature_c",25.0),
                density_kg_l=solution_specific_gravity(total_tds_mg_l(effective_comp) if effective_comp else raw_tds,_float(d,"temperature_c",25.0)),
                tds_mg_l=total_tds_mg_l(effective_comp) if effective_comp else raw_tds,composition=effective_comp or {})},
        "px_energy_note":"Excess IC outlet pressure in boosted BWRO is inherited from upstream/interstage pumping and is dissipated by throttling; it is not credited as additional isobaric efficiency.",
        "px_hpp_pump_source":"vcmp_database" if hpp_vcmp is not None else "manual_efficiency_fallback",
        "px_booster_pump_source":"vcmp_database" if pxb_vcmp is not None else "manual_efficiency_fallback",
        "px_hpp_pump_family":hpp_vcmp.get("product_family") if hpp_vcmp else None,
        "px_hpp_pump_stage_config":hpp_vcmp.get("stage_config") if hpp_vcmp else None,
        "px_hpp_pump_frequency_hz":hpp_vcmp.get("frequency_hz") if hpp_vcmp else None,
        "px_hpp_pump_efficiency":hpp_vcmp.get("pump_efficiency") if hpp_vcmp else peff,
        "px_hpp_pump_shaft_torque_nm":hpp_vcmp.get("shaft_torque_nm") if hpp_vcmp else None,
        "px_hpp_pump_speed_rpm":hpp_vcmp.get("speed_rpm") if hpp_vcmp else None,
        "px_booster_pump_family":pxb_vcmp.get("product_family") if pxb_vcmp else None,
        "px_booster_pump_stage_config":pxb_vcmp.get("stage_config") if pxb_vcmp else None,
        "px_booster_pump_frequency_hz":pxb_vcmp.get("frequency_hz") if pxb_vcmp else None,
        "px_booster_pump_efficiency":pxb_vcmp.get("pump_efficiency") if pxb_vcmp else ceff,
        "px_booster_pump_shaft_torque_nm":pxb_vcmp.get("shaft_torque_nm") if pxb_vcmp else None,
        "vcmp_mechanical_seal_note":"VCMP use on PX/interstage booster duty requires verification of a suitable high-pressure mechanical seal and pressure rating.",
    })
    _PX_STATE_CACHE.put(p_coordinate, signature, result.get("_px_solver_state", {}))
    return display({k:(flow_to_m3h(v,fu) if False else v) for k,v in result.items()}, fu, pu) if False else result

def _multistage_core(data):
    auto=str(data.get("design_mode","manual")).lower()=="auto"
    if not auto:
        result=_with_tridirectional_solve(data,_multistage_base)
        result["auto_sized"]=False
        return result

    candidates,basis=_multistage_auto_candidates(data)
    screened=[]; failed=[]; early_rejected=0; attempts=0
    set_compute_progress(total=max(1,len(candidates)+1), completed=0,
                         phase=f"Auto Design · screening {len(candidates)} seed arrays")

    def screen_many(items):
        nonlocal early_rejected,attempts
        for c in items:
            raise_if_cancelled()
            attempts+=1
            row=_screen_auto_candidate(c,basis)
            if row["result"] is not None:
                screened.append(row)
            else:
                early_rejected += 1 if row.get("early_rejected") else 0
                failed.append({"ratio":c.get("_auto_seed_ratio_label"),"error":row["error"],
                               "early_rejected":bool(row.get("early_rejected"))})
            advance_compute_progress(1, phase=f"Auto Design · screened {attempts} array candidate{'s' if attempts != 1 else ''}")

    screen_many(candidates)
    recovery_search_used=False
    if not screened:
        # A nominal seed can fail because the requested product is outside the
        # pressure-convergence range for that membrane area/array.  Instead of
        # stopping at that error, expand both active area and the integer tree
        # distribution and retry after the cheap hydraulic prefilter.
        recovery_search_used=True
        existing={tuple(int(c[f"vessels_{i}"]) for i in range(1,basis["n"]+1)) for c in candidates}
        recovery=_multistage_auto_recovery_candidates(data,basis,existing)
        recovery_limit=max(12,min(48,int(_float(data,"auto_design_recovery_candidate_limit",36) or 36)))
        recovery_batch=recovery[:recovery_limit]
        advance_compute_progress(0, extend_total=len(recovery_batch), phase="Auto Design · expanding membrane area / tree arrays")
        screen_many(recovery_batch)
    if not screened:
        # Prefer a solver/convergence reason over an early-filter reason when one
        # exists because it is generally more actionable to the user.
        ordered=sorted(failed,key=lambda x:(1 if x.get("early_rejected") else 0))
        msg=ordered[0]["error"] if ordered else "No hydraulically feasible Auto Design array converged."
        raise ValueError(
            "Auto Design could not establish a hydraulically feasible converged tree array after membrane-area and "
            f"pressure-vessel recovery search. {msg}"
        )
    screened.sort(key=lambda row:_auto_candidate_sort_key(row,basis))

    # Local integer refinement around the best tree arrays.  Every neighbor is
    # screened before the full coupled calculation and is normalized back to a
    # monotonically narrowing funnel if a local change would widen downstream.
    seed_rows=screened[:min(3,len(screened))]
    seen={tuple(int(row["input"][f"vessels_{i}"]) for i in range(1,basis["n"]+1)) for row in screened}
    neighbors=[]; limit=max(8,min(32,int(_float(data,"auto_design_candidate_limit",16) or 16)))
    for row in seed_rows:
        base_counts=[int(row["input"][f"vessels_{i}"]) for i in range(1,basis["n"]+1)]
        for j in range(basis["n"]):
            for delta in (-1,1):
                cc=list(base_counts); cc[j]=max(1,cc[j]+delta); cc=_auto_tree_counts(cc)
                key=tuple(cc)
                if key in seen: continue
                seen.add(key); neighbors.append((row["input"],cc,f"local Stage {j+1} {delta:+d}"))
        # For BWRO we retain the tail-beta redistribution search, but the funnel
        # constraint remains authoritative.  Moving capacity downstream may grow
        # an upstream stage to keep the final array tree-shaped.
        if basis["bwro_tail_beta_priority"] and basis["n"]>1:
            for src in range(basis["n"]-1):
                if base_counts[src]<=1: continue
                for dst in range(src+1,basis["n"]):
                    cc=list(base_counts); cc[src]-=1; cc[dst]+=1; cc=_auto_tree_counts(cc)
                    key=tuple(cc)
                    if key in seen: continue
                    seen.add(key); neighbors.append((row["input"],cc,f"tail-beta shift S{src+1}→S{dst+1}"))
    neighbor_batch=neighbors[:max(0,limit-len(screened))]
    if neighbor_batch:
        advance_compute_progress(0, extend_total=len(neighbor_batch), phase="Auto Design · integer tree-array refinement")
    for template,counts,label in neighbor_batch:
        raise_if_cancelled()
        c=dict(template)
        for i,v in enumerate(counts,1): c[f"vessels_{i}"]=int(v)
        c["_auto_seed_ratio_label"]=label
        attempts+=1; row=_screen_auto_candidate(c,basis)
        if row["result"] is not None: screened.append(row)
        else:
            early_rejected += 1 if row.get("early_rejected") else 0
            failed.append({"ratio":label,"error":row["error"],"early_rejected":bool(row.get("early_rejected"))})
        advance_compute_progress(1, phase=f"Auto Design · screened {attempts} array candidates")
    screened.sort(key=lambda row:_auto_candidate_sort_key(row,basis))
    best=screened[0]
    prepared=dict(best["input"])

    # Final flux guard.  Growing a downstream stage also grows any narrower
    # upstream stages so the final design never loses the tree/funnel geometry.
    guard_passes=0; max_guard=6
    while guard_passes<max_guard:
        raise_if_cancelled()
        guard_passes+=1
        set_compute_progress(phase=f"Auto Design · flux guard pass {guard_passes}")
        fast=dict(prepared); fast["_solver_fast"]=True
        rfast=_with_tridirectional_solve(fast,_multistage_base)
        counts=[int(prepared[f"vessels_{i}"]) for i in range(1,basis["n"]+1)]
        changed=False
        for i in range(1,basis["n"]+1):
            flux=float(rfast.get(f"stage{i}_flux_lmh",0.0) or 0.0)
            vessels=counts[i-1]
            if flux>basis["max_flux"]*1.005:
                counts[i-1]=max(vessels+1,int(math.ceil(vessels*flux/basis["max_flux"]*1.02)))
                changed=True
        counts=_auto_tree_counts(counts)
        if changed:
            for i,v in enumerate(counts,1): prepared[f"vessels_{i}"]=v
        else:
            break

    # One authoritative full-detail calculation for the selected final design.
    raise_if_cancelled()
    set_compute_progress(phase="Auto Design · final detailed validation")
    result=_with_tridirectional_solve(prepared,_multistage_base)
    raise_if_cancelled()
    advance_compute_progress(1, phase="Auto Design · complete")
    final_metrics=_auto_design_metrics(result,basis)
    final_feas=_auto_full_feasibility(result,basis)
    if not final_feas["ok"]:
        raise ValueError("Auto Design final hydraulic validation failed: "+"; ".join(final_feas["reasons"][:5]))

    sizing=[]
    stage_diag={int(x["stage"]):x for x in final_feas["stages"]}
    for i in range(1,basis["n"]+1):
        epv=int(prepared[f"elements_per_vessel_{i}"]); vessels=int(prepared[f"vessels_{i}"])
        prof=result.get(f"stage{i}_element_profile") or []
        tail_beta=float(prof[-1]["polarization_factor"]) if prof else None
        boost=float(result.get(f"interstage_boost_{i}",0.0) or 0.0) if i>1 else 0.0
        diag=stage_diag.get(i,{})
        sizing.append({"stage":i,"pressure_vessels":vessels,"elements_per_vessel":epv,
                       "total_elements":vessels*epv,"active_area_per_vessel_m2":basis["area_per_vessel"][i-1],
                       "stage_active_area_m2":vessels*basis["area_per_vessel"][i-1],
                       "actual_flux_lmh":result.get(f"stage{i}_flux_lmh"),
                       "max_design_flux_lmh":basis["max_flux"],"max_element_flux_lmh":diag.get("max_element_flux_lmh"),
                       "max_element_flux_limit_lmh":basis["max_element_flux_lmh"],"tail_beta":tail_beta,
                       "max_tail_beta_limit":basis["max_tail_beta"],"first_element_feed_m3h":diag.get("first_element_feed_m3h"),
                       "max_first_element_feed_m3h":diag.get("max_first_element_feed_m3h"),
                       "tail_concentrate_m3h":diag.get("tail_concentrate_m3h"),
                       "min_tail_concentrate_m3h":diag.get("min_tail_concentrate_m3h"),
                       "dp_limit_fraction":diag.get("dp_limit_fraction"),
                       "feed_flow_limit_basis":diag.get("feed_flow_limit_basis"),
                       "tail_flow_limit_basis":diag.get("tail_flow_limit_basis"),
                       "interstage_boost_bar":boost})
        result[f"auto_vessels_{i}"]=vessels
        result[f"auto_elements_per_vessel_{i}"]=epv
        result[f"auto_tail_beta_{i}"]=tail_beta
        if i>1: result[f"auto_interstage_boost_bar_{i}"]=boost

    operating=max(1,int(round(_float(data,"operating_trains",1) or 1)))
    vessels_per_skid=sum(int(prepared[f"vessels_{i}"]) for i in range(1,basis["n"]+1))
    elements_per_skid=sum(int(prepared[f"vessels_{i}"])*basis["epv"][i-1] for i in range(1,basis["n"]+1))
    result.update({
        "auto_sizing":sizing,"auto_sized":True,
        "auto_sizing_iterations":guard_passes,
        "max_design_flux_lmh":basis["max_flux"],
        "auto_design_joint_array_boost":bool(_interstage_control_mode(prepared)!="manual" and any(_interstage_equipment(prepared,i)!="none" for i in range(2,basis["n"]+1))),
        "auto_design_selected_seed":prepared.get("_auto_seed_ratio_label",best["input"].get("_auto_seed_ratio_label")),
        "auto_design_recovery_search_used":recovery_search_used,
        "auto_design_candidates_evaluated":attempts,
        "auto_design_candidates_converged":len(screened),
        "auto_design_candidates_failed":len(failed),
        "auto_design_candidates_early_rejected":early_rejected,
        "auto_design_required_area_m2":basis["required_area_m2"],
        "auto_design_area_ratio":final_metrics["area_ratio"],
        "auto_design_tail_beta_by_stage":final_metrics["tail_betas"],
        "auto_design_max_tail_beta":final_metrics["tail_beta_max"],
        "auto_design_max_tail_beta_limit":basis["max_tail_beta"],
        "auto_design_max_element_flux_limit_lmh":basis["max_element_flux_lmh"],
        "auto_design_bwro_tail_beta_priority":basis["bwro_tail_beta_priority"],
        "auto_design_tail_beta_basis":"tail-element polarization factor (beta)",
        "auto_design_array_seed_families":[x[0] for x in _auto_array_ratio_seeds(basis["n"])],
        "auto_design_hydraulic_limits":basis["hydraulic_limits"],
        "auto_design_operating_skids":operating,
        "auto_design_vessels_per_skid":vessels_per_skid,
        "auto_design_total_vessels_operating":vessels_per_skid*operating,
        "auto_design_elements_per_skid":elements_per_skid,
        "auto_design_total_elements_operating":elements_per_skid*operating,
        "auto_design_screening_note":"Manufacturer flow limits are used when cataloged; otherwise transparent diameter-based screening defaults are used for early feasibility only and must be verified against the selected membrane datasheet.",
        "auto_design_failed_seed_notes":failed[:8],
        "auto_design_seed_strategy":"capacity/flux membrane area → tree-array seed → hydraulic prefilter → osmotic/NDP pressure seed → adaptive bracket → detailed validation",
        "auto_design_stage1_pressure_seed_bar":result.get("pressure_seed_bar"),
        "auto_design_stage1_pressure_seed_basis":result.get("pressure_seed_basis"),
        "auto_design_stage1_pressure_seed_details":result.get("pressure_seed_details"),
    })
    return result


def multistage(data):
    prepared = _prepare_calculation_data(data)
    return _attach_acid_dosing(_multistage_core(prepared), prepared)



def _compatible_ro_warm_seed(data):
    """Return a compatible v0.2 RO warm-start seed, or None.

    Seed reuse is initialization only.  The authoritative solver still performs
    the full coupled calculation and convergence checks.  Structurally stale
    seeds (different stage count, membrane model, vessel count or EPV) are
    rejected rather than coerced into incompatible vectors.
    """
    candidates = [
        (data.get("_warm_start_seed"), "previous nearby solution"),
        (data.get("_base_design_seed"), "Plant Design Base Seed"),
    ]
    try:
        n = max(1, min(4, int(float(data.get("stage_count", 1) or 1))))
    except Exception:
        n = 1
    for seed, source in candidates:
        if not isinstance(seed, dict) or seed.get("stale"):
            continue
        try:
            if int(seed.get("stage_count", n)) != n:
                continue
            sm = seed.get("membranes") or []
            sv = seed.get("vessels") or []
            se = seed.get("elements_per_vessel") or []
            compatible = True
            for i in range(1, n + 1):
                dm = str(data.get(f"membrane_{i}", "") or "")
                if i - 1 < len(sm) and sm[i - 1] and dm and str(sm[i - 1]) != dm:
                    compatible = False; break
                dv = data.get(f"vessels_{i}")
                if i - 1 < len(sv) and sv[i - 1] and dv not in (None, "") and int(float(dv)) != int(float(sv[i - 1])):
                    compatible = False; break
                de = data.get(f"elements_per_vessel_{i}")
                if i - 1 < len(se) and se[i - 1] and de not in (None, "") and int(float(de)) != int(float(se[i - 1])):
                    compatible = False; break
            if not compatible:
                continue
            pbar = float(seed.get("feed_pressure_bar") or 0.0)
            if not math.isfinite(pbar) or pbar <= 0:
                continue
            return {"seed_bar": pbar, "source": source, "seed": seed}
        except (TypeError, ValueError, OverflowError):
            continue
    return None


def _stage1_pressure_seed_bar(data, target_product_m3h=None):
    """Return a physics-based Stage-1 feed-pressure seed for inverse solves.

    This is deliberately only an initial guess.  The authoritative membrane
    solver still brackets and converges pressure independently.  The predictor
    combines the requested product duty with the actual stage membrane areas,
    temperature/fouling-corrected water permeability, a near-total-rejection
    concentration estimate, clean hydraulic losses and any known/physics-seeded
    interstage pressure additions.  Each downstream stage is translated back to
    an equivalent Stage-1 pressure requirement, and the largest requirement is
    used as the starting point.
    """
    if _bool(data, "_disable_pressure_seed", False):
        return None
    try:
        fu=data.get("flow_unit","m3/h"); pu=data.get("pressure_unit","bar")
        q0=flow_to_m3h(float(data["feed_flow"]),fu)
        if q0<=0: return None
        target=float(target_product_m3h) if target_product_m3h is not None else None
        if target is None or target<=0:
            tr=_target_recovery_fraction_for_seed(data)
            if tr is None or tr<=0: return None
            target=q0*tr
        target=min(max(target,1e-9),q0*0.95)
        try: n=_multistage_count(data)
        except Exception: n=max(1,min(4,int(_float(data,"stage_count",1) or 1)))
        temp=float(_float(data,"temperature_c",25.0) or 25.0)
        fouling=min(max(float(_float(data,"fouling_factor",1.0) or 1.0),0.30),1.20)
        pp_default=pressure_to_bar(float(_float(data,"permeate_pressure",0.0) or 0.0),pu)
        pp_stage={}
        for _i in range(1,5):
            _raw=_float(data,f"permeate_pressure_{_i}",None)
            pp_stage[_i]=pressure_to_bar(_raw,pu) if _raw is not None else pp_default
        feed_tds=max(0.0,float(_float(data,"feed_tds",_float(data,"analysis_tds",0.0)) or 0.0))

        stage=[]
        for i in range(1,n+1):
            mid=str(data.get(f"membrane_{i}") or data.get("membrane_1") or "")
            if not mid: return None
            epv=max(1,min(8,int(round(_float(data,f"elements_per_vessel_{i}",7) or 7))))
            vessels=max(1,int(round(_float(data,f"vessels_{i}",1) or 1)))
            recipe=_normalize_membrane_recipe(mid,epv,data.get(f"membrane_recipe_{i}"))
            records=[get_membrane(x) for x in recipe]
            areas=[float(mm.get("area_m2") or mm.get("active_area_m2") or 0.0) for mm in records]
            if any(a<=0 for a in areas): return None
            aeff=[]; rejs=[]
            for mm in records:
                a_ds,_=_membrane_model_coefficients(mm)
                tt=_temperature_transport_parameters(mm,temp)
                aeff.append(float(a_ds)*float(tt["water_temperature_factor"])*fouling)
                rejs.append(float(mm.get("rejection_pct",99.0) or 99.0)/100.0)
            area_pos=max(sum(areas),1e-12)
            a_stage=sum(a*aarea for a,aarea in zip(aeff,areas))/area_pos
            r_stage=sum(r*aarea for r,aarea in zip(rejs,areas))/area_pos
            stage.append({"stage":i,"epv":epv,"vessels":vessels,"area_m2":vessels*area_pos,
                          "a_lmh_bar":max(a_stage,1e-6),"rejection":min(max(r_stage,0.0),0.999999),
                          "pressure_limit_bar":min(_membrane_pressure_limit_bar(mm,temp) for mm in records)})
        total_area=max(sum(x["area_m2"] for x in stage),1e-12)

        # For automatic interstage control, zero means no engineer bias; reuse
        # the already-established osmotic-rise seed as the provisional energy
        # addition so Stage-1 pressure is not biased high merely because a later
        # booster/turbo pressure input has not yet been solved.
        boost_seed={}
        if n>1 and _interstage_control_mode(data)!="manual":
            adjustable=[i for i in range(2,n+1) if _interstage_equipment(data,i)!="none"]
            if adjustable:
                try: boost_seed=_interstage_osmotic_boost_seeds(data,adjustable).get("boost_seed_bar",{})
                except Exception: boost_seed={}

        qin=q0; target_remaining=target; area_remaining=total_area
        cumulative_dp=0.0; cumulative_boost=0.0; equivalent=[]
        stage_details=[]
        for idx,x in enumerate(stage):
            area=x["area_m2"]
            if idx==len(stage)-1:
                qp=min(target_remaining,qin*0.90)
            else:
                qp=min(target_remaining*area/max(area_remaining,1e-12),qin*0.90)
            qp=max(0.0,qp); qout=max(qin-qp,qin*1e-8)
            rec=max(0.0,min(0.90,qp/max(qin,1e-12)))
            flux=qp*1000.0/max(area,1e-12)
            ndp=flux/max(x["a_lmh_bar"],1e-9)
            if rec>1e-9:
                avg_cf=-math.log(max(1.0-rec,1e-9))/rec
                elem_rec=1.0-(1.0-rec)**(1.0/max(x["epv"],1))
            else:
                avg_cf=1.0; elem_rec=0.0
            beta=math.exp(0.7*elem_rec)
            tds_in=feed_tds*q0/max(qin,1e-12) if feed_tds>0 else 0.0
            pi_feed=osmotic_pressure_bar(tds_in*avg_cf*beta,temp) if tds_in>0 else 0.0
            perm_tds=tds_in*(1.0-x["rejection"])
            pi_perm=osmotic_pressure_bar(perm_tds,temp) if perm_tds>0 else 0.0
            try:
                dp,_,_=clean_stage_pressure_drop(qin,qout,x["vessels"],x["epv"])
            except Exception:
                dp=0.0
            stage_pp=pp_stage.get(x["stage"],pp_default)
            required_here=stage_pp+max(0.0,pi_feed-pi_perm)+ndp+0.5*max(dp,0.0)
            p1_equiv=required_here+cumulative_dp-cumulative_boost
            equivalent.append(p1_equiv)
            stage_details.append({"stage":x["stage"],"estimated_recovery":rec,"estimated_flux_lmh":flux,
                                  "estimated_feed_osmotic_bar":pi_feed,"estimated_permeate_osmotic_bar":pi_perm,
                                  "estimated_ndp_bar":ndp,"estimated_stage_dp_bar":dp,
                                  "equivalent_stage1_pressure_bar":p1_equiv})
            cumulative_dp+=max(dp,0.0)
            if idx<len(stage)-1:
                pos=idx+2
                entered=max(0.0,_interstage_boost_bar(data,pos,pu))
                predicted=float(boost_seed.get(pos,0.0) or 0.0)
                cumulative_boost += entered if entered>0 else predicted
            target_remaining=max(0.0,target_remaining-qp)
            area_remaining=max(0.0,area_remaining-area)
            qin=qout
        if not equivalent: return None
        low=max(pp_stage.get(1,pp_default)+0.5,2.0)
        # A small numerical guard keeps the starting point just above the
        # simplified predictor; it is not used as a design margin.
        raw=max(equivalent)+0.35
        stage1_limit=float(stage[0]["pressure_limit_bar"])
        seed=min(max(raw,low),stage1_limit)
        return {"seed_bar":seed,"raw_seed_bar":raw,"basis":"physics: osmotic + NDP + hydraulic losses - interstage energy inputs",
                "stage_details":stage_details,"interstage_boost_seed_bar":{str(k):float(v) for k,v in boost_seed.items()},
                "target_product_m3h":target,"feed_flow_m3h":q0,"stage1_pressure_limit_bar":stage1_limit}
    except (KeyError,ValueError,TypeError,ZeroDivisionError,OverflowError):
        return None


def _rule_of_thumb_pressure_seed_bar(data, target_product_m3h=None):
    """Return a salinity-band pressure seed supplied by the project engineer.

    The estimate is intentionally independent from the detailed membrane-A
    predictor.  It uses Cc ~= Cf/(1-R), the arithmetic mean of feed and final
    concentrate TDS, the current osmotic model at that average concentration,
    and an empirical net-driving-pressure allowance:
      0-5,000 mg/L -> 6 bar
      5,000-15,000 mg/L -> 10 bar
      15,000-30,000 mg/L -> 12.5 bar
      >30,000 mg/L -> 15 bar

    It is a seed/fallback only.  It never replaces the full coupled membrane
    calculation or its convergence and hydraulic-limit checks.
    """
    try:
        if _bool(data, "_disable_pressure_seed", False):
            return None
        # The rule describes one membrane module/train.  Multistage pressure
        # requirements are better represented by the existing stage-by-stage
        # permeability/osmotic predictor.
        if _multistage_count(data) != 1:
            return None
        fu=data.get("flow_unit","m3/h"); pu=data.get("pressure_unit","bar")
        qf=flow_to_m3h(float(data["feed_flow"]),fu)
        if qf <= 0:
            return None
        target=float(target_product_m3h) if target_product_m3h is not None else None
        if target is None or target <= 0:
            rr=_target_recovery_fraction_for_seed(data)
            if rr is None:
                return None
            target=qf*rr
        recovery=min(max(target/max(qf,1e-12),1e-6),0.95)
        feed_tds=max(0.0,float(_float(data,"feed_tds",_float(data,"analysis_tds",0.0)) or 0.0))
        if feed_tds <= 0:
            return None
        concentrate_tds=feed_tds/max(1.0-recovery,1e-9)
        average_tds=0.5*(feed_tds+concentrate_tds)
        temp=float(_float(data,"temperature_c",25.0) or 25.0)
        average_pi=float(_osmotic_for_concentration(average_tds,temp,feed_tds,None)["osmotic_bar"])
        if feed_tds <= 5000.0:
            allowance=6.0
        elif feed_tds <= 15000.0:
            allowance=10.0
        elif feed_tds <= 30000.0:
            allowance=12.5
        else:
            allowance=15.0
        pp_raw=_float(data,"permeate_pressure_1",None)
        if pp_raw is None:
            pp_raw=_float(data,"permeate_pressure",0.0) or 0.0
        permeate_backpressure=pressure_to_bar(float(pp_raw),pu)
        seed=average_pi+allowance+permeate_backpressure
        return {"seed_bar":seed,
                "basis":"engineering rule: arithmetic-average osmotic pressure + salinity-band NDP allowance",
                "feed_tds_mg_l":feed_tds,"recovery":recovery,
                "estimated_concentrate_tds_mg_l":concentrate_tds,
                "estimated_average_tds_mg_l":average_tds,
                "estimated_average_osmotic_bar":average_pi,
                "ndp_allowance_bar":allowance,
                "permeate_backpressure_bar":permeate_backpressure}
    except (KeyError,ValueError,TypeError,ZeroDivisionError,OverflowError):
        return None


def _solve_pressure_for_product(data, base_calc):
    """Solve Stage-1 membrane pressure for a requested total permeate flow.

    Uses a safeguarded smart bracket followed by a bracketed secant/Brent-like
    iteration. The older broad pressure scan is retained only as an automatic
    conservative fallback. Every evaluated pressure remains a fully coupled
    membrane/ERD calculation, so speed is improved without decoupling physics.
    """
    if not _bool(data, "membrane_coupling", False):
        raise ValueError("Permeate-flow input requires RO membrane coupling to be ON.")
    fu = data.get("flow_unit", "m3/h")
    pu = data.get("pressure_unit", "bar")
    target_user = _float(data, "target_product_flow", None)
    if target_user is None or target_user <= 0:
        raise ValueError("Enter a permeate-flow target greater than zero.")
    target = flow_to_m3h(target_user, fu)
    qfeed = flow_to_m3h(float(data["feed_flow"]), fu)
    if target >= qfeed:
        raise ValueError("Permeate-flow target must be lower than the feed flow.")

    pp_user = _float(data, "permeate_pressure", 0.0)
    if pp_user is None:
        pp_user = 0.0
    pp_bar = pressure_to_bar(pp_user, pu)
    # Q→P and R→P pressure is an OUTPUT.  Use a physics-based membrane seed
    # instead of a generic 60-bar starting point whenever the design basis is
    # sufficient to estimate osmotic pressure, NDP and hydraulic losses.  An
    # entered pressure remains a valid engineer-provided seed for API/backward
    # compatibility; it is never treated as a fixed constraint in these modes.
    seed_info = _stage1_pressure_seed_bar(data, target)
    physics_seed_bar = float(seed_info["seed_bar"]) if seed_info else None
    rule_seed_info = _rule_of_thumb_pressure_seed_bar(data, target)
    rule_seed_bar = float(rule_seed_info["seed_bar"]) if rule_seed_info else None
    warm_info = _compatible_ro_warm_seed(data)
    current_user = _float(data, "membrane_pressure_1", None)
    if warm_info is not None:
        current_bar = float(warm_info["seed_bar"])
        seed_source = warm_info["source"]
    elif current_user is None:
        if physics_seed_bar is not None:
            current_bar = physics_seed_bar
            seed_source = "physics predictor"
        elif rule_seed_bar is not None:
            current_bar = rule_seed_bar
            seed_source = "salinity-band engineering rule"
        else:
            current_bar = 60.0
            seed_source = "60 bar neutral fallback"
    else:
        current_bar = pressure_to_bar(current_user, pu)
        seed_source = "engineer/user pressure seed"
    low_bar = max(pp_bar + 0.5, 2.0)
    try:
        msel = get_membrane(str(data.get("membrane_1", "")))
        membrane_limit = float(msel.get("max_operating_pressure_bar", 120.0))
    except Exception:
        membrane_limit = 120.0
    high_bar = max(low_bar + 0.5, membrane_limit)
    current_bar = min(max(current_bar, low_bar), high_bar)

    cache = {}
    eval_count = 0
    pressure_search_backend = "cpu-main"
    def nearest_warm_state(pbar):
        candidates=[]
        for row in cache.values():
            if row is None or len(row)<3 or not isinstance(row[2],dict): continue
            state=row[2].get("_px_solver_state")
            if state: candidates.append((abs(float(row[0])-float(pbar)),state))
        return min(candidates,key=lambda x:x[0])[1] if candidates else None
    def evaluate(pbar):
        nonlocal eval_count
        raise_if_cancelled()
        pbar = min(max(float(pbar), low_bar), high_bar)
        key = round(pbar, 8)
        if key in cache:
            return cache[key]
        trial = dict(data)
        trial["solve_basis"] = "pressure"
        trial["_solver_fast"] = True
        trial["membrane_pressure_1"] = pressure_from_bar(pbar, pu)
        if base_calc.__name__ in {"_interstage_base", "_biturbo_base"}:
            trial["solve_stage_pressures"] = True
        if base_calc.__name__ in {"_pressure_exchanger_base","_multistage_px_base"}:
            ws=nearest_warm_state(pbar)
            if ws: trial["_px_warm_state"]=ws
        eval_count += 1
        try:
            result = base_calc(trial)
            qprod = flow_to_m3h(float(result["product_flow"]), fu)
            if not math.isfinite(qprod):
                cache[key] = None
            else:
                cache[key] = (pbar, qprod, result)
        except (ValueError, ZeroDivisionError, OverflowError):
            cache[key] = None
        return cache[key]

    def batch_evaluate(points):
        """Evaluate independent feed-pressure candidates.

        v18.3.9 keeps routine manual Plant Design root solves in-process.  This
        avoids Windows multiprocessing spawn/import overhead for calculations
        that are intrinsically cheap.  Auto Design and other genuinely parallel
        workloads can still use the worker pool, and the wide fallback remains
        eligible for parallel execution unless the caller explicitly requests
        the serial fast path.
        """
        nonlocal eval_count, pressure_search_backend
        raise_if_cancelled()
        pts=[]
        for p in points:
            p=min(max(float(p),low_bar),high_bar); key=round(p,8)
            if key not in cache and key not in {round(x,8) for x in pts}: pts.append(p)
        prefer_serial = _bool(data, "_prefer_serial_root", False) or os.environ.get("CALCOSPOWER_TEST_SERIAL", "0") == "1"
        if pts and not prefer_serial and not _nested_cpu_disabled(data):
            mode_map={"_single_stage_base":"single","_multistage_base":"multistage","_interstage_base":"interstage",
                      "_biturbo_base":"biturbo","_pressure_exchanger_base":"px"}
            calc_mode=mode_map.get(base_calc.__name__)
            if base_calc.__name__ == "_multistage_px_base":
                calc_mode = "interstage_px" if str(data.get("calculation_workspace", "")).lower() == "interstage_px" else "px"
            if calc_mode:
                try:
                    from compute_engine import parallel_pressure_trials, update_compute_run
                    payloads=[]
                    for pbar in pts:
                        trial=dict(data); trial["solve_basis"]="pressure"; trial["_solver_fast"]=True
                        trial["membrane_pressure_1"]=pressure_from_bar(pbar,pu)
                        if base_calc.__name__ in {"_interstage_base","_biturbo_base"}: trial["solve_stage_pressures"]=True
                        if base_calc.__name__ in {"_pressure_exchanger_base","_multistage_px_base"}:
                            ws=nearest_warm_state(pbar)
                            if ws: trial["_px_warm_state"]=ws
                        payloads.append({"pressure":pbar,"data":trial,"base_calc_name":base_calc.__name__})
                    batch=parallel_pressure_trials(calc_mode,payloads)
                    raise_if_cancelled()
                    eval_count+=len(pts)
                    for pbar,row in zip(pts,batch.get("results",[])):
                        key=round(pbar,8)
                        if row and row.get("ok") and isinstance(row.get("result"),dict):
                            rr=row["result"]; qprod=flow_to_m3h(float(rr["product_flow"]),fu)
                            cache[key]=(pbar,qprod,rr) if math.isfinite(qprod) else None
                        else: cache[key]=None
                    pressure_search_backend=batch.get("backend","cpu-multiprocess")
                    update_compute_run(backend=pressure_search_backend,workers=batch.get("workers",1))
                except Exception:
                    # A user Stop request must never be converted into the normal
                    # sequential fallback path after the worker pool is terminated.
                    raise_if_cancelled()
                    pressure_search_backend="cpu-main"
                    for pbar in pts: evaluate(pbar)
            else:
                for pbar in pts: evaluate(pbar)
        else:
            for pbar in pts: evaluate(pbar)
        return [cache.get(round(min(max(float(p),low_bar),high_bar),8)) for p in points]

    def err(x):
        return x[1] - target

    valid = []
    def refresh_bracket():
        uniq=sorted({round(x[0],8):x for x in valid if x is not None}.values(),key=lambda x:x[0])
        for a,b in zip(uniq,uniq[1:]):
            if err(a)*err(b)<=0:
                return uniq,(a,b)
        return uniq,None

    # Evaluate the primary seed first, plus the independent physics predictor if
    # the engineer supplied a materially different starting value.  Then expand
    # a narrow bracket progressively.  Most converged duties therefore avoid the
    # old nine-point up-front pressure fan.
    initial_points=[current_bar]
    if physics_seed_bar is not None and abs(physics_seed_bar-current_bar)>0.75:
        initial_points.append(physics_seed_bar)
    for x in batch_evaluate(initial_points):
        if x is not None: valid.append(x)
    first=cache.get(round(current_bar,8))
    if first is not None and abs(err(first)) <= max(1e-5*target, 1e-5):
        full_trial=dict(data); full_trial["solve_basis"]="pressure"
        # Candidate screening remains in fast mode.  Only the final selected
        # Auto Design array is recalculated later without _solver_fast.
        if not _bool(data, "_solver_fast", False): full_trial.pop("_solver_fast",None)
        full_trial["membrane_pressure_1"]=pressure_from_bar(first[0],pu)
        if base_calc.__name__ in {"_interstage_base","_biturbo_base"}: full_trial["solve_stage_pressures"]=True
        result=base_calc(full_trial)
        result.update(solve_basis="product",target_product_flow=target_user,solved_feed_pressure=result["membrane_pressure_1"],
                      pressure_solve_iterations=0,pressure_solve_evaluations=eval_count,solver_method="smart bracket · physics-seeded adaptive",
                      pressure_search_backend=pressure_search_backend,
                      pressure_seed_bar=current_bar,pressure_seed_source=seed_source,
                      pressure_seed_basis=(seed_info or rule_seed_info or {}).get("basis"),pressure_seed_details=(seed_info or rule_seed_info),
                      engineering_rule_seed_bar=rule_seed_bar,engineering_rule_seed_details=rule_seed_info,
                      solver_fallback_used=False,product_flow_error=result["product_flow"]-target_user)
        return result
    uniq,bracket=refresh_bracket()
    if bracket is None:
        center=physics_seed_bar if physics_seed_bar is not None else current_bar
        for frac in (0.06,0.12,0.24,0.45):
            span=max(1.0,frac*max(center,15.0))
            pair=[center-span,center+span]
            for x in batch_evaluate(pair):
                if x is not None: valid.append(x)
            uniq,bracket=refresh_bracket()
            if bracket is not None:
                break

    fallback_used = False
    if bracket is None and rule_seed_bar is not None and abs(rule_seed_bar-current_bar)>0.50:
        for x in batch_evaluate([rule_seed_bar]):
            if x is not None: valid.append(x)
        uniq,bracket=refresh_bracket()
    if bracket is None:
        # Conservative fallback: broad scan, preserving v13's ability to bridge
        # invalid low-pressure ERD states.
        fallback_used = True
        # Auto Design candidate screening only needs to determine whether this
        # fixed array can bracket the requested duty.  A 17-point broad fallback
        # is sufficient here; the selected final array still receives the full
        # 49-point conservative fallback if needed.
        broad_divisions = 16 if _bool(data, "_auto_candidate_screen", False) else 48
        broad_points=[low_bar + (high_bar-low_bar)*i/float(broad_divisions) for i in range(broad_divisions+1)]
        for x in batch_evaluate(broad_points):
            if x is not None: valid.append(x)
        uniq=sorted({round(x[0],8):x for x in valid}.values(), key=lambda x:x[0])
        bracket=None
        for a,b in zip(uniq,uniq[1:]):
            if err(a)*err(b) <= 0:
                bracket=(a,b); break
        if bracket is None:
            if not uniq:
                raise ValueError("No valid pressure range could be found for the requested coupled duty point.")
            qmin=min(v[1] for v in uniq); qmax=max(v[1] for v in uniq)
            raise ValueError(
                f"Requested permeate flow is outside the solvable range at the current configuration "
                f"({flow_from_m3h(qmin,fu):.1f} to {flow_from_m3h(qmax,fu):.1f} {fu})."
            )

    lo, hi = bracket
    if lo[0] > hi[0]: lo,hi=hi,lo
    final=min((lo,hi), key=lambda x:abs(err(x)))
    iterations=0
    tol=max(1e-5*target,1e-5)
    max_root_iterations = 20 if _bool(data, "_auto_candidate_screen", False) else 35
    for iterations in range(1,max_root_iterations+1):
        raise_if_cancelled()
        flo,fhi=err(lo),err(hi)
        if abs(flo)<=tol: final=lo; break
        if abs(fhi)<=tol: final=hi; break
        if (hi[0]-lo[0]) <= HYDRAULIC_PRESSURE_ABS_TOL_BAR:
            final=min((lo,hi), key=lambda x:abs(err(x)))
            break
        # Bracketed secant step; midpoint fallback guarantees contraction.
        if abs(fhi-flo)>1e-14:
            p=hi[0]-fhi*(hi[0]-lo[0])/(fhi-flo)
        else:
            p=0.5*(lo[0]+hi[0])
        width=hi[0]-lo[0]
        guard=0.08*width
        if not (lo[0]+guard < p < hi[0]-guard):
            p=0.5*(lo[0]+hi[0])
        mid=evaluate(p)
        if mid is None:
            # A valid bracket is already known; bisect toward the valid side.
            p=0.5*(lo[0]+hi[0])
            mid=evaluate(p)
            if mid is None:
                # Fall back to quarter points before giving up this iteration.
                candidates=[evaluate(lo[0]+0.25*width),evaluate(lo[0]+0.75*width)]
                candidates=[x for x in candidates if x is not None]
                if not candidates:
                    fallback_used=True
                    continue
                mid=min(candidates,key=lambda x:abs(err(x)))
        final=mid
        fm=err(mid)
        if abs(fm)<=tol:
            break
        if flo*fm <= 0:
            hi=mid
        else:
            lo=mid

    # Solver trials intentionally suppress report-only work. Recalculate the
    # converged point once in full-detail mode for charts, sensitivities and
    # final reporting.
    final_trial = dict(data)
    final_trial["solve_basis"] = "pressure"
    # Do not accidentally turn every Auto Design candidate into a full report-
    # detail calculation.  Screening candidates stay fast; _multistage_core
    # performs exactly one authoritative full-detail solve after selection.
    if not _bool(data, "_solver_fast", False):
        final_trial.pop("_solver_fast", None)
    final_trial["membrane_pressure_1"] = pressure_from_bar(final[0], pu)
    if base_calc.__name__ in {"_interstage_base", "_biturbo_base"}:
        final_trial["solve_stage_pressures"] = True
    if base_calc.__name__ in {"_pressure_exchanger_base","_multistage_px_base"}:
        ws=nearest_warm_state(final[0])
        if ws: final_trial["_px_warm_state"]=ws
    result=base_calc(final_trial)
    result["solve_basis"]="product"
    result["target_product_flow"]=target_user
    result["solved_feed_pressure"]=result["membrane_pressure_1"]
    result["pressure_solve_iterations"]=iterations
    result["pressure_solve_evaluations"]=eval_count
    result["solver_method"]="smart bracket + physics-seeded adaptive + safeguarded secant"
    result["pressure_search_backend"]=pressure_search_backend
    result["pressure_seed_bar"]=current_bar
    result["pressure_seed_source"]=seed_source
    result["pressure_seed_basis"]=(seed_info or rule_seed_info or {}).get("basis")
    result["pressure_seed_details"]=dict(seed_info or rule_seed_info or {}); result["pressure_seed_details"]["warm_start_source"]=seed_source if warm_info is not None else None
    result["engineering_rule_seed_bar"]=rule_seed_bar
    result["engineering_rule_seed_details"]=rule_seed_info
    result["solver_fallback_used"]=fallback_used or bool(result.get("px_coupling_fallback",False))
    result["product_flow_error"]=result["product_flow"]-target_user
    result["final_full_calculation"] = True
    return result



def _solve_pressure_for_recovery(data, base_calc):
    """Solve Stage-1 membrane feed pressure for a requested overall system recovery.

    Feed flow is held fixed. Overall recovery defines the total permeate target as
    Qp = R * Qf. The existing fully coupled pressure-for-product solver is then
    used so membrane transport, element pressure drop, Stage 2 behavior and ERD
    duty remain coupled.
    """
    if not _bool(data, "membrane_coupling", False):
        raise ValueError("Overall-recovery input requires RO membrane coupling to be ON.")
    target_r = _float(data, "target_recovery", None)
    if target_r is None:
        raise ValueError("Enter an overall recovery setpoint greater than zero.")
    # UI uses percent (e.g. 45.0). Fractional input (0.45) is also accepted
    # for backward/API compatibility.
    if target_r > 1.0:
        target_r /= 100.0
    if target_r <= 0 or target_r >= 1:
        raise ValueError("Enter an overall recovery setpoint between 0 and 100% (for example 45 for 45%).")
    fu = data.get("flow_unit", "m3/h")
    qfeed_user = float(data["feed_flow"])
    target_q_user = qfeed_user * target_r
    trial = dict(data)
    trial["target_product_flow"] = target_q_user
    trial["solve_basis"] = "product"
    result = _solve_pressure_for_product(trial, base_calc)
    result["solve_basis"] = "recovery"
    result["target_recovery"] = target_r
    result["target_product_flow"] = target_q_user
    result["recovery_error"] = result.get("recovery", 0.0) - target_r
    return result

def _with_tridirectional_solve(data, base_calc):
    basis=str(data.get("solve_basis","pressure")).lower()
    if basis in {"product","permeate","flow"}:
        return _solve_pressure_for_product(data, base_calc)
    if basis in {"recovery","r"}:
        return _solve_pressure_for_recovery(data, base_calc)
    result=base_calc(data)
    result["solve_basis"]="pressure"
    result["target_product_flow"]=result.get("product_flow")
    result["solved_feed_pressure"]=result.get("membrane_pressure_1")
    result["pressure_solve_iterations"]=0
    result["product_flow_error"]=0.0
    return result


def single_stage(data):
    prepared = _prepare_calculation_data(data)
    return _attach_acid_dosing(_with_tridirectional_solve(prepared, _single_stage_base), prepared)


def _generalized_interstage_turbo(prepared):
    """Evaluate an Interstage Turbo solution embedded in a 3-4 stage Base Plant.

    The stage count, membrane arrays and requested interstage boosts are inherited
    from Plant Design Basis.  At least one interstage location must be configured
    as Turbocharger or Turbocharger + Booster Pump.  The existing multistage
    hydraulic-energy allocator remains authoritative, including the Qtr/Qpf > 0.20
    hard gate and pump supplementation when ``turbo_pump`` is selected.
    """
    n = _multistage_count(prepared)
    if n < 3:
        raise ValueError("Generalized Interstage Turbo requires at least three RO stages; two-stage designs use the dedicated legacy Interstage Turbo solver.")
    turbo_positions = [i for i in range(2, n + 1) if _interstage_equipment(prepared, i) in {"turbo", "turbo_pump"}]
    if not turbo_positions:
        raise ValueError("Interstage Turbo requires at least one interstage location configured as Turbocharger or Turbocharger + Booster Pump.")
    result = _multistage_core(prepared)
    details = []
    for i in turbo_positions:
        details.append({
            "from_stage": i - 1,
            "to_stage": i,
            "equipment": _interstage_equipment(prepared, i),
            "qpf": result.get(f"stage{i}_interstage_turbo_pump_flow"),
            "qtr": result.get(f"stage{i}_interstage_turbo_turbine_flow"),
            "reject_ratio": result.get(f"stage{i}_interstage_reject_ratio"),
            "hydraulic_match": result.get(f"stage{i}_interstage_turbo_suitability"),
            "required_hydraulic_kw": result.get(f"stage{i}_interstage_required_hydraulic_kw"),
            "turbo_hydraulic_kw": result.get(f"stage{i}_interstage_turbo_hydraulic_kw"),
            "booster_wire_kw": result.get(f"stage{i}_interstage_booster_wire_kw"),
        })
    result["generalized_interstage_turbo"] = True
    result["interstage_turbo_positions"] = details
    result["interstage_turbo_count"] = len(details)
    return result


def interstage(data):
    prepared = _prepare_calculation_data(data)
    if int(float(prepared.get("stage_count", 2) or 2)) > 2 or _bool(prepared, "generalized_interstage_turbo", False):
        return _attach_acid_dosing(_generalized_interstage_turbo(prepared), prepared)
    return _attach_acid_dosing(_with_tridirectional_solve(prepared, _interstage_base), prepared)




def _generalized_biturbo(prepared):
    """Evaluate a BiTurbo arrangement embedded in a 3-4 stage base plant.

    The membrane topology is inherited from Plant Design Basis.  Two or more
    interstage locations must be configured as Turbocharger or Turbocharger +
    Booster Pump.  Each turbo is screened using its own canonical Qtr/Qpf ratio
    and the local feed TDS at its pump-side stage inlet.
    """
    n=_multistage_count(prepared)
    if n < 3:
        raise ValueError("Generalized multistage BiTurbo requires at least three RO stages.")
    turbo_positions=[i for i in range(2,n+1) if _interstage_equipment(prepared,i) in {"turbo","turbo_pump"}]
    if len(turbo_positions) < 2:
        raise ValueError(
            "BiTurbo requires at least two turbocharger hydraulic positions. "
            "Select Turbocharger or Turbocharger + Booster Pump at two interstage locations."
        )
    result=_multistage_core(prepared)
    details=[]
    for i in turbo_positions:
        tds=float(result.get(f"stage{i}_feed_tds_ppm",0.0) or 0.0)
        rr=float(result.get(f"stage{i}_interstage_reject_ratio",0.0) or 0.0)
        qpf=result.get(f"stage{i}_interstage_turbo_pump_flow")
        qtr=result.get(f"stage{i}_interstage_turbo_turbine_flow")
        if tds < BITURBO_MIN_LOCAL_TDS_MG_L:
            raise ValueError(
                f"BiTurbo turbocharger at Stage {i-1} → {i} is disabled because the pump-side feed TDS is "
                f"{tds:,.0f} mg/L, below the 30,000 mg/L screening threshold."
            )
        # _multistage_base already enforces the hard RR gate while allocating energy.
        if rr <= TURBO_MIN_REJECT_RATIO + 1e-12:
            raise ValueError(
                f"BiTurbo turbocharger at Stage {i-1} → {i} is disabled because Reject Ratio Qtr/Qpf = {rr:.3f} "
                "is at or below 0.20."
            )
        details.append({
            "from_stage":i-1,"to_stage":i,"pump_side_feed_tds_mg_l":tds,
            "qpf":qpf,"qtr":qtr,"reject_ratio":rr,
            "reject_ratio_status":turbo_reject_ratio_status(rr),
            "equipment":_interstage_equipment(prepared,i),
        })
    result["generalized_biturbo"] = True
    result["biturbo_turbo_count"] = len(details)
    result["biturbo_turbo_positions"] = details
    result["biturbo_tds_screen_status"] = "candidate"
    result["biturbo_screen_tds_mg_l"] = min(x["pump_side_feed_tds_mg_l"] for x in details)
    result["biturbo_tds_screen_note"] = (
        "Each selected turbocharger position satisfies the 30,000 mg/L local pump-side feed TDS screen and the "
        "Qtr/Qpf > 0.20 hard reject-ratio gate. Peak hydraulic matching is around Qtr/Qpf = 0.65–0.70; "
        "the calculated hydraulic-energy balance remains the final feasibility check."
    )
    return result

def biturbo(data):
    prepared = _prepare_calculation_data(data)
    if int(float(prepared.get("stage_count",2) or 2)) >= 3 or _bool(prepared,"generalized_biturbo",False):
        return _attach_acid_dosing(_generalized_biturbo(prepared), prepared)
    # Legacy one/two-stage BiTurbo uses a feed turbo plus an interstage turbo.
    # Both turbochargers retain their own Qtr/Qpf gate in _biturbo_base.
    tds = float(prepared.get("analysis_tds", prepared.get("feed_tds", 0.0)) or 0.0)
    if 0.0 < tds < 30000.0:
        raise ValueError(
            f"BiTurbo is disabled because system feed TDS is {tds:,.0f} mg/L, below the 30,000 mg/L minimum screening threshold."
        )
    result = _with_tridirectional_solve(prepared, _biturbo_base)
    stage_feed_tds = []
    for i in (1, 2):
        comp = result.get(f"stage{i}_feed_composition_mg_l")
        if isinstance(comp, dict) and comp:
            stage_feed_tds.append(total_tds_mg_l(comp))
    if stage_feed_tds and min(stage_feed_tds) < 30000.0:
        raise ValueError(
            f"BiTurbo is disabled because a stage feed TDS is {min(stage_feed_tds):,.0f} mg/L, below the 30,000 mg/L minimum screening threshold."
        )
    fu = prepared.get("flow_unit", "m3/h")
    pu = prepared.get("pressure_unit", "bar")
    try:
        q1 = flow_to_m3h(float(result.get("reject_flow_1", 0.0) or 0.0), fu)
        q2 = flow_to_m3h(float(result.get("reject_flow_2", 0.0) or 0.0), fu)
        qf = flow_to_m3h(float(result.get("feed_flow", 0.0) or 0.0), fu)
        dp_inter = pressure_to_bar(float(result.get("interstage_turbine_dp", 0.0) or 0.0), pu)
        dp_feed = pressure_to_bar(float(result.get("feed_turbine_dp", 0.0) or 0.0), pu)
        boost_feed = pressure_to_bar(float(result.get("feed_turbo_boost", 0.0) or 0.0), pu)
        boost_inter = pressure_to_bar(float(result.get("interstage_boost", 0.0) or 0.0), pu)
        result["biturbo_interstage_source_hydraulic_kw"] = max(0.0, q2 * dp_inter / 36.0)
        result["biturbo_interstage_boost_hydraulic_kw"] = max(0.0, q1 * boost_inter / 36.0)
        result["biturbo_feed_source_hydraulic_kw"] = max(0.0, q1 * dp_feed / 36.0)
        result["biturbo_feed_boost_hydraulic_kw"] = max(0.0, qf * boost_feed / 36.0)
    except (TypeError, ValueError, KeyError):
        pass
    result["biturbo_screen_tds_mg_l"] = tds
    result["biturbo_tds_screen_status"] = "candidate"
    result["biturbo_tds_screen_note"] = (
        "Feed and Stage 2 inlet TDS satisfy the 30,000 mg/L legacy BiTurbo screening threshold. "
        "The calculated flow/pressure hydraulic-energy balance remains the governing feasibility check."
    )
    return _attach_acid_dosing(result, prepared)


def pressure_exchanger(data):
    prepared = _prepare_calculation_data(data)
    prepared["calculation_workspace"] = "px"
    use_multi = int(float(prepared.get("stage_count",1) or 1)) > 1 or _bool(prepared,"plant_solution",False)
    base = _multistage_px_base if use_multi else _pressure_exchanger_base
    return _attach_acid_dosing(_with_tridirectional_solve(prepared, base), prepared)


def interstage_pressure_exchanger(data):
    """Dedicated 2–4 stage isobaric-chamber workspace.

    The final-stage concentrate is always the IC high-pressure source.  The
    pressure balance automatically selects booster, direct connection or
    throttling at the IC feed branch, including the boosted-BWRO condition where
    final brine pressure exceeds the Stage-1 header requirement.
    """
    prepared = _prepare_calculation_data(data)
    n = int(float(prepared.get("stage_count", 2) or 2))
    if n < 2:
        raise ValueError("Interstage Isobaric Chamber requires at least two RO stages.")
    prepared["stage_count"] = min(4, n)
    prepared["plant_solution"] = True
    prepared["calculation_workspace"] = "interstage_px"
    return _attach_acid_dosing(_with_tridirectional_solve(prepared, _multistage_px_base), prepared)




def _rounded_motor_nameplate_kw(shaft_kw, sizing_factor=1.10, frame_kw=50.0):
    duty=max(0.0,float(shaft_kw))*max(1.0,float(sizing_factor))
    frame=max(1.0,float(frame_kw))
    return math.ceil(duty/frame-1e-12)*frame if duty>0 else 0.0


def _part_load_motor_efficiency(nominal_eff, load_factor, k_partload=0.06):
    eta=max(1e-6,min(1.0,float(nominal_eff)))
    lf=max(0.0,float(load_factor))
    k=max(0.0,float(k_partload))
    return max(1e-6,min(1.0,eta*(1.0-k*(1.0-lf)**2)))


def _base_plant_for_mechanical_erd(data):
    """Run the inherited membrane plant and return it on the user's display units.

    DWEER and Pelton are sibling ERD solutions.  They do not resize the membrane
    array or change the user's stage topology; they consume the Base Plant's
    calculated feed/product/final-brine duty and then replace the HP-section
    energy architecture with the selected recovery device.
    """
    d=dict(data)
    # DWEER and Pelton are post-RO energy architectures. When the workspace was
    # generated from Plant Design, consume the exact converged Base Plant result
    # instead of solving the membrane train again. Re-solving here can select a
    # different pressure bracket (or fail to bracket at all) even though the Base
    # Plant duty is already valid, which breaks like-for-like ERD comparison.
    if _bool(d,"generated_from_base_plant",False):
        inherited=d.get("_base_plant_result")
        if isinstance(inherited,dict):
            required=("feed_flow","product_flow","membrane_pressure_1")
            if all(inherited.get(k) not in (None,"") for k in required):
                n=max(1,int(inherited.get("stage_count",1) or 1))
                if inherited.get(f"reject_pressure_{n}") not in (None,""):
                    snap=dict(inherited)
                    src_fu=str(snap.get("flow_unit") or d.get("flow_unit") or "m3/h")
                    src_pu=str(snap.get("pressure_unit") or d.get("pressure_unit") or "bar")
                    dst_fu=str(d.get("flow_unit") or src_fu); dst_pu=str(d.get("pressure_unit") or src_pu)
                    flow_keys={"feed_flow","product_flow","reject_flow_final"}
                    pressure_keys={"suction_pressure","permeate_pressure","pretreatment_discharge_pressure","membrane_pressure_1"}
                    for i in range(1,n+1):
                        flow_keys.update({f"reject_flow_{i}",f"stage{i}_feed_flow",f"stage{i}_permeate_flow"})
                        pressure_keys.update({f"membrane_pressure_{i}",f"reject_pressure_{i}"})
                    if src_fu!=dst_fu:
                        for k in flow_keys:
                            if isinstance(snap.get(k),(int,float)):
                                snap[k]=flow_from_m3h(flow_to_m3h(float(snap[k]),src_fu),dst_fu)
                    if src_pu!=dst_pu:
                        for k in pressure_keys:
                            if isinstance(snap.get(k),(int,float)):
                                snap[k]=pressure_from_bar(pressure_to_bar(float(snap[k]),src_pu),dst_pu)
                    snap["flow_unit"]=dst_fu;snap["pressure_unit"]=dst_pu
                    return snap
        d["design_mode"]="manual"
    return _multistage_core(d)


def _dweer_base(data):
    fu,pu=data.get("flow_unit","m3/h"),data.get("pressure_unit","bar")
    base=_base_plant_for_mechanical_erd(data)
    n=max(1,int(base.get("stage_count",1) or 1))
    qf=flow_to_m3h(base["feed_flow"],fu); qp=flow_to_m3h(base["product_flow"],fu)
    qb=flow_to_m3h(base.get("reject_flow_final",base.get(f"reject_flow_{n}")),fu)
    pfeed=pressure_to_bar(base["membrane_pressure_1"],pu)
    pbrine=pressure_to_bar(base.get(f"reject_pressure_{n}"),pu)
    psuc=pressure_to_bar(base.get("suction_pressure",data.get("suction_pressure",0)),pu)
    if min(qf,qp,qb)<=0: raise ValueError("DWEER requires positive feed, permeate and final-brine flows.")
    if pbrine<=0: raise ValueError("DWEER requires positive final-stage brine pressure.")

    over=max(0.0,float(data.get("dweer_overflush_fraction",0.03) or 0.0))
    mix=max(0.0,min(0.20,float(data.get("dweer_mixing_fraction",0.02) or 0.0)))
    hp_loss=max(0.0,pressure_to_bar(float(data.get("dweer_hp_side_dp",pressure_from_bar(0.9,pu)) or pressure_from_bar(0.9,pu)),pu))
    lp_loss=max(0.0,pressure_to_bar(float(data.get("dweer_lp_side_dp",pressure_from_bar(0.7,pu)) or pressure_from_bar(0.7,pu)),pu))
    qmodule=max(1e-9,flow_to_m3h(float(data.get("dweer_module_flow",flow_from_m3h(200.0,fu)) or flow_from_m3h(200.0,fu)),fu))
    apply_mix=_bool(data,"dweer_apply_mixing_penalty",True)

    cf=float(base.get("stage1_feed_tds_ppm",data.get("feed_tds",0.0)) or 0.0)
    cb=float(base.get(f"stage{n}_concentrate_tds_ppm",0.0) or 0.0)
    q_hp_out=qb
    q_flush=qb*over; q_lp_in=qb+q_flush; q_hpp=max(0.0,qf-q_hp_out); q_lp_tot=qf+q_flush
    cf_mix=cf+mix*(cb-cf)
    cf_memb=(q_hp_out*cf_mix+q_hpp*cf)/max(qf,1e-12)
    dtds=max(0.0,cf_memb-cf)
    temp=float(data.get("temperature_c",25.0) or 25.0)
    recovery=qp/qf
    cf_avg=math.log(1.0/max(1e-12,1.0-recovery))/max(recovery,1e-12)
    osm_k=max(0.0,float(data.get("dweer_osmotic_k_bar_per_g_l",0.77) or 0.77))
    dpi=osm_k*(dtds/1000.0)*((temp+273.15)/298.15)*cf_avg if apply_mix else 0.0
    pf_a=pfeed+dpi
    pb_a=pbrine+dpi
    p_hp_out=max(0.0,pb_a-hp_loss)
    dp_boost=max(0.0,pf_a-p_hp_out)
    dp_throttle=max(0.0,p_hp_out-pf_a)
    p_lp_out=max(0.0,psuc-lp_loss)
    eta_erd=(q_hp_out*p_hp_out + q_lp_in*p_lp_out)/max(qb*pb_a + q_lp_in*psuc,1e-12)
    nmodules=int(math.ceil(qb/qmodule))

    peff=max(1e-6,float(data.get("pump_eff",0.85) or 0.85)); meff=max(1e-6,float(data.get("motor_eff",0.965) or 0.965)); veff=_vfd_eff(data,"vfd_eff","pump_no_vfd")
    bp_eff=max(1e-6,float(data.get("dweer_booster_pump_eff",data.get("booster_pump_eff",0.80)) or 0.80))
    bp_meff=max(1e-6,float(data.get("dweer_booster_motor_eff",data.get("booster_motor_eff",0.955)) or 0.955)); bp_veff=max(1e-6,float(data.get("dweer_booster_vfd_eff",0.97) or 0.97))
    lp_eff=max(1e-6,float(data.get("dweer_lp_pump_eff",0.82) or 0.82)); lp_meff=max(1e-6,float(data.get("dweer_lp_motor_eff",0.94) or 0.94))
    k_part=max(0.0,float(data.get("erd_motor_partload_k",0.06) or 0.06)); sf=max(1.0,float(data.get("erd_motor_sizing_factor",1.10) or 1.10))
    hpp_hyd=q_hpp*max(0.0,pf_a-psuc)/36.0; hpp_shaft=hpp_hyd/peff
    hpp_name=_rounded_motor_nameplate_kw(hpp_shaft,sf,float(data.get("erd_hpp_motor_frame_kw",50.0) or 50.0)); hpp_lf=hpp_shaft/max(hpp_name,1e-12); hpp_motor_eff=_part_load_motor_efficiency(meff,hpp_lf,k_part); hpp_el=hpp_shaft/max(hpp_motor_eff*veff,1e-12)
    bp_hyd=q_hp_out*dp_boost/36.0; bp_shaft=bp_hyd/bp_eff
    bp_name=_rounded_motor_nameplate_kw(bp_shaft,sf,float(data.get("erd_booster_motor_frame_kw",10.0) or 10.0)); bp_lf=bp_shaft/max(bp_name,1e-12) if bp_name>0 else 0.0; bp_motor_eff=_part_load_motor_efficiency(bp_meff,bp_lf,k_part) if bp_name>0 else bp_meff; bp_el=bp_shaft/max(bp_motor_eff*bp_veff,1e-12)
    lp_hyd_overflush=q_flush*max(0.0,psuc)/36.0; lp_hyd_loss=q_lp_in*lp_loss/36.0; lp_el=(lp_hyd_overflush+lp_hyd_loss)/max(lp_eff*lp_meff,1e-12)
    inherited_interstage_kw=max(0.0,float(base.get("booster_kw",0.0) or 0.0))
    ro_kw=hpp_el+bp_el+lp_el+inherited_interstage_kw
    pret_kw=max(0.0,float(base.get("pretreatment_kw",0.0) or 0.0))
    recovered=q_hp_out*max(0.0,p_hp_out-psuc)/36.0
    available=qb*max(0.0,pb_a-psuc)/36.0

    result=dict(base); base_snapshot=dict(base)
    result.update({
        "erd_type":"DWEER","dweer_model_basis":"Positive-displacement work exchanger · workbook-calibrated screening model",
        "dweer_brine_in_flow":qb,"dweer_hp_feed_out_flow":q_hp_out,"dweer_overflush_flow":q_flush,"dweer_lp_feed_in_flow":q_lp_in,
        "dweer_drain_flow":q_lp_in,"dweer_hpp_makeup_flow":q_hpp,"dweer_total_lp_feed_flow":q_lp_tot,
        "dweer_mixing_fraction":mix,"dweer_feed_tds_after_exchange_mg_l":cf_mix,"dweer_blended_membrane_feed_tds_mg_l":cf_memb,
        "dweer_feed_tds_increase_mg_l":dtds,"dweer_mixing_osmotic_penalty_dp":dpi,"dweer_required_feed_pressure":pf_a,
        "dweer_brine_hp_in_pressure":pb_a,"dweer_hp_feed_out_pressure":p_hp_out,"dweer_hp_booster_dp":dp_boost,"dweer_throttle_dp":dp_throttle,
        "dweer_lp_out_pressure":p_lp_out,"dweer_device_efficiency":eta_erd,"dweer_modules_required":nmodules,"dweer_module_design_flow":qmodule,
        "dweer_hpp_hydraulic_kw":hpp_hyd,"dweer_hpp_shaft_kw":hpp_shaft,"dweer_hpp_motor_nameplate_kw":hpp_name,"dweer_hpp_motor_load_factor":hpp_lf,"dweer_hpp_motor_eff":hpp_motor_eff,"dweer_hpp_electric_kw":hpp_el,
        "dweer_booster_hydraulic_kw":bp_hyd,"dweer_booster_shaft_kw":bp_shaft,"dweer_booster_motor_nameplate_kw":bp_name,"dweer_booster_motor_load_factor":bp_lf,"dweer_booster_motor_eff":bp_motor_eff,"dweer_booster_electric_kw":bp_el,
        "dweer_lp_increment_electric_kw":lp_el,"dweer_recovered_hydraulic_kw":recovered,"dweer_available_brine_hydraulic_kw":available,"dweer_recovered_fraction":recovered/max(available,1e-12),
        "dweer_inherited_interstage_booster_kw":inherited_interstage_kw,
        "hpp_kw":hpp_el,"electric_kw":ro_kw,"ro_sec":ro_kw/qp,"pump_sec":ro_kw/qp,"pretreatment_kw":pret_kw,"pretreatment_sec":pret_kw/qp,"total_sec":ro_kw/qp+pret_kw/qp,
        "dweer_sec":ro_kw/qp,"dweer_energy_saving_vs_conventional_kw":max(0.0,float(base.get("electric_kw",0.0) or 0.0)-ro_kw),
        "dweer_note":"DWEER module flow is a sizing-screen input unless replaced with current vendor data. Mixing/overflush and pressure losses follow the attached comparison calculator basis."
    })
    changed={k:v for k,v in result.items() if k not in base_snapshot or base_snapshot.get(k)!=v}
    out=dict(base_snapshot); out.update(display(changed,fu,pu))
    return out


def dweer(data):
    prepared=_prepare_calculation_data(data)
    return _attach_acid_dosing(_dweer_base(prepared),prepared)


def _pelton_base(data):
    fu,pu=data.get("flow_unit","m3/h"),data.get("pressure_unit","bar")
    base=_base_plant_for_mechanical_erd(data)
    n=max(1,int(base.get("stage_count",1) or 1))
    qf=flow_to_m3h(base["feed_flow"],fu); qp=flow_to_m3h(base["product_flow"],fu)
    qb=flow_to_m3h(base.get("reject_flow_final",base.get(f"reject_flow_{n}")),fu)
    pfeed=pressure_to_bar(base["membrane_pressure_1"],pu); psuc=pressure_to_bar(base.get("suction_pressure",data.get("suction_pressure",0)),pu); pb=pressure_to_bar(base.get(f"reject_pressure_{n}"),pu)
    pdis=max(0.0,pressure_to_bar(float(data.get("pelton_discharge_pressure",pressure_from_bar(0.5,pu)) or pressure_from_bar(0.5,pu)),pu))
    if pb<=pdis: raise ValueError("Pelton final-brine pressure must be above turbine discharge pressure.")
    peff=max(1e-6,float(data.get("pump_eff",0.85) or 0.85)); meff=max(1e-6,float(data.get("motor_eff",0.965) or 0.965)); veff=_vfd_eff(data,"vfd_eff","pump_no_vfd")
    eta_pel=max(0.0,min(1.0,float(data.get("pelton_turbine_eff",0.87) or 0.87))); eta_shaft=max(0.0,min(1.0,float(data.get("pelton_shaft_eff",0.99) or 0.99)))
    nshaft=max(1.0,float(data.get("pelton_shaft_speed_rpm",1780.0) or 1780.0)); jets=max(1,int(round(float(data.get("pelton_jets",1) or 1))))
    cv=max(0.01,float(data.get("pelton_nozzle_cv",0.98) or 0.98)); phi=max(0.05,float(data.get("pelton_speed_ratio",0.47) or 0.47))
    k_part=max(0.0,float(data.get("erd_motor_partload_k",0.06) or 0.06)); sf=max(1.0,float(data.get("erd_motor_sizing_factor",1.10) or 1.10)); frame=max(1.0,float(data.get("erd_hpp_motor_frame_kw",50.0) or 50.0))
    sizing_basis=str(data.get("pelton_motor_sizing_basis","full_start") or "full_start").lower()
    dp_hpp=max(0.0,pfeed-psuc); whyd_hpp=qf*dp_hpp/36.0; wsh_hpp=whyd_hpp/peff
    dp_pel=max(0.0,pb-pdis); whyd_pel=qb*dp_pel/36.0; wsh_pel=whyd_pel*eta_pel; delivered=wsh_pel*eta_shaft
    net_shaft=max(0.0,wsh_hpp-delivered); sizing_duty=wsh_hpp if sizing_basis in {"2","full","full_start","startup","start_up"} else net_shaft
    motor_name=_rounded_motor_nameplate_kw(sizing_duty,sf,frame); lf=net_shaft/max(motor_name,1e-12) if motor_name>0 else 0.0; actual_meff=_part_load_motor_efficiency(meff,lf,k_part); motor_el=net_shaft/max(actual_meff*veff,1e-12)
    inherited_interstage_kw=max(0.0,float(base.get("booster_kw",0.0) or 0.0)); ro_kw=motor_el+inherited_interstage_kw; pret_kw=max(0.0,float(base.get("pretreatment_kw",0.0) or 0.0))
    # Runner/head sizing from the attached calculator.
    sg_user=data.get("pelton_brine_sg","")
    if sg_user not in (None,""):
        sg=max(0.5,float(sg_user))
    else:
        cb=float(base.get(f"stage{n}_concentrate_tds_ppm",data.get("feed_tds",35000.0)) or 35000.0); temp=float(data.get("temperature_c",25.0) or 25.0); sg=solution_specific_gravity(cb,temp)
    hnet=dp_pel*10.1972/max(sg,1e-12); c1=cv*math.sqrt(max(0.0,2.0*9.81*hnet)); u=phi*c1; diameter=60.0*u/(math.pi*nshaft)
    qjet=qb/jets/3600.0; ajet=qjet/max(c1,1e-12); djet=math.sqrt(max(0.0,4.0*ajet/math.pi))*1000.0; mratio=diameter*1000.0/max(djet,1e-12)
    buckets=int(round(15.0+mratio/2.0)); bwidth=3.2*djet; bdepth=1.0*djet; ns=nshaft*math.sqrt(max(wsh_pel/jets,0.0))/max(hnet,1e-12)**1.25; runaway=1.8*nshaft
    tq_pump=9550.0*wsh_hpp/nshaft; tq_pel=9550.0*delivered/nshaft; tq_mot=9550.0*net_shaft/nshaft
    result=dict(base); base_snapshot=dict(base)
    result.update({
        "erd_type":"Pelton Turbine","pelton_model_basis":"Common-shaft Pelton + HP pump · workbook-calibrated screening model",
        "pelton_hpp_flow":qf,"pelton_hpp_dp":dp_hpp,"pelton_hpp_hydraulic_kw":whyd_hpp,"pelton_hpp_shaft_kw":wsh_hpp,
        "pelton_brine_flow":qb,"pelton_brine_in_pressure":pb,"pelton_discharge_pressure":pdis,"pelton_turbine_dp":dp_pel,"pelton_available_brine_hydraulic_kw":whyd_pel,
        "pelton_runner_shaft_kw":wsh_pel,"pelton_shaft_delivered_kw":delivered,"pelton_net_motor_shaft_kw":net_shaft,"pelton_pump_shaft_share":delivered/max(wsh_hpp,1e-12),
        "pelton_motor_sizing_duty_kw":sizing_duty,"pelton_motor_nameplate_kw":motor_name,"pelton_motor_load_factor":lf,"pelton_motor_eff":actual_meff,"pelton_motor_electric_kw":motor_el,
        "pelton_recovered_fraction":delivered/max(whyd_pel,1e-12),"pelton_turbine_eff":eta_pel,"pelton_shaft_eff":eta_shaft,"pelton_brine_sg":sg,
        "pelton_pump_torque_nm":tq_pump,"pelton_runner_torque_nm":tq_pel,"pelton_motor_torque_nm":tq_mot,"pelton_pump_side_shaft_torque_nm":tq_pump,"pelton_startup_torque_nm":tq_pump,
        "pelton_net_head_m":hnet,"pelton_jet_velocity_m_s":c1,"pelton_runner_velocity_m_s":u,"pelton_runner_diameter_m":diameter,"pelton_jet_flow_m3_s":qjet,"pelton_jet_area_m2":ajet,"pelton_jet_diameter_mm":djet,
        "pelton_jet_ratio":mratio,"pelton_jet_ratio_status":"OK" if 10.0<=mratio<=20.0 else ("Review" if 8.0<=mratio<=25.0 else "Outside preferred screening range"),
        "pelton_bucket_count":buckets,"pelton_bucket_width_mm":bwidth,"pelton_bucket_depth_mm":bdepth,"pelton_specific_speed":ns,"pelton_specific_speed_status":"OK" if 4.0<=ns<=30.0 else "Review","pelton_runaway_speed_rpm":runaway,
        "pelton_inherited_interstage_booster_kw":inherited_interstage_kw,
        "hpp_kw":motor_el,"electric_kw":ro_kw,"ro_sec":ro_kw/qp,"pump_sec":ro_kw/qp,"pretreatment_kw":pret_kw,"pretreatment_sec":pret_kw/qp,"total_sec":ro_kw/qp+pret_kw/qp,"pelton_sec":ro_kw/qp,
        "pelton_energy_saving_vs_conventional_kw":max(0.0,float(base.get("electric_kw",0.0) or 0.0)-ro_kw),
        "pelton_note":"Common-shaft screening follows the attached calculator. The pump-side shaft extension/rotor carries full HP-pump torque; verify runner/nozzle/shaft design with the equipment vendor."
    })
    changed={k:v for k,v in result.items() if k not in base_snapshot or base_snapshot.get(k)!=v}
    out=dict(base_snapshot); out.update(display(changed,fu,pu))
    return out


def pelton(data):
    prepared=_prepare_calculation_data(data)
    return _attach_acid_dosing(_pelton_base(prepared),prepared)


CALCS = {"single": single_stage, "multistage": multistage, "interstage": interstage, "biturbo": biturbo, "px": pressure_exchanger, "interstage_px": interstage_pressure_exchanger, "dweer": dweer, "pelton": pelton}
