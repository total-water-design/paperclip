"""Focused regression tests for the non-mutating TWDS host validator."""
from __future__ import annotations

import argparse
import importlib.util
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("twds_host_validator", Path(__file__).with_name("twds-host-validator.py"))
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class HostValidatorFinalizationTest(unittest.TestCase):
    def test_finalization_verifies_comment_status_and_fresh_human_gate(self) -> None:
        calls: list[tuple[str, str, dict[str, object]]] = []
        verdict = {"version": 1, "verdict": "PASS", "requestedSha": "a" * 40, "nextStep": "Proceed."}
        args = argparse.Namespace(
            originating_issue_id="TOT-207", paperclip_api_url="http://paperclip.test", paperclip_api_key="key",
            final_status="in_review", human_review_required=True,
        )

        def request(base: str, key: str, method: str, path: str, payload: dict[str, object], out: Path) -> object:
            calls.append((method, path, payload))
            if path.endswith("/interactions"):
                return {"id": "gate-1", "status": "pending", "resolverPolicy": "human_only"}
            return {"id": "write"}

        def get(base: str, key: str, path: str, out: Path) -> object:
            if path.endswith("/comments"):
                return {"comments": [{"body": "Host validation verdict: PASS\n\nCandidate: " + "a" * 40 + "\nNext step: Proceed."}]}
            if path.endswith("/interactions"):
                return {"interactions": [{"id": "gate-1", "status": "pending", "resolverPolicy": "human_only"}]}
            return {"status": "in_review"}

        original_request, original_get = VALIDATOR.api_request, VALIDATOR.api_get
        VALIDATOR.api_request, VALIDATOR.api_get = request, get
        try:
            with tempfile.TemporaryDirectory() as directory:
                VALIDATOR.finalize(verdict, args, Path(directory))
        finally:
            VALIDATOR.api_request, VALIDATOR.api_get = original_request, original_get

        self.assertEqual([call[:2] for call in calls], [
            ("POST", "/api/issues/TOT-207/comments"),
            ("PATCH", "/api/issues/TOT-207"),
            ("POST", "/api/issues/TOT-207/interactions"),
        ])
        self.assertEqual(calls[-1][2]["resolverPolicy"], "human_only")


if __name__ == "__main__":
    unittest.main()
