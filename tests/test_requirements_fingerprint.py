from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from deploy.requirements_fingerprint import RequirementsFingerprintError, fingerprint


class RequirementsFingerprintTests(unittest.TestCase):
    def _root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        self.addCleanup(temp.cleanup)
        return root

    def test_transitive_include_change_invalidates_fingerprint(self):
        root = self._root()
        wrapper = "-r requirements.txt\ngunicorn>=23,<24\n"
        (root / "requirements-server.txt").write_text(wrapper, encoding="utf-8")
        (root / "requirements.txt").write_text("Flask>=3,<4\n", encoding="utf-8")
        before, records = fingerprint(root / "requirements-server.txt", root)
        self.assertEqual([r.path for r in records], ["requirements-server.txt", "requirements.txt"])
        (root / "requirements.txt").write_text("Flask>=3,<4\npyotp>=2.9,<3\n", encoding="utf-8")
        after, _ = fingerprint(root / "requirements-server.txt", root)
        self.assertEqual((root / "requirements-server.txt").read_text(encoding="utf-8"), wrapper)
        self.assertNotEqual(before, after)

    def test_segno_transitive_change_invalidates_byte_identical_wrapper(self):
        root = self._root()
        wrapper = b"-r requirements.txt\ngunicorn>=23,<24\n"
        (root / "requirements-server.txt").write_bytes(wrapper)
        (root / "requirements.txt").write_text("Flask>=3.1.3,<4\npyotp>=2.9,<3\ncryptography>=45,<47\n", encoding="utf-8")
        before, _ = fingerprint(root / "requirements-server.txt", root)
        before_wrapper = (root / "requirements-server.txt").read_bytes()
        (root / "requirements.txt").write_text("Flask>=3.1.3,<4\npyotp>=2.9,<3\ncryptography>=45,<47\nsegno>=1.6,<2\n", encoding="utf-8")
        after, _ = fingerprint(root / "requirements-server.txt", root)
        self.assertEqual(before_wrapper, wrapper)
        self.assertEqual((root / "requirements-server.txt").read_bytes(), wrapper)
        self.assertNotEqual(before, after)

    def test_nested_include_graph_is_recursive(self):
        root = self._root()
        (root / "requirements-server.txt").write_text("--requirement requirements.txt\n", encoding="utf-8")
        (root / "requirements.txt").write_text("-r requirements/extra.txt\nFlask>=3,<4\n", encoding="utf-8")
        (root / "requirements").mkdir()
        (root / "requirements/extra.txt").write_text("cryptography>=45,<47\n", encoding="utf-8")
        _digest, records = fingerprint(root / "requirements-server.txt", root)
        self.assertEqual([r.path for r in records], ["requirements-server.txt", "requirements.txt", "requirements/extra.txt"])

    def test_deeper_include_change_invalidates_fingerprint(self):
        root = self._root()
        (root / "requirements-server.txt").write_text("-r requirements.txt\n", encoding="utf-8")
        (root / "requirements.txt").write_text("-r requirements/extra.txt\n", encoding="utf-8")
        (root / "requirements").mkdir()
        (root / "requirements/extra.txt").write_text("cryptography>=45,<47\n", encoding="utf-8")
        before, _ = fingerprint(root / "requirements-server.txt", root)
        (root / "requirements/extra.txt").write_text("cryptography>=45,<47\npyotp>=2.9,<3\n", encoding="utf-8")
        after, _ = fingerprint(root / "requirements-server.txt", root)
        self.assertNotEqual(before, after)

    def test_compact_r_syntax_is_supported(self):
        root = self._root()
        (root / "requirements-server.txt").write_text("-rrequirements.txt\n", encoding="utf-8")
        (root / "requirements.txt").write_text("Flask>=3,<4\n", encoding="utf-8")
        _digest, records = fingerprint(root / "requirements-server.txt", root)
        self.assertEqual(len(records), 2)

    def test_cycle_fails_closed(self):
        root = self._root()
        (root / "requirements-server.txt").write_text("-r requirements.txt\n", encoding="utf-8")
        (root / "requirements.txt").write_text("-r requirements-server.txt\n", encoding="utf-8")
        with self.assertRaisesRegex(RequirementsFingerprintError, "cycle"):
            fingerprint(root / "requirements-server.txt", root)

    def test_repo_escape_fails_closed(self):
        parent = self._root()
        root = parent / "repo"
        root.mkdir()
        outside = parent / "outside.txt"
        outside.write_text("Flask>=3,<4\n", encoding="utf-8")
        (root / "requirements-server.txt").write_text("-r ../outside.txt\n", encoding="utf-8")
        with self.assertRaisesRegex(RequirementsFingerprintError, "escapes repository root"):
            fingerprint(root / "requirements-server.txt", root)

    def test_missing_include_fails_closed(self):
        root = self._root()
        (root / "requirements-server.txt").write_text("-r requirements.txt\n", encoding="utf-8")
        with self.assertRaisesRegex(RequirementsFingerprintError, "does not exist"):
            fingerprint(root / "requirements-server.txt", root)


if __name__ == "__main__":
    unittest.main()
