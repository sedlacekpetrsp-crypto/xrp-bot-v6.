"""Synthetic-only tests: python -m unittest discover -s research -p 'test_g1_b1_provenance_preflight.py'"""
import hashlib
import tempfile
import unittest
from pathlib import Path
from g1_b1_provenance_preflight import audit_b1, ProvenanceError


class B1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "sample.json").write_bytes(b'{"synthetic":true}')
        self.row = dict(path="sample.json",
                        sha256=hashlib.sha256(b'{"synthetic":true}').hexdigest(),
                        source_url="https://example.org/archive",
                        published_at="2026-11-01T10:00:00Z",
                        observed_at="2026-11-01T10:01:00Z")
        self.cutoff = "2026-11-01T10:02:00Z"

    def check_rejected(self, **changes):
        with self.assertRaises(ProvenanceError):
            audit_b1([{**self.row, **changes}], self.root, self.cutoff)

    def test_valid(self):
        self.assertEqual(audit_b1([self.row], self.root, self.cutoff), 1)

    def test_observed_at_decision_is_not_pit(self):
        self.check_rejected(observed_at=self.cutoff)

    def test_future_observation(self):
        self.check_rejected(observed_at="2026-11-01T10:03:00Z")

    def test_publication_after_observation(self):
        self.check_rejected(published_at="2026-11-01T10:01:01Z")

    def test_naive_timestamp(self):
        self.check_rejected(observed_at="2026-11-01T10:01:00")

    def test_hash_mismatch(self):
        self.check_rejected(sha256="0" * 64)

    def test_missing_source(self):
        self.check_rejected(source_url="")

    def test_duplicate(self):
        with self.assertRaises(ProvenanceError):
            audit_b1([self.row, self.row], self.root, self.cutoff)

    def test_missing_file(self):
        self.check_rejected(path="missing.json")

    def test_path_escape(self):
        self.check_rejected(path="../outside.json")

    def test_empty_manifest(self):
        with self.assertRaises(ProvenanceError):
            audit_b1([], self.root, self.cutoff)


if __name__ == "__main__":
    unittest.main()
