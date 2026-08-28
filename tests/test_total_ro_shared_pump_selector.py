from __future__ import annotations

import pytest

from app import app
from calculations import _pump_curve_screening
from tests.test_conventional_ro_regression import base_case


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TOTALRO_AUTH_ENABLED", "0")
    monkeypatch.setenv("TOTALRO_CSRF_ENABLED", "0")
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.mark.parametrize(
    ("mode", "expected_technology"),
    [("shared_auto", None), ("vcmp", "VCMP"), ("hhecp", "HHECP"), ("pd", "PD")],
)
def test_calculate_response_routes_explicit_pump_technology(client, mode, expected_technology):
    payload = base_case()
    payload["pump_curve_basis"] = mode
    response = client.post("/api/calculate/multistage", json=payload)
    body = response.get_json()

    assert response.status_code == 200, body
    assert body["pump_selection_mode"] == mode
    if expected_technology is None:
        assert body["pump_selected_technology"] in {"VCMP", "HHECP", "PD"}
    else:
        assert body["pump_selected_technology"] == expected_technology
    assert body["pump_curve_source"] == "shared_pump_database"
    assert body["pump_selected_model"]
    assert body["pump_duty_units"] >= 1
    assert body["pump_installed_units"] >= body["pump_duty_units"]


def test_no_feasible_catalog_response_is_explicit_and_uses_manual_efficiency(client):
    payload = base_case()
    payload.update(pump_curve_basis="pd", pump_max_duty_units=1)
    response = client.post("/api/calculate/multistage", json=payload)
    body = response.get_json()

    assert response.status_code == 200, body
    assert body["pump_selection_mode"] == "pd"
    assert body["pump_selection_status"] == "no_feasible_option"
    assert body["pump_database_fallback"] is True
    assert "No positive-displacement" in body["pump_database_fallback_reason"]
    assert body["pump_curve_source"] == "typical_screening"


def test_small_flow_catalog_selection_has_explicit_manual_fallback():
    result = _pump_curve_screening(
        {"pump_curve_basis": "shared_auto", "flow_unit": "m3/h", "pressure_unit": "bar"},
        1e-14, 1e-14, 0.0, 0.85, 0.97, 0.97,
    )

    assert result["pump_selection_mode"] == "shared_auto"
    assert result["pump_selection_status"] == "no_feasible_option"
    assert "too small" in result["pump_database_fallback_reason"]


def test_manual_mode_does_not_call_catalog_selector(client):
    payload = base_case()
    payload.update(pump_curve_basis="manual", pump_bep_flow=100, pump_bep_dp=18)
    response = client.post("/api/calculate/multistage", json=payload)
    body = response.get_json()

    assert response.status_code == 200, body
    assert body["pump_curve_basis"] == "manual"
    assert body["pump_curve_source"] == "typical_screening"
    assert "pump_selected_technology" not in body
