"""Suite-wide administrator analytics and capacity planning.

This module is registered by the production WSGI entry point after the main
Flask application is constructed. It intentionally keeps engineering payloads
out of telemetry: only account/session identifiers, event metadata, aggregate
resource pressure, and project-storage totals are used.

All dashboard time-of-day analysis is normalized to America/New_York so the
administrator sees one consistent US Eastern clock with EST/EDT handled by the
IANA time-zone database.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import ceil, floor
from pathlib import Path
from statistics import median
from threading import RLock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json
import os
import time

try:
    EASTERN = ZoneInfo("America/New_York")
    EASTERN_LABEL = "US Eastern (ET — EST/EDT)"
except ZoneInfoNotFoundError:  # pragma: no cover - Linux servers provide tzdata
    EASTERN = timezone(timedelta(hours=-5))
    EASTERN_LABEL = "US Eastern (EST fallback)"

ACTIVE_GRACE_SECONDS = 5 * 60
HEARTBEAT_SECONDS = 30
RESOURCE_SAMPLE_SECONDS = 60
FORECAST_DAYS = 90

_sample_lock = RLock()
_last_sample_monotonic = 0.0


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _percentile(values: list[float], p: float) -> float:
    vals = sorted(float(v) for v in values if v is not None)
    if not vals:
        return 0.0
    idx = min(len(vals) - 1, max(0, int(round((len(vals) - 1) * p))))
    return vals[idx]


def _session_bounds(row, now: datetime, grace_seconds: int = ACTIVE_GRACE_SECONDS) -> tuple[datetime, datetime] | None:
    start = _aware(getattr(row, "started_at", None))
    if start is None:
        return None
    ended = _aware(getattr(row, "ended_at", None))
    last_seen = _aware(getattr(row, "last_seen_at", None)) or start
    if ended is not None:
        end = ended
    else:
        end = min(now, last_seen + timedelta(seconds=grace_seconds))
    if end < start:
        end = start
    return start, end


def _floor_slot(value: datetime, minutes: int) -> datetime:
    minute = (value.minute // minutes) * minutes
    return value.replace(minute=minute, second=0, microsecond=0)


def _hour_label(hour: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    display = hour % 12 or 12
    return f"{display} {suffix}"


def build_hourly_profile(
    sessions,
    events,
    start: datetime,
    end: datetime,
    *,
    tz=EASTERN,
    slot_minutes: int = 15,
) -> list[dict]:
    """Average and peak unique connected users by Eastern hour of day."""
    now = end
    slot_users: dict[tuple[str, int, int], set[int]] = defaultdict(set)
    active_days: set[str] = set()
    events_by_hour = [0] * 24
    calculations_by_hour = [0] * 24

    for row in sessions:
        bounds = _session_bounds(row, now)
        if not bounds:
            continue
        s0, s1 = bounds
        s0, s1 = max(s0, start), min(s1, end)
        if s1 < s0:
            continue
        cursor = _floor_slot(s0, slot_minutes)
        while cursor < s1:
            slot_end = cursor + timedelta(minutes=slot_minutes)
            if cursor < s1 and slot_end > s0:
                local = cursor.astimezone(tz)
                day = local.date().isoformat()
                active_days.add(day)
                uid = int(getattr(row, "user_id", 0) or 0)
                if uid:
                    slot_users[(day, local.hour, local.minute // slot_minutes)].add(uid)
            cursor += timedelta(minutes=slot_minutes)

    for event in events:
        created = _aware(getattr(event, "created_at", None))
        if created is None or created < start or created > end:
            continue
        hour = created.astimezone(tz).hour
        events_by_hour[hour] += 1
        if str(getattr(event, "event_type", "") or "").startswith("calculation_"):
            calculations_by_hour[hour] += 1

    day_count = len(active_days)
    slots_per_hour = max(1, 60 // slot_minutes)
    result = []
    for hour in range(24):
        values = [
            len(slot_users.get((day, hour, quarter), set()))
            for day in active_days
            for quarter in range(slots_per_hour)
        ]
        avg_users = (sum(values) / len(values)) if values else 0.0
        result.append(
            {
                "hour": hour,
                "label": _hour_label(hour),
                "avg_users": round(avg_users, 2),
                "peak_users": max(values, default=0),
                "events": events_by_hour[hour],
                "calculations": calculations_by_hour[hour],
                "active_days": day_count,
            }
        )
    return result


def build_concurrency_series(
    sessions,
    start: datetime,
    end: datetime,
    *,
    tz=EASTERN,
    step_minutes: int = 30,
) -> list[dict]:
    """Point-in-time unique connected-user counts for a bounded interval."""
    intervals: list[tuple[datetime, datetime, int]] = []
    for row in sessions:
        bounds = _session_bounds(row, end)
        if not bounds:
            continue
        s0, s1 = bounds
        if s1 < start or s0 > end:
            continue
        uid = int(getattr(row, "user_id", 0) or 0)
        if uid:
            intervals.append((max(s0, start), min(s1, end), uid))

    cursor = _floor_slot(start, step_minutes)
    if cursor < start:
        cursor += timedelta(minutes=step_minutes)
    points = []
    while cursor <= end:
        users = {uid for s0, s1, uid in intervals if s0 <= cursor <= s1}
        local = cursor.astimezone(tz)
        points.append(
            {
                "timestamp": cursor.isoformat(),
                "label": local.strftime("%-I:%M %p") if os.name != "nt" else local.strftime("%I:%M %p").lstrip("0"),
                "users": len(users),
            }
        )
        cursor += timedelta(minutes=step_minutes)
    if not points or points[-1]["timestamp"] != end.isoformat():
        users = {uid for s0, s1, uid in intervals if s0 <= end <= s1}
        local = end.astimezone(tz)
        points.append(
            {
                "timestamp": end.isoformat(),
                "label": local.strftime("%-I:%M %p") if os.name != "nt" else local.strftime("%I:%M %p").lstrip("0"),
                "users": len(users),
            }
        )
    return points


def build_daily_series(sessions, events, start: datetime, end: datetime, *, tz=EASTERN) -> list[dict]:
    """Daily active users and event/calculation totals in US Eastern time."""
    daily_users: dict[str, set[int]] = defaultdict(set)
    daily: dict[str, dict] = defaultdict(
        lambda: {"events": 0, "calculations": 0, "failures": 0, "cpu_seconds": 0.0}
    )

    for row in sessions:
        bounds = _session_bounds(row, end)
        if not bounds:
            continue
        s0, s1 = bounds
        s0, s1 = max(s0, start), min(s1, end)
        if s1 < s0:
            continue
        uid = int(getattr(row, "user_id", 0) or 0)
        local_start = s0.astimezone(tz).date()
        local_end = s1.astimezone(tz).date()
        day = local_start
        while day <= local_end:
            if uid:
                daily_users[day.isoformat()].add(uid)
            day += timedelta(days=1)

    for event in events:
        created = _aware(getattr(event, "created_at", None))
        if created is None or created < start or created > end:
            continue
        key = created.astimezone(tz).date().isoformat()
        row = daily[key]
        row["events"] += 1
        event_type = str(getattr(event, "event_type", "") or "")
        if event_type in {"calculation_completed", "calculation_failed"}:
            row["calculations"] += 1
            if not bool(getattr(event, "success", True)) or event_type == "calculation_failed":
                row["failures"] += 1
            row["cpu_seconds"] += float(getattr(event, "cpu_seconds", 0.0) or 0.0)

    keys = sorted(set(daily) | set(daily_users))
    return [
        {
            "date": key,
            "label": datetime.fromisoformat(key).strftime("%b %d"),
            "active_users": len(daily_users.get(key, set())),
            **daily.get(key, {"events": 0, "calculations": 0, "failures": 0, "cpu_seconds": 0.0}),
        }
        for key in keys
    ]


def build_weekly_peak_concurrency(
    sessions,
    start: datetime,
    end: datetime,
    *,
    tz=EASTERN,
    step_minutes: int = 30,
) -> list[dict]:
    """Peak concurrent users per ISO week for forecast input."""
    series = build_concurrency_series(sessions, start, end, tz=tz, step_minutes=step_minutes)
    peaks: dict[tuple[int, int], dict] = {}
    for point in series:
        stamp = datetime.fromisoformat(point["timestamp"])
        local = stamp.astimezone(tz)
        year, week, _ = local.isocalendar()
        key = (year, week)
        row = peaks.setdefault(
            key,
            {
                "label": f"{year}-W{week:02d}",
                "week_start": (local.date() - timedelta(days=local.weekday())).isoformat(),
                "peak_users": 0,
            },
        )
        row["peak_users"] = max(int(row["peak_users"]), int(point["users"]))
    return [peaks[key] for key in sorted(peaks)]


def linear_peak_forecast(weekly_peaks: list[dict], weeks_forward: int = 8) -> dict:
    """Simple transparent least-squares forecast; no opaque ML model is used."""
    observed = [float(row.get("peak_users", 0) or 0) for row in weekly_peaks]
    n = len(observed)
    if n < 4 or max(observed, default=0) <= 0:
        current = max(observed, default=0.0)
        return {
            "confidence": "collecting_baseline",
            "growth_per_week": 0.0,
            "current_peak": int(round(current)),
            "forecast_4w": int(round(current)),
            "forecast_8w": int(round(current)),
            "points": [
                {
                    "label": row["label"],
                    "observed": int(row["peak_users"]),
                    "forecast": None,
                }
                for row in weekly_peaks
            ],
        }

    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(observed) / n
    denom = sum((x - x_mean) ** 2 for x in xs)
    slope = (sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, observed)) / denom) if denom else 0.0
    intercept = y_mean - slope * x_mean
    slope = max(-max(observed), slope)

    points = [
        {"label": row["label"], "observed": int(row["peak_users"]), "forecast": None}
        for row in weekly_peaks
    ]
    if points:
        points[-1]["forecast"] = points[-1]["observed"]
    last_week_start = datetime.fromisoformat(weekly_peaks[-1]["week_start"]).date()
    for i in range(1, weeks_forward + 1):
        x = n - 1 + i
        predicted = max(0.0, intercept + slope * x)
        week_start = last_week_start + timedelta(days=7 * i)
        points.append(
            {
                "label": week_start.strftime("%b %d"),
                "observed": None,
                "forecast": round(predicted, 2),
            }
        )

    def predicted_at(extra_weeks: int) -> int:
        return int(round(max(0.0, intercept + slope * (n - 1 + extra_weeks))))

    return {
        "confidence": "directional",
        "growth_per_week": round(slope, 2),
        "current_peak": int(round(observed[-1])),
        "forecast_4w": predicted_at(4),
        "forecast_8w": predicted_at(8),
        "points": points,
    }


def _memory_snapshot() -> tuple[float | None, float | None]:
    """Return system memory percent and total GiB using Linux /proc when available."""
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = float(raw.strip().split()[0])
        total = values.get("MemTotal", 0.0)
        available = values.get("MemAvailable", values.get("MemFree", 0.0))
        if total > 0:
            return max(0.0, min(100.0, (1.0 - available / total) * 100.0)), total / 1048576.0
    except Exception:
        pass
    return None, None


def _process_rss_mb() -> float | None:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
    except Exception:
        pass
    return None


def current_resource_snapshot(*, active_sessions: int = 0, project_bytes: int = 0, database_bytes: int | None = None) -> dict:
    """No-dependency resource pressure snapshot suitable for the current Linux EC2 host."""
    vcpus = max(1, int(os.cpu_count() or 1))
    cpu_percent = None
    try:
        load1 = float(os.getloadavg()[0])
        cpu_percent = max(0.0, min(100.0, (load1 / vcpus) * 100.0))
    except Exception:
        pass
    memory_percent, memory_gb = _memory_snapshot()
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "process_memory_mb": _process_rss_mb(),
        "database_bytes": database_bytes,
        "project_bytes": int(project_bytes or 0),
        "active_sessions": int(active_sessions or 0),
        "vcpus": vcpus,
        "memory_gb": memory_gb,
        "sampled_at": datetime.now(timezone.utc),
    }


AWS_COMPUTE_SHAPES = (
    {"instance": "c7i.large", "vcpus": 2, "memory_gb": 4, "servers": 1},
    {"instance": "c7i.xlarge", "vcpus": 4, "memory_gb": 8, "servers": 1},
    {"instance": "c7i.2xlarge", "vcpus": 8, "memory_gb": 16, "servers": 1},
    {"instance": "c7i.4xlarge", "vcpus": 16, "memory_gb": 32, "servers": 1},
    {"instance": "c7i.8xlarge", "vcpus": 32, "memory_gb": 64, "servers": 1},
)


def capacity_plan(
    samples,
    forecast: dict,
    *,
    current_vcpus: int,
    current_memory_gb: float | None,
    current_instance: str = "t3.micro",
) -> dict:
    """Translate measured load plus concurrency forecast into a transparent EC2 plan."""
    samples = list(samples)
    cpu_values = [float(getattr(s, "cpu_percent", 0) or 0) for s in samples if getattr(s, "cpu_percent", None) is not None]
    mem_values = [float(getattr(s, "memory_percent", 0) or 0) for s in samples if getattr(s, "memory_percent", None) is not None]
    active_values = [int(getattr(s, "active_sessions", 0) or 0) for s in samples]
    p95_cpu = _percentile(cpu_values, 0.95)
    p95_memory = _percentile(mem_values, 0.95)
    observed_peak = max(active_values, default=int(forecast.get("current_peak", 0) or 0))
    forecast_peak = max(
        observed_peak,
        int(forecast.get("forecast_8w", 0) or 0),
        int(forecast.get("forecast_4w", 0) or 0),
    )

    pressure_factor = max(
        1.0,
        p95_cpu / 60.0 if p95_cpu else 1.0,
        p95_memory / 70.0 if p95_memory else 1.0,
    )
    demand_factor = max(1.0, forecast_peak / max(1, observed_peak)) if observed_peak else 1.0
    scale_factor = max(pressure_factor, demand_factor)

    current_vcpus = max(1, int(current_vcpus or 1))
    current_memory_gb = float(current_memory_gb or 0.0)
    target_vcpus = max(2, int(ceil(current_vcpus * scale_factor)))
    target_memory = max(4.0, current_memory_gb * max(1.0, p95_memory / 65.0 if p95_memory else 1.0))

    chosen = AWS_COMPUTE_SHAPES[-1]
    for shape in AWS_COMPUTE_SHAPES:
        if shape["vcpus"] >= target_vcpus and shape["memory_gb"] >= target_memory:
            chosen = shape
            break

    safe_by_cpu = None
    safe_by_mem = None
    if observed_peak > 0 and p95_cpu > 0:
        safe_by_cpu = max(1, int(floor(observed_peak * 70.0 / p95_cpu)))
    if observed_peak > 0 and p95_memory > 0:
        safe_by_mem = max(1, int(floor(observed_peak * 80.0 / p95_memory)))
    finite_caps = [x for x in (safe_by_cpu, safe_by_mem) if x]
    safe_concurrency = min(finite_caps) if finite_caps else None

    server_count = 1
    if safe_concurrency and forecast_peak > safe_concurrency:
        server_count = max(2, int(ceil(forecast_peak / max(1, safe_concurrency))))

    sample_count = len(samples)
    insufficient = sample_count < 60 or not cpu_values or not mem_values
    if insufficient:
        status = "collecting_baseline"
        chosen = AWS_COMPUTE_SHAPES[0] if current_memory_gb < 4.0 else chosen
        server_count = 1
    elif p95_cpu >= 75 or p95_memory >= 82:
        status = "scale_now"
    elif p95_cpu >= 60 or p95_memory >= 70 or (
        safe_concurrency and forecast_peak >= max(1, int(0.8 * safe_concurrency))
    ):
        status = "plan_upgrade"
    else:
        status = "healthy"

    trigger_weeks = None
    growth = float(forecast.get("growth_per_week", 0.0) or 0.0)
    current_peak = int(forecast.get("current_peak", observed_peak) or observed_peak)
    if safe_concurrency and growth > 0:
        trigger = 0.8 * safe_concurrency
        if current_peak < trigger:
            trigger_weeks = max(0, int(ceil((trigger - current_peak) / growth)))
        else:
            trigger_weeks = 0

    current_description = f"{current_instance} / {current_vcpus} vCPU"
    if current_memory_gb:
        current_description += f" / {current_memory_gb:.1f} GiB"

    if status == "scale_now":
        action = "Scale compute capacity now; resource pressure is above the planning threshold."
    elif status == "plan_upgrade":
        action = "Plan the next EC2 upgrade before forecast demand reaches the current headroom."
    elif status == "healthy":
        action = "Current capacity has measured headroom; continue collecting telemetry."
    else:
        action = "Collect at least one hour of resource samples and multiple active-user periods before treating the capacity estimate as reliable."

    return {
        "status": status,
        "sample_count": sample_count,
        "p95_cpu": round(p95_cpu, 1),
        "p95_memory": round(p95_memory, 1),
        "observed_peak": observed_peak,
        "forecast_peak_8w": forecast_peak,
        "safe_concurrency": safe_concurrency,
        "current": current_description,
        "recommended_instance": chosen["instance"],
        "recommended_vcpus": chosen["vcpus"],
        "recommended_memory_gb": chosen["memory_gb"],
        "recommended_servers": server_count,
        "trigger_weeks": trigger_weeks,
        "action": action,
        "architecture_note": (
            "Before running more than one web/compute server, move heavy-calculation coordination "
            "to a shared queue/lock and use shared PostgreSQL/session infrastructure; the current "
            "process-wide calculation gate is intentionally single-host."
        ),
        "method_note": (
            "Directional model using p95 server pressure, observed concurrent sessions and an "
            "8-week least-squares concurrency trend. It is a planning aid, not an AWS guarantee."
        ),
    }


def _database_size_bytes(db_url: str) -> int | None:
    try:
        if not str(db_url).startswith("sqlite:///"):
            return None
        raw = str(db_url)[len("sqlite:///") :]
        path = Path("/" + raw.lstrip("/")) if raw.startswith("/") else Path(raw)
        return path.stat().st_size if path.exists() else None
    except Exception:
        return None


def register_suite_metrics(app) -> None:
    """Install enhanced Suite Core analytics into an already-created Flask app."""
    if app.extensions.get("twds_suite_metrics"):
        return
    app.extensions["twds_suite_metrics"] = True

    from flask import jsonify, render_template, request, session
    from flask_login import current_user
    from sqlalchemy import func, select
    from auth import (
        ResourceSample,
        ProjectRevision,
        TelemetryEvent,
        TelemetrySession,
        User,
        _current_telemetry_session,
        admin_required,
        db,
    )

    def _utcnow_local() -> datetime:
        return datetime.now(timezone.utc)

    def _connected(now: datetime) -> tuple[int, int]:
        cutoff = now - timedelta(seconds=ACTIVE_GRACE_SECONDS)
        rows = db.session.scalars(
            select(TelemetrySession).where(TelemetrySession.last_seen_at >= cutoff)
        ).all()
        live = []
        for row in rows:
            ended = _aware(row.ended_at)
            if ended is None or ended >= cutoff:
                live.append(row)
        return len({int(row.user_id) for row in live}), len(live)

    def _maybe_sample(now: datetime, active_sessions: int) -> None:
        global _last_sample_monotonic
        monotonic_now = time.monotonic()
        with _sample_lock:
            if monotonic_now - _last_sample_monotonic < RESOURCE_SAMPLE_SECONDS:
                return
            _last_sample_monotonic = monotonic_now
        project_bytes = int(
            db.session.scalar(select(func.coalesce(func.sum(ProjectRevision.snapshot_bytes), 0))) or 0
        )
        snap = current_resource_snapshot(
            active_sessions=active_sessions,
            project_bytes=project_bytes,
            database_bytes=_database_size_bytes(app.config.get("SQLALCHEMY_DATABASE_URI", "")),
        )
        db.session.add(
            ResourceSample(
                cpu_percent=snap["cpu_percent"],
                memory_percent=snap["memory_percent"],
                process_memory_mb=snap["process_memory_mb"],
                database_bytes=snap["database_bytes"],
                project_bytes=snap["project_bytes"],
                active_sessions=snap["active_sessions"],
                sampled_at=now,
            )
        )

    @app.before_request
    def _suite_metrics_heartbeat():
        if not app.config.get("AUTH_ENABLED", False):
            return None
        if request.endpoint == "static":
            return None
        if not current_user.is_authenticated or getattr(current_user, "status", None) != "active":
            return None
        epoch = time.time()
        last = float(session.get("_twds_metrics_heartbeat", 0.0) or 0.0)
        if epoch - last < HEARTBEAT_SECONDS:
            return None
        try:
            _current_telemetry_session(current_user)
            session["_twds_metrics_heartbeat"] = epoch
            _users, live_sessions = _connected(_utcnow_local())
            _maybe_sample(_utcnow_local(), live_sessions)
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Suite metrics heartbeat failed")
        return None

    def _enhanced_admin_metrics():
        now = _utcnow_local()
        window = str(request.args.get("window") or "30d").lower()
        days = {"24h": 1, "7d": 7, "30d": 30, "90d": 90, "1y": 365, "all": 36500}.get(window, 30)
        start = now - timedelta(days=days)

        users = db.session.scalars(select(User)).all()
        sessions = db.session.scalars(
            select(TelemetrySession).where(TelemetrySession.last_seen_at >= start)
        ).all()
        events = db.session.scalars(
            select(TelemetryEvent).where(TelemetryEvent.created_at >= start)
        ).all()
        projects = db.session.scalars(select(ProjectRevision)).all()
        resources = db.session.scalars(
            select(ResourceSample).where(ResourceSample.sampled_at >= start).order_by(ResourceSample.sampled_at)
        ).all()

        active_ids = {int(s.user_id) for s in sessions}
        durations = []
        for row in sessions:
            bounds = _session_bounds(row, now)
            if bounds:
                s0, s1 = bounds
                durations.append(max(0.0, (s1 - s0).total_seconds()))

        calculations = [
            event for event in events
            if str(event.event_type) in {"calculation_completed", "calculation_failed"}
        ]
        runtimes = sorted(
            float(event.duration_ms or 0) / 1000.0
            for event in calculations
            if event.duration_ms is not None
        )

        hourly = build_hourly_profile(sessions, events, start, now)
        last24_start = now - timedelta(hours=24)
        last24_sessions = db.session.scalars(
            select(TelemetrySession).where(TelemetrySession.last_seen_at >= last24_start - timedelta(minutes=5))
        ).all()
        concurrency_24h = build_concurrency_series(last24_sessions, last24_start, now)
        daily = build_daily_series(sessions, events, start, now)

        forecast_start = now - timedelta(days=FORECAST_DAYS)
        forecast_sessions = db.session.scalars(
            select(TelemetrySession).where(TelemetrySession.last_seen_at >= forecast_start)
        ).all()
        weekly_peaks = build_weekly_peak_concurrency(forecast_sessions, forecast_start, now)
        forecast = linear_peak_forecast(weekly_peaks)

        connected_users, connected_sessions = _connected(now)
        project_bytes = sum(int(project.snapshot_bytes or 0) for project in projects)

        live_snapshot = current_resource_snapshot(
            active_sessions=connected_sessions,
            project_bytes=project_bytes,
            database_bytes=_database_size_bytes(app.config.get("SQLALCHEMY_DATABASE_URI", "")),
        )
        current_vcpus = int(live_snapshot["vcpus"])
        current_memory_gb = live_snapshot["memory_gb"]
        current_instance = os.getenv("TOTALRO_EC2_INSTANCE_TYPE", "t3.micro")
        plan = capacity_plan(
            resources,
            forecast,
            current_vcpus=current_vcpus,
            current_memory_gb=current_memory_gb,
            current_instance=current_instance,
        )

        app_counts: dict[str, int] = {}
        tier_counts: dict[str, int] = {}
        country_counts: dict[str, int] = {}
        for event in events:
            app_name = str(event.application or "suite")
            app_counts[app_name] = app_counts.get(app_name, 0) + 1
        for user in users:
            tier_counts[user.licensed_tier] = tier_counts.get(user.licensed_tier, 0) + 1
            if user.country_name:
                country_counts[user.country_name] = country_counts.get(user.country_name, 0) + 1

        cpu_hours = sum(float(event.cpu_seconds or 0) for event in calculations) / 3600.0
        historical = [
            (
                row["date"],
                {
                    "events": row["events"],
                    "calculations": row["calculations"],
                    "failures": row["failures"],
                    "cpu_seconds": row["cpu_seconds"],
                    "active_users": row["active_users"],
                },
            )
            for row in daily
        ]

        metrics_payload = {
            "timezone": EASTERN_LABEL,
            "hourly": hourly,
            "concurrency_24h": concurrency_24h,
            "daily": daily,
            "forecast": forecast["points"],
        }

        return render_template(
            "auth/admin_metrics.html",
            window=window,
            timezone_label=EASTERN_LABEL,
            users=len(users),
            active_users=len(active_ids),
            connected_users=connected_users,
            connected_sessions=connected_sessions,
            peak_connected_24h=max((point["users"] for point in concurrency_24h), default=0),
            sessions=len(sessions),
            avg_session_s=(sum(durations) / len(durations) if durations else 0.0),
            median_session_s=(median(durations) if durations else 0.0),
            calculations=len(calculations),
            calc_failures=sum(1 for event in calculations if not bool(event.success)),
            avg_runtime_s=(sum(runtimes) / len(runtimes) if runtimes else 0.0),
            p95_runtime_s=_percentile(runtimes, 0.95),
            cpu_hours=cpu_hours,
            project_bytes=project_bytes,
            project_count=len(projects),
            daily=historical,
            app_counts=app_counts,
            tier_counts=tier_counts,
            country_counts=country_counts,
            capacity=plan,
            forecast=forecast,
            live_resource=live_snapshot,
            metrics_payload_json=json.dumps(metrics_payload, separators=(",", ":"), default=str),
            metrics_live_url="/admin/metrics/live",
        )

    app.view_functions["auth.admin_metrics"] = admin_required(_enhanced_admin_metrics)

    def _metrics_live():
        now = _utcnow_local()
        connected_users, connected_sessions = _connected(now)
        project_bytes = int(
            db.session.scalar(select(func.coalesce(func.sum(ProjectRevision.snapshot_bytes), 0))) or 0
        )
        snap = current_resource_snapshot(
            active_sessions=connected_sessions,
            project_bytes=project_bytes,
            database_bytes=_database_size_bytes(app.config.get("SQLALCHEMY_DATABASE_URI", "")),
        )
        return jsonify(
            {
                "ok": True,
                "connected_users": connected_users,
                "connected_sessions": connected_sessions,
                "cpu_pressure_percent": snap["cpu_percent"],
                "memory_percent": snap["memory_percent"],
                "process_memory_mb": snap["process_memory_mb"],
                "sampled_at": now.isoformat(),
                "timezone": EASTERN_LABEL,
            }
        )

    app.add_url_rule(
        "/admin/metrics/live",
        endpoint="suite_metrics_live",
        view_func=admin_required(_metrics_live),
        methods=["GET"],
    )
