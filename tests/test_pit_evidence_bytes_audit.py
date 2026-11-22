import hashlib
import tempfile
import unittest
from pathlib import Path

from research.pit_evidence_bytes_audit import verify_manifest_bytes


class EvidenceBytesAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "evidence.txt").write_bytes(b"evidence")
        self.good = hashlib.sha256(b"evidence").hexdigest()

    def check(self, path, digest):
        return verify_manifest_bytes(self.root, [{"path": path, "sha256": digest}])[0]["status"]

    def test_valid(self):
        self.assertEqual(self.check("evidence.txt", self.good), "OK")

    def test_wrong_hash(self):
        self.assertEqual(self.check("evidence.txt", "0" * 64), "HASH_MISMATCH")

    def test_missing(self):
        self.assertEqual(self.check("missing", self.good), "MISSING_OR_LINK")

    def test_parent_traversal(self):
        self.assertEqual(self.check("../secret", self.good), "INVALID")

    def test_absolute_path(self):
        self.assertEqual(self.check("/etc/passwd", self.good), "INVALID")

    def test_uppercase_hash(self):
        self.assertEqual(self.check("evidence.txt", self.good.upper()), "INVALID")

    def test_duplicate(self):
        rows = [{"path": "evidence.txt", "sha256": self.good}] * 2
        self.assertEqual([r["status"] for r in verify_manifest_bytes(self.root, rows)], ["OK", "DUPLICATE"])

    def test_symlink(self):
        (self.root / "link").symlink_to(self.root / "evidence.txt")
        self.assertEqual(self.check("link", self.good), "MISSING_OR_LINK")

    def test_backslash(self):
        self.assertEqual(self.check("dir\\file", self.good), "INVALID")

    def test_nested_file(self):
        (self.root / "sub").mkdir()
        (self.root / "sub" / "x").write_bytes(b"evidence")
        self.assertEqual(self.check("sub/x", self.good), "OK")


if __name__ == "__main__":
    unittest.main()
