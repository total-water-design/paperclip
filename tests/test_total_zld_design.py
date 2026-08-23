import pytest

from total_zld_design import calculate_fo_regression, calculate_thermal_legacy
from total_zld_design.snapshot import build_snapshot


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
    snapshot = build_snapshot(
        project={"project_name": "ZLD regression"},
        inputs=result.inputs,
        results=result.to_dict(),
        active_mode=result.mode,
    )
    assert snapshot["format"] == "Total ZLD Design Project"
    assert snapshot["schema_version"] == 1
    assert snapshot["app_version"] == "0.2.0"
    assert snapshot["active_mode"] == "fo_regression"
    assert snapshot["cases"]["1"]["results"]["mode"] == "fo_regression"


def test_zld_blueprint_serves_both_route_forms():
    flask = pytest.importorskip("flask")
    from total_zld_design.web import create_zld_blueprint

    app = flask.Flask(__name__)
    app.secret_key = "zld-route-test"
    app.register_blueprint(create_zld_blueprint())
    client = app.test_client()

    assert client.get("/zld").status_code == 200
    assert client.get("/zld/").status_code == 200
    assert client.get("/zld/api/health").get_json()["version"] == "0.2.0"
