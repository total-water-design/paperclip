"""Suite-wide pump selection facade across VCMP, HHECP and PD pumps."""
from __future__ import annotations

import vcmp_pump
import hhecp_pump
import pd_pump


def _tag_vcmp(op):
    if not isinstance(op, dict):
        return op
    op.setdefault("technology", "VCMP")
    op.setdefault("model", f"{op.get('product_family', 'VCMP')} {op.get('stage_config', '')}".strip())
    op.setdefault("duty_units", 1)
    op.setdefault("installed_units", 1)
    if op.get("wire_kw") is not None:
        op.setdefault("wire_kw_per_pump", op.get("wire_kw"))
    return op


def list_shared_pumps():
    return {
        "vcmp": vcmp_pump.list_pumps(),
        "hhecp": list(hhecp_pump.MODELS),
        "pd": list(pd_pump.PUMPS),
    }


def select_pump(flow_m3h, required_dp_bar, density_kg_m3=998.0,
                motor_eff=0.95, vfd_eff=0.98,
                min_vfd_hz=30.0, max_vfd_hz=60.0,
                flow_margin=0.05, head_margin=0.05,
                reduced_impeller_penalty_pp=2.0,
                low_speed_derate_pp_per_10pct=0.0,
                reference_rpm_60=None, top_n=5,
                max_duty_units=10, available_inlet_bar=0.0,
                technologies=None):
    techs = {str(t).strip().lower() for t in (technologies or ("vcmp", "hhecp", "pd"))}
    options = []
    reasons = []

    if "vcmp" in techs:
        result = vcmp_pump.select_pump(
            flow_m3h, required_dp_bar, density_kg_m3, motor_eff, vfd_eff,
            min_vfd_hz, max_vfd_hz, flow_margin, head_margin,
            reduced_impeller_penalty_pp, low_speed_derate_pp_per_10pct,
            reference_rpm_60, max(top_n, 10),
        )
        if result.get("ok"):
            options.extend(_tag_vcmp(dict(op)) for op in result.get("options", []))
        else:
            reasons.append(result.get("reason", "VCMP unavailable"))

    if "hhecp" in techs:
        result = hhecp_pump.select(
            flow_m3h, required_dp_bar, density_kg_m3, motor_eff, vfd_eff,
            min_vfd_hz, max_vfd_hz, flow_margin, head_margin,
            max(top_n, 10), max_duty_units,
        )
        if result.get("ok"):
            options.extend(result.get("options", []))
        else:
            reasons.append(result.get("reason", "HHECP unavailable"))

    if "pd" in techs:
        result = pd_pump.select(
            flow_m3h, required_dp_bar, available_inlet_bar,
            motor_eff, vfd_eff, flow_margin, head_margin,
            max(top_n, 10), max_duty_units,
        )
        if result.get("ok"):
            options.extend(result.get("options", []))
        else:
            reasons.append(result.get("reason", "PD unavailable"))

    options.sort(key=lambda x: (
        float(x.get("wire_kw", 1e99)),
        int(x.get("duty_units", 1)),
        str(x.get("model", "")),
    ))
    for i, op in enumerate(options, 1):
        op["selection_rank"] = i
    keep = options[:max(1, int(top_n))]
    if not keep:
        return {
            "ok": False,
            "reason": "; ".join(reasons) or "No shared pump option covers the requested duty.",
            "options": [],
            "database_records": {
                "vcmp": len(vcmp_pump.PUMPS),
                "hhecp": len(hhecp_pump.MODELS),
                "pd": len(pd_pump.PUMPS),
            },
        }
    return {
        "ok": True,
        "selected": keep[0],
        "options": keep,
        "selection_basis": "Lowest actual wire power across feasible shared pump technologies",
        "database_records": {
            "vcmp": len(vcmp_pump.PUMPS),
            "hhecp": len(hhecp_pump.MODELS),
            "pd": len(pd_pump.PUMPS),
        },
    }


def curve_points(source_id, speed_ratio, density_kg_m3=998.0,
                 motor_eff=0.95, vfd_eff=0.98,
                 reduced_impeller_penalty_pp=2.0,
                 low_speed_derate_pp_per_10pct=0.0,
                 reference_rpm_60=None, samples=25):
    try:
        if isinstance(source_id, int) or str(source_id).isdigit():
            return vcmp_pump.curve_points(
                int(source_id), speed_ratio, density_kg_m3, motor_eff, vfd_eff,
                reduced_impeller_penalty_pp, low_speed_derate_pp_per_10pct,
                reference_rpm_60, samples,
            )
    except (KeyError, ValueError, TypeError):
        pass

    sid = str(source_id)
    if sid in hhecp_pump.BY_CODE:
        return hhecp_pump.curve_points(
            sid, speed_ratio, density_kg_m3, motor_eff, vfd_eff, samples,
        )
    if sid in pd_pump.BY_MODEL:
        row = pd_pump.BY_MODEL[sid]
        rpm = float(row["reference_rpm"]) * float(speed_ratio)
        q = float(row["kq_m3h_per_rpm"]) * rpm
        max_dp = float(row["max_outlet_barg"])
        head = max_dp * 100000.0 / max(float(density_kg_m3) * 9.80665, 1e-12)
        return [
            {
                "flow_m3h": q, "head_m": 0.0, "pump_dp_bar": 0.0,
                "efficiency": None, "shaft_kw": None, "wire_kw": None,
                "frequency_hz": None, "speed_ratio": float(speed_ratio),
                "speed_rpm": rpm,
            },
            {
                "flow_m3h": q, "head_m": head, "pump_dp_bar": max_dp,
                "efficiency": None, "shaft_kw": None, "wire_kw": None,
                "frequency_hz": None, "speed_ratio": float(speed_ratio),
                "speed_rpm": rpm,
            },
        ]
    raise KeyError(f"Unknown pump source_id/model: {source_id}")
