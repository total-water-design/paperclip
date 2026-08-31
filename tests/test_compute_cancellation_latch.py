import sys
from pathlib import Path

import pytest


# Keep the required console entry point (``pytest ...``) equivalent to
# ``python -m pytest ...`` by making the repository root importable explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import compute_engine


@pytest.fixture(autouse=True)
def reset_compute_cancellation_state():
    compute_engine.shutdown_pool()
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
    compute_engine.shutdown_pool()
    with compute_engine._monitor_lock:
        compute_engine._pending_cancel = None
        compute_engine._cancel_event.clear()
        compute_engine._compute_state["active"] = False


def test_pre_start_cancel_is_consumed_by_matching_owner_before_result_commit():
    response = compute_engine.request_compute_cancel(owner="owner-a", hard=False)

    assert response == {
        "ok": True,
        "active": False,
        "run_id": None,
        "pending_cancel": True,
    }
    run_id = compute_engine.begin_compute_run("calculate", owner="owner-a")
    result_committed = False
    with pytest.raises(compute_engine.CalculationCancelled):
        compute_engine.raise_if_cancelled()
        result_committed = True

    assert isinstance(run_id, int)
    assert compute_engine.compute_status()["cancel_requested"] is True
    assert result_committed is False


def test_active_cancel_still_succeeds_and_stale_run_id_is_rejected_first():
    run_id = compute_engine.begin_compute_run("calculate", owner="owner-a")

    stale = compute_engine.request_compute_cancel(run_id + 1, owner="owner-a", hard=False)
    assert stale == {
        "ok": False,
        "active": True,
        "run_id": run_id,
        "reason": "run_id_mismatch",
    }
    assert compute_engine.cancellation_requested() is False

    active = compute_engine.request_compute_cancel(run_id, owner="owner-a", hard=False)
    assert active == {
        "ok": True,
        "active": True,
        "run_id": run_id,
        "cancel_requested": True,
    }
    with pytest.raises(compute_engine.CalculationCancelled):
        compute_engine.raise_if_cancelled()


def test_pending_cancel_does_not_cross_owner_boundary():
    compute_engine.request_compute_cancel(owner="owner-a", hard=False)

    compute_engine.begin_compute_run("calculate", owner="owner-b")

    compute_engine.raise_if_cancelled()
    assert compute_engine.compute_status()["cancel_requested"] is False


def test_expired_pending_cancel_does_not_cancel_later_run(monkeypatch):
    times = [100.0, 100.0 + compute_engine._PENDING_CANCEL_TTL_SECONDS + 0.001]
    monkeypatch.setattr(compute_engine.time, "time", lambda: times.pop(0) if times else 106.0)
    compute_engine.request_compute_cancel(owner="owner-a", hard=False)

    compute_engine.begin_compute_run("calculate", owner="owner-a")

    compute_engine.raise_if_cancelled()
    assert compute_engine.compute_status()["cancel_requested"] is False


def test_consumed_cancel_allows_immediately_following_calculation_to_complete():
    compute_engine.request_compute_cancel(owner="owner-a", hard=False)
    compute_engine.begin_compute_run("calculate", owner="owner-a")
    with pytest.raises(compute_engine.CalculationCancelled):
        compute_engine.raise_if_cancelled()
    compute_engine.finish_compute_run(cancelled=True)

    compute_engine.begin_compute_run("calculate", owner="owner-a")
    compute_engine.raise_if_cancelled()
    completed = compute_engine.finish_compute_run()

    assert completed["active"] is False
    assert completed["cancelled"] is False
    assert completed["phase"] == "complete"


def test_hard_cancel_terminates_and_releases_backend_pool(monkeypatch):
    class Worker:
        def __init__(self):
            self.terminated = False
            self.join_timeout = None

        def is_alive(self):
            return True

        def terminate(self):
            self.terminated = True

        def join(self, timeout):
            self.join_timeout = timeout

    class Pool:
        def __init__(self, worker):
            self._processes = {123: worker}
            self.shutdown_args = None

        def shutdown(self, *, wait, cancel_futures):
            self.shutdown_args = (wait, cancel_futures)

    worker = Worker()
    pool = Pool(worker)
    monkeypatch.setattr(compute_engine, "_pool", pool)
    monkeypatch.setattr(compute_engine, "_pool_workers", 1)
    run_id = compute_engine.begin_compute_run("calculate", owner="owner-a")

    response = compute_engine.request_compute_cancel(run_id, owner="owner-a", hard=True)

    assert response["cancel_requested"] is True
    assert worker.terminated is True
    assert worker.join_timeout == 0.25
    assert pool.shutdown_args == (False, True)
    assert compute_engine._pool is None
    assert compute_engine._pool_workers is None
