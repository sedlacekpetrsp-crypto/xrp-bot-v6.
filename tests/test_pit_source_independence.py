"""Synthetic regression cases; no historical or performance evaluation."""
import unittest
from research.pit_source_independence import independent_source_gate

T = "2026-01-03T00:00:00Z"

def rec(origin="exchange", source_id="a", content_hash="abc",
        published_at="2026-01-01T00:00:00Z", captured_at="2026-01-02T00:00:00Z"):
    return dict(origin=origin, source_id=source_id, content_hash=content_hash,
                published_at=published_at, captured_at=captured_at)


class SourceIndependenceTests(unittest.TestCase):
    def gate(self, rows):
        return independent_source_gate(rows, decision_at=T)

    def test_two_independent_origins(self):
        self.assertEqual(self.gate([rec(), rec("regulator", "b")])["status"], "DATA_GO")

    def test_two_mirrors_same_origin(self):
        self.assertEqual(self.gate([rec(), rec("EXCHANGE", "mirror")])["independent_origins"], 1)

    def test_conflicting_same_origin(self):
        self.assertEqual(self.gate([rec(), rec(source_id="mirror", content_hash="xyz")])["reason"], "conflicting_origin_snapshots")

    def test_capture_after_decision(self):
        self.assertEqual(self.gate([rec(captured_at="2026-01-04T00:00:00Z")])["reason"], "not_available_asof")

    def test_published_after_capture(self):
        self.assertEqual(self.gate([rec(published_at="2026-01-03T00:00:00Z")])["reason"], "not_available_asof")

    def test_naive_timestamp(self):
        self.assertEqual(self.gate([rec(captured_at="2026-01-02T00:00:00")])["reason"], "bad_timestamp")

    def test_missing_hash(self):
        self.assertEqual(self.gate([dict(origin="x")])["reason"], "missing_provenance")

    def test_non_dict_record(self):
        self.assertEqual(self.gate([None])["reason"], "bad_record")

    def test_empty(self):
        self.assertEqual(self.gate([])["status"], "DATA_NO_GO")

    def test_no_performance_permission(self):
        self.assertFalse(self.gate([rec(), rec("regulator", "b")])["performance_authorized"])

    def test_invalid_min_sources(self):
        with self.assertRaises(ValueError):
            independent_source_gate([], decision_at=T, min_sources=1)

    def test_invalid_decision_time(self):
        with self.assertRaises(ValueError):
            independent_source_gate([], decision_at="2026-01-03T00:00:00")


if __name__ == "__main__":
    unittest.main()
