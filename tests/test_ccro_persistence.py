from __future__ import annotations

from datetime import datetime, timezone

import pytest


@pytest.fixture
def authenticated_ccro_client(tmp_path, monkeypatch):
    db_path = tmp_path / "ccro-persistence.db"
    monkeypatch.setenv("TOTALRO_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("TOTALRO_AUTH_ENABLED", "1")
    monkeypatch.setenv("TOTALRO_CSRF_ENABLED", "0")
    monkeypatch.setenv("TOTALRO_SECRET_KEY", "ccro-persistence-test-" + "x" * 48)
    monkeypatch.setenv("TOTALRO_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("TOTALRO_AUTO_CREATE_DB", "1")
    monkeypatch.setenv("TOTALRO_COOKIE_SECURE", "0")
    monkeypatch.setenv("TOTALRO_TRUSTED_HOSTS", "localhost,127.0.0.1")

    import app as app_module
    from auth import User, db, ensure_default_entitlements

    app = app_module.app
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    accepted = datetime.now(timezone.utc)
    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(
            email="ccro-persistence@example.com",
            full_name="CCRO Persistence",
            organization="TWDS Test",
            role="user",
            licensed_tier="entry",
            status="active",
            terms_accepted_at=accepted,
            password_hash="",
        )
        user.set_password("CCRO-Persistence-Password")
        db.session.add(user)
        db.session.flush()
        entitlements = ensure_default_entitlements(user, flush=True)
        entitlements["ro"].enabled = True
        entitlements["ro"].tier = "entry"
        db.session.commit()

    client = app.test_client()
    login = client.post(
        "/login",
        data={"email": "ccro-persistence@example.com", "password": "CCRO-Persistence-Password"},
    )
    assert login.status_code == 302
    return client


def _ccro_payload(recovery=65):
    return {
        "flow_unit": "m3/h",
        "pressure_unit": "bar",
        "water_mode": "tds",
        "feed_tds": 2500,
        "analysis_tds": 2500,
        "temperature_c": 25,
        "feed_ph": 7.8,
        "membrane_1": "DuPont FilmTec|SW30HRLE-400|A / standard",
        "vessels_1": 4,
        "elements_per_vessel_1": 3,
        "permeate_pressure_1": 0,
        "ccro_target_average_recovery": recovery,
        "ccro_closed_circuit_permeate_flow": 8,
        "ccro_concentrate_recycle_per_vessel": 4.54,
        "ccro_pf_feed_ratio": 1.20,
        "ccro_pf_recovery": 20,
        "ccro_system_volume_m3": 1.0,
        "ccro_loop_extra_dp": 0.3,
        "suction_pressure": 2,
        "pump_eff": 0.85,
        "motor_eff": 0.97,
        "vfd_eff": 0.97,
        "ccro_circulation_pump_eff": 0.82,
        "ccro_circulation_motor_eff": 0.96,
        "ccro_circulation_vfd_eff": 0.97,
        "pretreatment_discharge_pressure": 6,
        "pretreatment_recovery": 0.85,
        "pretreatment_pump_eff": 0.82,
        "pretreatment_motor_eff": 0.95,
        "pretreatment_vfd_eff": 0.97,
        "fouling_factor": 0.90,
        "salt_passage_factor": 1.0,
    }


def test_ccro_save_reopen_recalculate_with_fresh_authenticated_project(authenticated_ccro_client):
    from addons.ccro.engine import ccro

    payload = _ccro_payload()
    result = ccro(payload)
    snapshot = {
        "format": "Total RO Design Project",
        "schema_version": 7,
        "app_version": "0.2",
        "project": {"project_name": "CCRO Persistence", "revision": "Rev 0"},
        "active_case": 1,
        "active_mode": "ccro",
        "units": {"flow": "m3/h", "pressure": "bar", "flux": "LMH"},
        "cases": {
            "1": {
                "waterProfile": dict(payload),
                "modeStates": {"ccro": dict(payload)},
                "caseResults": {"ccro": result},
            }
        },
    }

    created = authenticated_ccro_client.post("/api/projects", json={"snapshot": snapshot})
    assert created.status_code == 201, created.get_data(as_text=True)
    project = created.get_json()["project"]
    revision_id = project["id"]

    reopened = authenticated_ccro_client.get(f"/api/projects/{revision_id}")
    assert reopened.status_code == 200
    reopened_snapshot = reopened.get_json()["snapshot"]
    reopened_payload = reopened_snapshot["cases"]["1"]["modeStates"]["ccro"]
    reopened_result = ccro(reopened_payload)
    assert reopened_result["ccro"] is True
    assert reopened_result["ccro_cycle_profile"] == result["ccro_cycle_profile"]
    assert reopened_result["ccro_cycle_graph_profiles"] == result["ccro_cycle_graph_profiles"]
    assert reopened_result["recovery"] == pytest.approx(result["recovery"])

    changed = dict(reopened_snapshot)
    changed["cases"] = {"1": dict(reopened_snapshot["cases"]["1"])}
    changed["cases"]["1"]["modeStates"] = {"ccro": dict(reopened_payload, ccro_target_average_recovery=70)}
    updated = authenticated_ccro_client.put(f"/api/projects/{revision_id}", json={"snapshot": changed})
    assert updated.status_code == 200, updated.get_data(as_text=True)
    reread = authenticated_ccro_client.get(f"/api/projects/{revision_id}")
    assert reread.status_code == 200
    assert reread.get_json()["snapshot"]["cases"]["1"]["modeStates"]["ccro"]["ccro_target_average_recovery"] == 70
