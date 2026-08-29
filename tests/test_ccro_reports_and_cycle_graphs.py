import json
from pathlib import Path

from addons.ccro.engine import ccro
from ro_comparison import inspect_ccro_hydraulic_envelope
from report_snapshot import validate_report_snapshot
from tests.test_ccro_addon import ccro_case

ROOT = Path(__file__).resolve().parents[1]


def test_ccro_cycle_graph_profiles_are_compact_and_change_by_cycle():
    result = ccro(ccro_case(recovery=80, system_volume=5.0))
    profiles = result["ccro_cycle_graph_profiles"]
    assert len(profiles) == len(result["ccro_cycle_profile"])
    assert [p["cycle"] for p in profiles] == list(range(1, len(profiles) + 1))
    assert all(len(p["element_profile"]) == int(result["stage1_elements_per_vessel"]) for p in profiles)
    assert profiles[0]["feed_pressure_bar"] != profiles[-1]["feed_pressure_bar"]
    assert profiles[0]["element_profile"][0]["feed_tds_ppm"] != profiles[-1]["element_profile"][0]["feed_tds_ppm"]
    serialized = json.dumps(profiles)
    for forbidden in ("solver_history", "solver_diagnostics", "composition_mg_l", "carbonate"):
        assert forbidden not in serialized


def _snapshot(result, cycle=None):
    profile = result["ccro_cycle_graph_profiles"][-1 if cycle is None else cycle - 1]
    sig = "ccro-test-signature"
    return {
        "schema": "TotalRODesign.ReportSnapshot.v1",
        "state": "Ready",
        "stale": False,
        "active_mode": "ccro",
        "calculation_mode": "ccro",
        "case_id": 1,
        "stage_count": 1,
        "unit_system": {"flow": "m3/h", "pressure": "bar", "flux": "LMH"},
        "design_input": {"_last_calculated_signature": sig},
        "result": result,
        "options": {"report_type": "standard", "include_detailed_chemistry": False, "include_tail_chemistry": False, "include_hydraulic_envelope": False},
        "report_selection": {"ccro_cycle": profile["cycle"]},
        "selected_graph_profile": profile,
        "warning_messages": result.get("ccro_warnings", []),
        "report_integrity": {"last_calculated_signature": sig, "active_signature": sig},
    }


def test_ccro_report_snapshot_is_valid_without_multistage_result():
    result = ccro(ccro_case(recovery=75, system_volume=4.0))
    assert validate_report_snapshot(_snapshot(result)) == []


def test_ccro_snapshot_selected_cycle_is_explicit_and_immutable_surface():
    result = ccro(ccro_case(recovery=80, system_volume=5.0))
    early = _snapshot(result, 1)
    final = _snapshot(result)
    assert early["report_selection"]["ccro_cycle"] == 1
    assert early["selected_graph_profile"]["feed_pressure_bar"] != final["selected_graph_profile"]["feed_pressure_bar"]
    assert early["result"]["recovery"] == final["result"]["recovery"]
    assert validate_report_snapshot(early) == []


def test_ccro_report_snapshot_rejects_wrong_selected_profile():
    result = ccro(ccro_case(recovery=80, system_volume=5.0))
    snapshot = _snapshot(result, 1)
    snapshot["report_selection"]["ccro_cycle"] = 2
    errors = validate_report_snapshot(snapshot)
    assert any("does not match" in error for error in errors)


def test_ccro_report_ui_contract_is_mode_aware_all_tier_and_no_recalculation():
    addon = (ROOT / "static/addons/ccro/ccro_addon.js").read_text(encoding="utf-8")
    renderer = (ROOT / "static/addons/ccro/ccro_report.js").read_text(encoding="utf-8")
    assert "function activeReportContext()" in addon
    assert "function ccroCalculationSignature" in addon
    assert "caseResults?.[reportMode]" in addon
    assert "modeStates?.[reportMode]" in addon
    assert "ccroSelectedGraphCycle" in addon
    assert "Displayed CCRO cycle" in addon
    assert "ccro_cycle_graph_profiles" in addon
    assert "active_mode:'ccro'" in addon
    assert "calculation_mode:'ccro'" in addon
    assert "selected_graph_profile:selected" in addon
    assert "minimum_tier" not in renderer  # renderer is tier-neutral; entitlement happens before snapshot
    assert "/api/calculate/ccro" not in addon[addon.index("function bindCcroCycleSelector"):addon.index("function activeReportContext")]
    assert "CCRO Engineering Report" in renderer
    assert "Selected Graph Cycle" in renderer


def test_ccro_report_renderer_is_customer_surface_scrubbed():
    surface = (ROOT / "ro_customer_surface.py").read_text(encoding="utf-8")
    assert '"/static/addons/ccro/ccro_report.js"' in surface
    renderer = (ROOT / "static/addons/ccro/ccro_report.js").read_text(encoding="utf-8").lower()
    for forbidden in ("solver_history", "tolerance", "brent", "bisection", "iteration_history"):
        assert forbidden not in renderer


def test_conventional_report_renderer_remains_present_and_ccro_dispatch_is_explicit():
    report = (ROOT / "static/report.js").read_text(encoding="utf-8")
    assert "__TOTALRO_CCRO_REPORT_SNAPSHOT__" in report
    assert "function stageTable()" in report
    assert "function render()" in report


def test_ccro_hydraulic_envelope_rejects_interior_cycle_and_reports_first_governor():
    result = {
        "ccro_cycle_profile": [
            {"cycle": 1, "duration_min": 2, "feed_pressure_bar": 40, "minimum_element_ndp_bar": 8,
             "sequence_equivalent_recovery": .40},
            {"cycle": 2, "duration_min": 2, "feed_pressure_bar": 45, "minimum_element_ndp_bar": 3,
             "sequence_equivalent_recovery": .50},
            {"cycle": 3, "duration_min": 2, "feed_pressure_bar": 49, "minimum_element_ndp_bar": 8,
             "sequence_equivalent_recovery": .60},
        ]
    }
    envelope = inspect_ccro_hydraulic_envelope(result, {"pressure_bar": 50, "minimum_ndp_bar": 5})
    assert envelope["status"] == "infeasible"
    assert envelope["first_governing_constraint"] == {
        "constraint": "minimum_ndp", "critical_value": 3.0, "limit": 5.0,
        "cycle": 2, "time_min": 4.0, "recovery": .50,
    }
