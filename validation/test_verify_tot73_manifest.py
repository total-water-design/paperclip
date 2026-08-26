import hashlib
import json
import shutil
import tempfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_tot73_manifest import verify

HERE = Path(__file__).resolve().parent
MANIFEST = "TOT-73_CONVENTIONAL_RO_VECTOR_MANIFEST.json"
APPROVAL = "TOT-73_CONVENTIONAL_RO_APPROVAL.json"

class Tot73VerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        shutil.copytree(HERE, self.repo / "validation", ignore=shutil.ignore_patterns("__pycache__", "test_*.py"))
        self.manifest = self.repo / "validation" / MANIFEST
        self.approval = self.repo / "validation" / APPROVAL
    def tearDown(self):
        self.temp.cleanup()
    def approved(self):
        record = json.loads(self.approval.read_text())
        record.update(approved_by="test-board", approved_at="2026-08-26T00:00:00Z",
                      approval_record="test-interaction", candidate_commit_sha="a" * 40,
                      manifest_sha256=hashlib.sha256(self.manifest.read_bytes()).hexdigest())
        self.approval.write_text(json.dumps(record))
    def test_current_draft_is_pending_human_approval(self):
        status, details = verify(self.manifest, self.approval)
        self.assertEqual("PENDING", status)
        self.assertIn("incomplete", details[0])
    def test_missing_or_modified_source_fails_closed(self):
        source = self.repo / "validation/sources/RO-FilmTec-BW30-PRO-400-PDS-45-D03742-en.pdf"
        source.unlink()
        self.assertEqual("FAIL", verify(self.manifest, self.approval)[0])
        shutil.copy2(HERE / "sources/RO-FilmTec-BW30-PRO-400-PDS-45-D03742-en.pdf", source)
        source.write_bytes(source.read_bytes() + b"modified")
        self.assertEqual("FAIL", verify(self.manifest, self.approval)[0])
    def assert_manifest_mutation_fails(self, mutate):
        self.approved()
        data = json.loads(self.manifest.read_text())
        mutate(data)
        self.manifest.write_text(json.dumps(data))
        status, details = verify(self.manifest, self.approval)
        self.assertEqual("FAIL", status)
        self.assertIn("manifest_sha256", details[0])

    def test_altered_vector_fails_approval_integrity(self):
        self.assert_manifest_mutation_fails(
            lambda data: data["cases"][0]["expected_outputs"].update(
                permeate_flow_m3_h=999))

    def test_altered_tolerance_fails_approval_integrity(self):
        self.assert_manifest_mutation_fails(
            lambda data: data["registry"]["quantity_rules"][0].update(
                absolute_tolerance=999))
    def test_correct_detached_approval_passes(self):
        self.approved()
        self.assertEqual(("PASS", []), verify(self.manifest, self.approval))

if __name__ == "__main__":
    unittest.main()
