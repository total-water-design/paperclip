"""Final reconciliation hardening for Suite Core administrator metrics.

This module corrects three audit findings without changing the existing metrics
schema: time-of-day averages include zero-activity slots in the selected window,
capacity planning uses unique-user concurrency consistently, and production
registration can keep the legacy ResourceSample.active_sessions column while
normalizing its interpretation for planning.
"""
from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import suite_metrics as metrics


_ORIGINAL_HOURLY_PROFILE = metrics.build_hourly_profile
_ORIGINAL_CAPACITY_PLAN = metrics.capacity_plan


def build_hourly_profile_window_average(
    sessions,
    events,
    start,
    end,
    *,
    tz=metrics.EASTERN,
    slot_minutes: int = 15,
) -> list[dict]:
    """Average/peak connected users by local hour across the whole window.

    The original implementation only averaged days that had at least one
    session. This implementation pre-populates every analysis slot, so days and
    hours with zero activity remain part of the denominator.
    """
    step = timedelta(minutes=slot_minutes)
    slot_users: dict[object, set[int]] = {}

    cursor = metrics._floor_slot(start, slot_minutes)
    while cursor < end:
        slot_end = cursor + step
        if slot_end > start:
            slot_users[cursor] = set()
        cursor += step

    for row in sessions:
        bounds = metrics._session_bounds(row, end)
        if not bounds:
            continue
        s0, s1 = bounds
        s0, s1 = max(s0, start), min(s1, end)
        if s1 < s0:
            continue
        uid = int(getattr(row, "user_id", 0) or 0)
        if not uid:
            continue
        cursor = metrics._floor_slot(s0, slot_minutes)
        while cursor < s1:
            slot_end = cursor + step
            if cursor < s1 and slot_end > s0 and cursor in slot_users:
                slot_users[cursor].add(uid)
            cursor += step

    events_by_hour = [0] * 24
    calculations_by_hour = [0] * 24
    for event in events:
        created = metrics._aware(getattr(event, "created_at", None))
        if created is None or created < start or created > end:
            continue
        hour = created.astimezone(tz).hour
        events_by_hour[hour] += 1
        if str(getattr(event, "event_type", "") or "").startswith("calculation_"):
            calculations_by_hour[hour] += 1

    local_days = {stamp.astimezone(tz).date().isoformat() for stamp in slot_users}
    result = []
    for hour in range(24):
        values = [
            len(users)
            for stamp, users in slot_users.items()
            if stamp.astimezone(tz).hour == hour
        ]
        result.append(
            {
                "hour": hour,
                "label": metrics._hour_label(hour),
                "avg_users": round(sum(values) / len(values), 2) if values else 0.0,
                "peak_users": max(values, default=0),
                "events": events_by_hour[hour],
                "calculations": calculations_by_hour[hour],
                "active_days": len(local_days),
            }
        )
    return result


def capacity_plan_unique_users(
    samples,
    forecast: dict,
    *,
    current_vcpus: int,
    current_memory_gb: float | None,
    current_instance: str = "unknown",
) -> dict:
    """Run the existing transparent capacity model using unique-user units.

    ResourceSample.active_sessions is retained for backward schema compatibility,
    but it must not define the observed-user peak because older rows may contain
    browser-session counts. The unique-user peak already calculated from
    TelemetrySession history is the authoritative concurrency basis.
    """
    unique_peak = int(forecast.get("current_peak", 0) or 0)
    normalized = [
        SimpleNamespace(
            cpu_percent=getattr(row, "cpu_percent", None),
            memory_percent=getattr(row, "memory_percent", None),
            active_sessions=unique_peak,
        )
        for row in samples
    ]
    plan = _ORIGINAL_CAPACITY_PLAN(
        normalized,
        forecast,
        current_vcpus=current_vcpus,
        current_memory_gb=current_memory_gb,
        current_instance=current_instance or "unknown",
    )
    plan["concurrency_unit"] = "unique_authenticated_users"
    return plan


def apply_suite_metrics_hardening() -> None:
    """Install audit corrections before register_suite_metrics(app) is called."""
    if getattr(metrics, "_twds_metrics_hardened", False):
        return
    metrics.build_hourly_profile = build_hourly_profile_window_average
    metrics.capacity_plan = capacity_plan_unique_users
    metrics._twds_metrics_hardened = True
