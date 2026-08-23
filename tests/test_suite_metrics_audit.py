from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
import os
import unittest

import suite_metrics
import suite_metrics_audit

suite_metrics_audit.apply_suite_metrics_audit_corrections(suite_metrics)


def _session(user_id, start, end):
    return SimpleNamespace(user_id=user_id, started_at=start, last_seen_at=end, ended_at=end)


class SuiteMetricsAuditTests(unittest.TestCase):
    def test_hourly_average_includes_zero_activity_slots(self):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(days=2)
        sessions = [_session(1, start + timedelta(hours=8), start + timedelta(hours=9))]
        profile = suite_metrics.build_hourly_profile(
            sessions, [], start, end, tz=timezone.utc, slot_minutes=15
        )
        self.assertEqual(profile[8]["peak_users"], 1)
        self.assertEqual(profile[8]["avg_users"], 0.5)

    def test_capacity_concurrency_is_unique_user_based(self):
        samples = [
            SimpleNamespace(cpu_percent=30.0, memory_percent=40.0, active_sessions=20)
            for _ in range(60)
        ]
        forecast = {
            "current_peak": 3,
            "forecast_4w": 4,
            "forecast_8w": 5,
            "growth_per_week": 0.25,
            "points": [
                {"label": "W1", "observed": 2, "forecast": None},
                {"label": "W2", "observed": 3, "forecast": 3},
            ],
        }
        with patch.object(suite_metrics_audit, "_resolved_instance_type", return_value=("c7i.large", "test")):
            plan = suite_metrics.capacity_plan(
                samples, forecast, current_vcpus=2, current_memory_gb=4.0, current_instance="t3.micro"
            )
        self.assertEqual(plan["observed_peak"], 3)
        self.assertEqual(plan["forecast_peak_8w"], 5)
        self.assertEqual(plan["safe_concurrency"], 6)
        self.assertIn("unique authenticated users", plan["method_note"])

    def test_unverified_host_never_fabricates_t3_micro(self):
        samples = [SimpleNamespace(cpu_percent=20.0, memory_percent=30.0, active_sessions=1) for _ in range(60)]
        forecast = {"current_peak": 1, "forecast_4w": 1, "forecast_8w": 1, "growth_per_week": 0.0, "points": []}
        with patch.dict(os.environ, {}, clear=False), \
             patch.object(suite_metrics_audit, "_resolved_instance_type", return_value=(None, "unverified")):
            plan = suite_metrics.capacity_plan(
                samples, forecast, current_vcpus=2, current_memory_gb=4.0, current_instance="t3.micro"
            )
        self.assertNotIn("t3.micro", plan["current"])
        self.assertIn("instance type unavailable", plan["current"])

    def test_configured_instance_type_is_reported(self):
        with patch.dict(os.environ, {"TOTALRO_EC2_INSTANCE_TYPE": "c7i.xlarge"}, clear=False):
            suite_metrics_audit._INSTANCE_TYPE_CHECKED = False
            suite_metrics_audit._INSTANCE_TYPE_CACHE = None
            instance, source = suite_metrics_audit._resolved_instance_type()
        self.assertEqual(instance, "c7i.xlarge")
        self.assertEqual(source, "environment")


if __name__ == "__main__":
    unittest.main()
