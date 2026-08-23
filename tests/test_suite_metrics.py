from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from suite_metrics import (
    build_concurrency_series,
    build_daily_series,
    build_hourly_profile,
    capacity_plan,
    linear_peak_forecast,
)


def session(user_id, start, end):
    return SimpleNamespace(
        user_id=user_id,
        started_at=start,
        last_seen_at=end,
        ended_at=end,
    )


class SuiteMetricsTests(unittest.TestCase):
    def test_hourly_profile_uses_eastern_clock(self):
        start = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc)
        rows = [
            session(
                1,
                datetime(2026, 1, 15, 13, 0, tzinfo=timezone.utc),
                datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc),
            )
        ]
        events = [
            SimpleNamespace(
                created_at=datetime(2026, 1, 15, 13, 30, tzinfo=timezone.utc),
                event_type="calculation_completed",
                success=True,
                cpu_seconds=8.0,
            )
        ]
        profile = build_hourly_profile(rows, events, start, end)
        self.assertEqual(profile[8]["label"], "8 AM")
        self.assertEqual(profile[8]["peak_users"], 1)
        self.assertEqual(profile[8]["calculations"], 1)
        self.assertEqual(profile[9]["peak_users"], 0)

    def test_concurrency_counts_unique_users(self):
        start = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
        end = start + timedelta(hours=2)
        rows = [
            session(1, start, end),
            session(1, start + timedelta(minutes=15), end),
            session(2, start + timedelta(minutes=30), end),
        ]
        points = build_concurrency_series(rows, start, end, step_minutes=30)
        at_one_hour = next(p for p in points if p["timestamp"] == (start + timedelta(hours=1)).isoformat())
        self.assertEqual(at_one_hour["users"], 2)

    def test_daily_series_aggregates_users_and_failures(self):
        start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(days=2)
        rows = [session(7, start + timedelta(hours=15), start + timedelta(hours=16))]
        events = [
            SimpleNamespace(
                created_at=start + timedelta(hours=15, minutes=30),
                event_type="calculation_failed",
                success=False,
                cpu_seconds=4.0,
            )
        ]
        daily = build_daily_series(rows, events, start, end)
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0]["active_users"], 1)
        self.assertEqual(daily[0]["calculations"], 1)
        self.assertEqual(daily[0]["failures"], 1)

    def test_linear_forecast_detects_growth(self):
        weekly = [
            {"label": f"W{i}", "week_start": f"2026-01-{1 + 7*i:02d}", "peak_users": i + 1}
            for i in range(4)
        ]
        forecast = linear_peak_forecast(weekly, weeks_forward=8)
        self.assertEqual(forecast["confidence"], "directional")
        self.assertGreater(forecast["growth_per_week"], 0)
        self.assertGreater(forecast["forecast_8w"], forecast["current_peak"])

    def test_capacity_plan_uses_measured_pressure_and_forecast(self):
        samples = [
            SimpleNamespace(cpu_percent=30.0, memory_percent=40.0, active_sessions=2)
            for _ in range(60)
        ]
        forecast = {
            "current_peak": 2,
            "forecast_4w": 3,
            "forecast_8w": 4,
            "growth_per_week": 0.5,
        }
        plan = capacity_plan(
            samples,
            forecast,
            current_vcpus=2,
            current_memory_gb=1.0,
            current_instance="t3.micro",
        )
        self.assertEqual(plan["status"], "plan_upgrade")
        self.assertEqual(plan["recommended_instance"], "c7i.xlarge")
        self.assertEqual(plan["recommended_servers"], 1)
        self.assertIsNotNone(plan["safe_concurrency"])

    def test_capacity_plan_does_not_fake_confidence_without_samples(self):
        forecast = {
            "current_peak": 1,
            "forecast_4w": 1,
            "forecast_8w": 1,
            "growth_per_week": 0.0,
        }
        plan = capacity_plan(
            [],
            forecast,
            current_vcpus=2,
            current_memory_gb=1.0,
            current_instance="t3.micro",
        )
        self.assertEqual(plan["status"], "collecting_baseline")
        self.assertEqual(plan["recommended_instance"], "c7i.large")


if __name__ == "__main__":
    unittest.main()
