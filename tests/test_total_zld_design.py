from pathlib import Path

import pytest

from total_zld_design import (
    calculate_fo_regression,
    calculate_thermal_legacy,
    crystal_kinetics_capabilities,
    crystallizer_design_capabilities,
    crystallizer_inhibitor_capabilities,
    falling_film_capabilities,
    population_balance_capabilities,
    process_train_capabilities,
    solution_property_capabilities,
)
from total_zld_design.service import defaults_payload
from total_zld_design.snapshot import build_snapshot

ROOT = Path(__file__).resolve().parents[1]


def test_total_zld_design_workbook_regression_fingerprints():
    thermal = calculate_thermal_legacy()
    fo = calculate_fo_regression()
    assert thermal.summary["overall_recovery"] == pytest.approx(0.7214285714, abs=1e-9)
    assert thermal.summary["total_recovered_water_m3_h"] == pytest.approx(180.35714286, abs=1e-6)
    assert fo.summary["total_water_recovered_m3_h"] == pytest.approx(42.391488, abs=1e-5)
    assert fo.summary["feed_water_recovery"] == pytest.approx(0.42391488, abs=1e-7)
    assert fo.summary["final_bulk_concentration_factor"] == pytest.approx(1.735855, abs=1e-5)


def test_total_zld_snapshot_is_suite_compatible():
    result = calculate_fo_regression()
    train = [{"instance_id": "falling_film_evaporator-1", "unit_type": "falling_film_evaporator", "enabled": True}]
    snapshot = build_snapshot(
        project={"project_name": "ZLD regression", "process_train": train},
        inputs=result.inputs,
        results=result.to_dict(),
        active_mode=result.mode,
    )
    assert snapshot["format"] == "Total ZLD Design Project"
    assert snapshot["schema_version"] == 1
    assert snapshot["app_version"] == "0.2.0"
    assert snapshot["active_mode"] == "fo_regression"
    assert snapshot["cases"]["1"]["results"]["mode"] == "fo_regression"
    assert snapshot["project"]["process_train"] == train


def test_zld_foundation_capabilities_are_exposed_consistently():
    public = {
        "solution_properties": solution_property_capabilities(),
        "crystal_kinetics": crystal_kinetics_capabilities(),
        "crystallization_inhibitors": crystallizer_inhibitor_capabilities(),
        "population_balance": population_balance_capabilities(),
        "crystallizer_design": crystallizer_design_capabilities(),
        "falling_film_capabilities": falling_film_capabilities(),
        "process_train_capabilities": process_train_capabilities(),
    }
    payload = defaults_payload()
    assert set(public).issubset(payload)
    for key, value in public.items():
        assert payload[key] == value
    assert "falling_film" in payload
    assert "process_train" in payload
    assert "calibration" in public["crystallization_inhibitors"]["status"]
    assert public["crystallizer_design"]["selection_warning"] == "Ranking is engineering screening, not final vendor selection."


def test_zld_blueprint_serves_both_route_forms():
    flask = pytest.importorskip("flask")
    from total_zld_design.web import create_zld_blueprint

    app = flask.Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.secret_key = "zld-route-test"
    app.config["AUTH_ENABLED"] = False
    app.register_blueprint(create_zld_blueprint())
    client = app.test_client()

    assert client.get("/zld").status_code == 200
    assert client.get("/zld/").status_code == 200
    assert client.get("/zld/api/health").get_json()["version"] == "0.2.0"


def test_zld_template_uses_suite_ui_contract_v1_shell_and_results_hierarchy():
    text = (ROOT / "total_zld_design/web/templates/zld_contract.html").read_text()
    assert '{% extends "shared/application_shell.html" %}' in text
    assert "Total ZLD Design" in text
    assert "SYSTEM SUMMARY" in text
    assert "PROCESS / UNIT SUMMARY" in text
    assert "DETAILED RESULTS" in text
    assert "WARNINGS & CONSTRAINTS" in text
    assert "ENERGY / ECONOMICS" in text
    assert "WATER CHEMISTRY" in text
    assert "Calculate Thermal Train" not in text
    assert "Calculate FO Transport" not in text


def test_zld_client_uses_shared_project_calculation_and_configurable_train_contract():
    text = (ROOT / "total_zld_design/web/static/zld_contract.js").read_text()
    assert "twds:project-action" in text
    assert "TWDSAppUI" in text
    assert "validating" in text
    assert "calculating" in text
    assert "converging" in text
    assert "converged" in text
    assert "attention" in text
    assert "stale" in text
    assert "window.ZLDTrain" in text
    assert "process_train" in text
    assert "train-remove" in text
    assert "train-up" in text
    assert "train-down" in text
    assert "falling_film_evaporator" in text
    assert "runFFE" in text


def test_zld_branch_carries_pinned_shared_shell_dependencies():
    required = [
        ROOT / "templates/shared/application_shell.html",
        ROOT / "templates/shared/suite_components.html",
        ROOT / "static/suite_ui_tokens.css",
        ROOT / "static/suite_application_shell.css",
        ROOT / "static/suite_application_shell.js",
    ]
    assert all(path.is_file() for path in required)
