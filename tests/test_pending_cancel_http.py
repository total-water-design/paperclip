import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as ro_app
import compute_engine


@pytest.fixture(autouse=True)
def reset_lifecycle_state():
    with ro_app._calculation_owner_lock:
        ro_app._active_calculation_owner = None
    with compute_engine._monitor_lock:
        compute_engine._pending_cancel = None
        compute_engine._cancel_event.clear()
        compute_engine._compute_state.update({
            "active": False,
            "run_id": None,
            "cancel_requested": False,
            "cancelled": False,
        })
    yield
    with compute_engine._monitor_lock:
        compute_engine._pending_cancel = None
        compute_engine._cancel_event.clear()
        compute_engine._compute_state["active"] = False


def test_client_side_pending_stop_does_not_poison_immediate_real_calculate(monkeypatch):
    monkeypatch.setitem(ro_app.CALCS, "multistage", lambda payload: {"ok": True})
    monkeypatch.setattr(ro_app, "record_telemetry", lambda *args, **kwargs: None)
    monkeypatch.setattr(ro_app.db.session, "commit", lambda: None)
    ro_app.app.config.update(TESTING=True, AUTH_ENABLED=False)

    with ro_app.app.test_client() as client:
        stopped = client.post("/api/compute/cancel", json={})
        calculated = client.post(
            "/api/calculate/multistage",
            json={"solve_basis": "pressure", "design_mode": "manual", "stage_count": 1},
        )

    assert stopped.status_code == 200
    assert stopped.get_json()["already_finished"] is True
    assert stopped.get_json().get("pending_cancel") is None
    assert calculated.status_code == 200
    assert calculated.get_json()["ok"] is True
    assert calculated.get_json().get("cancelled") is None
    assert compute_engine._pending_cancel is None
    assert compute_engine.compute_status()["cancelled"] is False
