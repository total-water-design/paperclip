"""Audit corrections for the Suite Metrics reconciliation milestone.

The source milestone remains authoritative for dashboard behavior.  This module
applies the three reconciliation-audit corrections before the metrics routes are
registered on Alpha: hourly averages include zero-activity slots, capacity
concurrency is expressed only as unique authenticated users, and EC2 instance
identity is never fabricated from a t3.micro default.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from math import ceil, floor
import os
import urllib.request

_INSTANCE_TYPE_CHECKED = False
_INSTANCE_TYPE_CACHE = None


def _imds_instance_type(timeout: float = 0.20):
    """Resolve the EC2 instance type with IMDSv2, returning None off EC2."""
    try:
        token_request = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
        )
        with urllib.request.urlopen(token_request, timeout=timeout) as response:
            token = response.read().decode("utf-8").strip()
        metadata_request = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/instance-type",
            headers={"X-aws-ec2-metadata-token": token},
        )
        with urllib.request.urlopen(metadata_request, timeout=timeout) as response:
            value = response.read().decode("utf-8").strip()
        return value or None
    except Exception:
        return None


def _resolved_instance_type():
    global _INSTANCE_TYPE_CHECKED, _INSTANCE_TYPE_CACHE
    configured = str(os.getenv("TOTALRO_EC2_INSTANCE_TYPE") or "").strip()
    if configured:
        return configured, "environment"
    if not _INSTANCE_TYPE_CHECKED:
        _INSTANCE_TYPE_CACHE = _imds_instance_type()
        _INSTANCE_TYPE_CHECKED = True
    if _INSTANCE_TYPE_CACHE:
        return _INSTANCE_TYPE_CACHE, "ec2-metadata"
    return None, "unverified"


def apply_suite_metrics_audit_corrections(metrics) -> None:
    """Patch the validated metrics facade before register_suite_metrics(app)."""
    if getattr(metrics, "_twds_metrics_audit_corrected", False):
        return

    def build_hourly_profile(sessions, events, start, end, *, tz=metrics.EASTERN, slot_minutes=15):
        """Average/peak unique users by hour including zero-activity slots."""
        sessions = list(sessions)
        events = list(events)
        effective_start = start
        if end - start > timedelta(days=3650):
            candidates = []
            for row in sessions:
                stamp = metrics._aware(getattr(row, "started_at", None))
                if stamp is not None and stamp <= end:
                    candidates.append(stamp)
            for event in events:
                stamp = metrics._aware(getattr(event, "created_at", None))
                if stamp is not None and stamp <= end:
                    candidates.append(stamp)
            effective_start = min(candidates) if candidates else end

        slot_users = defaultdict(set)
        events_by_hour = [0] * 24
        calculations_by_hour = [0] * 24
        active_days = set()

        for row in sessions:
            bounds = metrics._session_bounds(row, end)
            if not bounds:
                continue
            s0, s1 = bounds
            s0, s1 = max(s0, effective_start), min(s1, end)
            if s1 <= s0:
                continue
            uid = int(getattr(row, "user_id", 0) or 0)
            cursor = metrics._floor_slot(s0, slot_minutes)
            while cursor < s1:
                slot_end = cursor + timedelta(minutes=slot_minutes)
                if cursor < s1 and slot_end > s0 and uid:
                    slot_users[cursor].add(uid)
                    active_days.add(cursor.astimezone(tz).date().isoformat())
                cursor += timedelta(minutes=slot_minutes)

        for event in events:
            created = metrics._aware(getattr(event, "created_at", None))
            if created is None or created < effective_start or created > end:
                continue
            hour = created.astimezone(tz).hour
            events_by_hour[hour] += 1
            if str(getattr(event, "event_type", "") or "").startswith("calculation_"):
                calculations_by_hour[hour] += 1

        values_by_hour = [[] for _ in range(24)]
        cursor = metrics._floor_slot(effective_start, slot_minutes)
        while cursor < end:
            slot_end = cursor + timedelta(minutes=slot_minutes)
            if slot_end > effective_start:
                hour = cursor.astimezone(tz).hour
                values_by_hour[hour].append(len(slot_users.get(cursor, set())))
            cursor += timedelta(minutes=slot_minutes)

        result = []
        for hour in range(24):
            values = values_by_hour[hour]
            avg_users = sum(values) / len(values) if values else 0.0
            result.append({
                "hour": hour,
                "label": metrics._hour_label(hour),
                "avg_users": round(avg_users, 2),
                "peak_users": max(values, default=0),
                "events": events_by_hour[hour],
                "calculations": calculations_by_hour[hour],
                "active_days": len(active_days),
            })
        return result

    def capacity_plan(samples, forecast, *, current_vcpus, current_memory_gb, current_instance=None):
        """Capacity plan whose concurrency quantities are all unique users."""
        samples = list(samples)
        cpu_values = [
            float(getattr(s, "cpu_percent", 0) or 0)
            for s in samples if getattr(s, "cpu_percent", None) is not None
        ]
        mem_values = [
            float(getattr(s, "memory_percent", 0) or 0)
            for s in samples if getattr(s, "memory_percent", None) is not None
        ]
        p95_cpu = metrics._percentile(cpu_values, 0.95)
        p95_memory = metrics._percentile(mem_values, 0.95)

        observed_points = [
            int(round(float(point.get("observed", 0) or 0)))
            for point in (forecast.get("points") or [])
            if point.get("observed") is not None
        ]
        observed_peak = max(
            observed_points,
            default=int(forecast.get("current_peak", 0) or 0),
        )
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

        chosen = metrics.AWS_COMPUTE_SHAPES[-1]
        for shape in metrics.AWS_COMPUTE_SHAPES:
            if shape["vcpus"] >= target_vcpus and shape["memory_gb"] >= target_memory:
                chosen = shape
                break

        safe_by_cpu = max(1, int(floor(observed_peak * 70.0 / p95_cpu))) if observed_peak > 0 and p95_cpu > 0 else None
        safe_by_mem = max(1, int(floor(observed_peak * 80.0 / p95_memory))) if observed_peak > 0 and p95_memory > 0 else None
        finite_caps = [x for x in (safe_by_cpu, safe_by_mem) if x]
        safe_concurrency = min(finite_caps) if finite_caps else None

        server_count = 1
        if safe_concurrency and forecast_peak > safe_concurrency:
            server_count = max(2, int(ceil(forecast_peak / max(1, safe_concurrency))))

        sample_count = len(samples)
        insufficient = sample_count < 60 or not cpu_values or not mem_values
        if insufficient:
            status = "collecting_baseline"
            chosen = metrics.AWS_COMPUTE_SHAPES[0] if current_memory_gb < 4.0 else chosen
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
            trigger_weeks = 0 if current_peak >= trigger else max(0, int(ceil((trigger - current_peak) / growth)))

        instance_type, instance_source = _resolved_instance_type()
        current_description = instance_type or "EC2 instance type unavailable"
        current_description += f" / {current_vcpus} vCPU"
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
            "current_instance": instance_type,
            "instance_source": instance_source,
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
                "Directional model using p95 server pressure, observed peak unique authenticated users "
                "and an 8-week least-squares unique-user concurrency trend. It is a planning aid, not an AWS guarantee."
            ),
        }

    metrics.build_hourly_profile = build_hourly_profile
    metrics.capacity_plan = capacity_plan
    metrics._twds_metrics_audit_corrected = True
