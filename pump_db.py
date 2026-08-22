"""Vertical Multistage Centrifugal Pump (VCMP) performance database.

The database is derived from the user-supplied 60 Hz optimizer workbook.  The
module deliberately keeps the source nomenclature generic (VCMP) and applies
standard affinity laws so a selected curve can be evaluated at VFD speed.

This is a preliminary hydraulic/energy selector. Final manufacturer checks for
NPSH, minimum continuous stable flow, pressure rating, materials, temperature,
mechanical seal, motor rating, and approved VFD range remain mandatory.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "vcmp_pumps.json"
G = 9.80665
# Current VCMP dataset represents standard 60 Hz two-pole vertical multistage
# pump service. Use 3500 rpm as the preliminary full-speed shaft basis until a
# verified model-specific shaft speed is added to the database or entered by the user.
DEFAULT_REFERENCE_RPM_60 = 3500.0


def _load():
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    return data.get("meta", {}), data.get("pumps", [])


META, PUMPS = _load()
BY_SOURCE_ID = {int(r["source_id"]): r for r in PUMPS}


def list_pumps():
    return list(PUMPS)


def _poly4(coeff, x):
    a, b, c, d = [float(v) for v in coeff]
    x = float(x)
    return ((a * x + b) * x + c) * x + d


def head_m(row, flow_m3h, speed_ratio=1.0):
    """Pump head at flow and speed ratio using the workbook affinity transform."""
    r = max(1e-9, float(speed_ratio))
    q = float(flow_m3h)
    a, b, c, d = [float(v) for v in row["qh_coeff"]]
    return (a / r) * q**3 + b * q**2 + (c * r) * q + d * r**2


def raw_efficiency(row, flow_m3h, speed_ratio=1.0):
    """Unadjusted pump hydraulic efficiency as a fraction at homologous flow."""
    r = max(1e-9, float(speed_ratio))
    q60 = float(flow_m3h) / r
    return _poly4(row["eta_coeff_pct"], q60) / 100.0


def adjusted_efficiency(row, flow_m3h, speed_ratio=1.0,
                        reduced_impeller_penalty_pp=2.0,
                        low_speed_derate_pp_per_10pct=0.0):
    eta = 100.0 * raw_efficiency(row, flow_m3h, speed_ratio)
    if int(row.get("reduced_impellers", 0) or 0) > 0:
        eta -= float(reduced_impeller_penalty_pp)
    speed_loss = max(0.0, 1.0 - float(speed_ratio))
    eta -= float(low_speed_derate_pp_per_10pct) * (speed_loss / 0.10)
    return eta / 100.0


def _head_to_bar(head_m_value, density_kg_m3):
    return float(density_kg_m3) * G * float(head_m_value) / 100000.0


def _bar_to_head(dp_bar, density_kg_m3):
    return float(dp_bar) * 100000.0 / max(float(density_kg_m3) * G, 1e-12)


def _solve_speed_ratio(row, flow_m3h, required_head_m, min_ratio, max_ratio):
    """Return operating ratio and actual head, honoring a minimum VFD speed.

    If minimum speed already produces more head than required, the minimum speed
    is returned and the excess head is intentionally retained so oversized
    pumps are penalized in wire power, matching the supplied optimizer logic.
    """
    q = float(flow_m3h)
    hreq = float(required_head_m)
    lo, hi = float(min_ratio), float(max_ratio)
    hlo = head_m(row, q, lo)
    hhi = head_m(row, q, hi)
    if hhi + 1e-9 < hreq:
        return None
    if hlo >= hreq:
        return lo, hlo, True
    # For centrifugal pumps at a fixed flow the transformed curve should be
    # monotone over the approved VFD interval. Bisection is more robust than a
    # fixed-count Newton method for a heterogeneous 431-curve database.
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        hm = head_m(row, q, mid)
        if hm >= hreq:
            hi = mid
        else:
            lo = mid
    r = 0.5 * (lo + hi)
    return r, head_m(row, q, r), False


def evaluate_pump(row, flow_m3h, required_dp_bar, density_kg_m3=998.0,
                  motor_eff=0.95, vfd_eff=0.98,
                  min_vfd_hz=40.0, max_vfd_hz=60.0,
                  reduced_impeller_penalty_pp=2.0,
                  low_speed_derate_pp_per_10pct=0.0,
                  reference_rpm_60=None):
    q = float(flow_m3h)
    rho = max(1.0, float(density_kg_m3))
    if q <= 0 or float(required_dp_bar) <= 0:
        return None
    min_ratio = float(min_vfd_hz) / 60.0
    max_ratio = float(max_vfd_hz) / 60.0
    if min_ratio <= 0 or max_ratio < min_ratio:
        return None
    hreq = _bar_to_head(required_dp_bar, rho)
    solved = _solve_speed_ratio(row, q, hreq, min_ratio, max_ratio)
    if solved is None:
        return None
    ratio, actual_head, min_speed_limited = solved
    q60 = q / max(ratio, 1e-12)
    qmin = float(row.get("min_flow_m3h_60hz", 0.0) or 0.0)
    qmax = float(row.get("max_flow_m3h_60hz", 0.0) or 0.0)
    if q60 < qmin - 1e-9 or q60 > qmax + 1e-9:
        return None
    eta_raw = raw_efficiency(row, q, ratio)
    eta = adjusted_efficiency(row, q, ratio, reduced_impeller_penalty_pp,
                              low_speed_derate_pp_per_10pct)
    if not (0.05 < eta <= 0.95) or not math.isfinite(eta):
        return None
    actual_dp = _head_to_bar(actual_head, rho)
    hydraulic_kw = rho * G * (q / 3600.0) * actual_head / 1000.0
    shaft_kw = hydraulic_kw / eta
    wire_kw = shaft_kw / max(float(motor_eff) * float(vfd_eff), 1e-12)
    rpm = None
    torque_nm = None
    rpm_basis = "user" if reference_rpm_60 not in (None, "") else "vcmp_default_3500rpm"
    ref_rpm = reference_rpm_60 if reference_rpm_60 not in (None, "") else DEFAULT_REFERENCE_RPM_60
    try:
        ref_rpm = float(ref_rpm)
        rpm = ref_rpm * ratio
        if rpm > 1e-9:
            torque_nm = shaft_kw * 1000.0 / (2.0 * math.pi * rpm / 60.0)
    except (TypeError, ValueError):
        ref_rpm = None
        rpm = torque_nm = None
        rpm_basis = "unavailable"
    shutoff_head = max(0.0, head_m(row, 0.0, ratio))
    shutoff_dp = _head_to_bar(shutoff_head, rho)
    bep = row.get("bep_flow_m3h_60hz")
    flow_bep_ratio = None
    if bep not in (None, 0, 0.0):
        flow_bep_ratio = q60 / float(bep)
    return {
        "source_id": int(row["source_id"]),
        "product_family": row["product_family"],
        "stage_config": row["stage_config"],
        "pump_series": row.get("pump_series", "VCMP"),
        "reduced_impellers": int(row.get("reduced_impellers", 0) or 0),
        "flow_m3h": q,
        "required_dp_bar": float(required_dp_bar),
        "actual_dp_bar": actual_dp,
        "required_head_m": hreq,
        "actual_head_m": actual_head,
        "head_margin_pct": 100.0 * (actual_head / max(hreq, 1e-12) - 1.0),
        "speed_ratio": ratio,
        "frequency_hz": 60.0 * ratio,
        "reference_rpm_60": ref_rpm,
        "speed_rpm": rpm,
        "rpm_basis": rpm_basis,
        "shutoff_head_m": shutoff_head,
        "shutoff_dp_bar": shutoff_dp,
        "equivalent_flow_60hz_m3h": q60,
        "raw_efficiency": eta_raw,
        "pump_efficiency": eta,
        "motor_efficiency": float(motor_eff),
        "vfd_efficiency": float(vfd_eff),
        "overall_wire_efficiency": eta * float(motor_eff) * float(vfd_eff),
        "hydraulic_kw": hydraulic_kw,
        "shaft_kw": shaft_kw,
        "wire_kw": wire_kw,
        "sec_kwh_m3": wire_kw / q,
        "shaft_torque_nm": torque_nm,
        "min_speed_limited": bool(min_speed_limited),
        "flow_bep_ratio": flow_bep_ratio,
        "min_flow_60hz_m3h": qmin,
        "max_flow_60hz_m3h": qmax,
    }


def select_pump(flow_m3h, required_dp_bar, density_kg_m3=998.0,
                motor_eff=0.95, vfd_eff=0.98,
                min_vfd_hz=40.0, max_vfd_hz=60.0,
                flow_margin=0.05, head_margin=0.05,
                reduced_impeller_penalty_pp=2.0,
                low_speed_derate_pp_per_10pct=0.0,
                reference_rpm_60=None, top_n=5):
    """Select the lowest-wire-power feasible VCMP curve for one pump duty.

    The selected geometry must be able to cover the margin duty at the maximum
    approved VFD speed. Ranking and the returned operating efficiency are based
    on the actual process duty. No parallel-pump bank is invented here; if a
    single VCMP curve cannot cover the duty, the caller should retain its manual
    efficiency fallback or use a different pump family.
    """
    q = float(flow_m3h)
    dp = float(required_dp_bar)
    rho = max(1.0, float(density_kg_m3))
    if q <= 0 or dp <= 0:
        return {"ok": False, "reason": "Pump duty must have positive flow and differential pressure.", "options": []}
    design_q = q * (1.0 + max(0.0, float(flow_margin)))
    design_dp = dp * (1.0 + max(0.0, float(head_margin)))
    options = []
    for row in PUMPS:
        # Design-margin feasibility first.
        margin_eval = evaluate_pump(
            row, design_q, design_dp, rho, motor_eff, vfd_eff,
            min_vfd_hz, max_vfd_hz, reduced_impeller_penalty_pp,
            low_speed_derate_pp_per_10pct, reference_rpm_60,
        )
        if margin_eval is None:
            continue
        actual = evaluate_pump(
            row, q, dp, rho, motor_eff, vfd_eff,
            min_vfd_hz, max_vfd_hz, reduced_impeller_penalty_pp,
            low_speed_derate_pp_per_10pct, reference_rpm_60,
        )
        if actual is None:
            continue
        actual["design_margin_flow_m3h"] = design_q
        actual["design_margin_dp_bar"] = design_dp
        actual["design_margin_frequency_hz"] = margin_eval["frequency_hz"]
        actual["design_margin_head_m"] = margin_eval["actual_head_m"]
        options.append(actual)
    options.sort(key=lambda x: (x["wire_kw"], x["actual_dp_bar"], x["source_id"]))
    for i, op in enumerate(options, 1):
        op["selection_rank"] = i
    if not options:
        return {
            "ok": False,
            "reason": f"No single VCMP curve covers this flow/head duty within the configured {float(min_vfd_hz):g}–{float(max_vfd_hz):g} Hz VFD envelope and design margins.",
            "options": [],
            "database_records": len(PUMPS),
        }
    keep = options[:max(1, int(top_n))]
    return {
        "ok": True,
        "selected": keep[0],
        "options": keep,
        "database_records": len(PUMPS),
        "selection_basis": "Lowest actual wire power among curves that also cover the margin duty",
        "flow_margin": float(flow_margin),
        "head_margin": float(head_margin),
        "min_vfd_hz": float(min_vfd_hz),
        "max_vfd_hz": float(max_vfd_hz),
    }


def curve_points(source_id, speed_ratio, density_kg_m3=998.0,
                 motor_eff=0.95, vfd_eff=0.98,
                 reduced_impeller_penalty_pp=2.0,
                 low_speed_derate_pp_per_10pct=0.0,
                 reference_rpm_60=None, samples=25):
    row = BY_SOURCE_ID[int(source_id)]
    r = max(1e-9, float(speed_ratio))
    qmin = max(0.0, float(row.get("min_flow_m3h_60hz", 0.0) or 0.0) * r)
    qmax = max(qmin, float(row.get("max_flow_m3h_60hz", 0.0) or 0.0) * r)
    out = []
    for i in range(max(2, int(samples))):
        q = qmin + (qmax - qmin) * i / max(1, samples - 1)
        h = max(0.0, head_m(row, q, r))
        eta = adjusted_efficiency(row, q, r, reduced_impeller_penalty_pp,
                                  low_speed_derate_pp_per_10pct)
        dp = _head_to_bar(h, density_kg_m3)
        hyd = float(density_kg_m3) * G * (q / 3600.0) * h / 1000.0
        shaft = hyd / eta if eta > 0.05 else None
        wire = shaft / max(float(motor_eff) * float(vfd_eff), 1e-12) if shaft is not None else None
        ref_rpm = reference_rpm_60 if reference_rpm_60 not in (None, "") else DEFAULT_REFERENCE_RPM_60
        rpm = torque = None
        try:
            rpm = float(ref_rpm) * r
            if shaft is not None and rpm > 1e-9:
                torque = shaft * 1000.0 / (2.0 * math.pi * rpm / 60.0)
        except (TypeError, ValueError):
            rpm = torque = None
        out.append({
            "flow_m3h": q, "head_m": h, "pump_dp_bar": dp,
            "efficiency": eta if eta > 0 else None,
            "hydraulic_kw": hyd, "shaft_kw": shaft, "wire_kw": wire,
            "frequency_hz": 60.0 * r, "speed_ratio": r,
            "speed_rpm": rpm, "shaft_torque_nm": torque,
        })
    return out
