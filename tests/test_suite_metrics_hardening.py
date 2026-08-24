from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import suite_metrics
from suite_metrics_hardening import (
    apply_suite_metrics_hardening,
    build_hourly_profile_window_average,
    capacity_plan_unique_users,
)


def session(user_id, start, end):
    return SimpleNamespace(
        user_id=user_id,
        started_at=start,
        last_seen_at=end,
        ended_at=end,
    )


def test_hourly_average_includes_zero_activity_slots_in_window():
    start = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=2)
    rows = [
        session(
            1,
            datetime(2026, 1, 15, 13, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc),
        )
    ]
    profile = build_hourly_profile_window_average(rows, [], start, end)
    # 8 AM Eastern appears on both days: four occupied quarter-hours and four
    # zero-user quarter-hours, so the full-window average is 0.5 user.
    assert profile[8]["peak_users"] == 1
    assert profile[8]["avg_users"] == 0.5


def test_capacity_plan_uses_unique_user_peak_not_session_count():
    samples = [
        SimpleNamespace(cpu_percent=30.0, memory_percent=40.0, active_sessions=20)
        for _ in range(60)
    ]
    forecast = {
        "current_peak": 2,
        "forecast_4w": 3,
        "forecast_8w": 4,
        "growth_per_week": 0.5,
    }
    plan = capacity_plan_unique_users(
        samples,
        forecast,
        current_vcpus=2,
        current_memory_gb=8.0,
        current_instance="t3.large",
    )
    assert plan["observed_peak"] == 2
    assert plan["concurrency_unit"] == "unique_authenticated_users"
    assert "t3.large" in plan["current"]


def test_hardening_install_is_idempotent():
    apply_suite_metrics_hardening()
    first_hourly = suite_metrics.build_hourly_profile
    first_capacity = suite_metrics.capacity_plan
    apply_suite_metrics_hardening()
    assert suite_metrics.build_hourly_profile is first_hourly
    assert suite_metrics.capacity_plan is first_capacity
