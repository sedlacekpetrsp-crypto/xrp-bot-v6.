import unittest
from datetime import datetime, timedelta, timezone
from research.pit_source_independence import audit_independent_sources

T = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def source(publisher, origin, **changes):
    item = dict(publisher_id=publisher, original_source_id=origin,
                published_at=T-timedelta(hours=3),
                first_captured_at=T-timedelta(hours=2),
                evidence_url="https://example.org/archived")
    item.update(changes)
    return item


class TestPitSourceIndependence(unittest.TestCase):
    def test_distinct_originals_pass_diagnostic(self):
        self.assertTrue(audit_independent_sources([source("A", "A1"), source("B", "B1")], T)["accepted"])

    def test_mirrors_are_not_independent(self):
        result = audit_independent_sources([source("A", "origin"), source("B", "origin")], T)
        self.assertFalse(result["accepted"])
        self.assertIn("insufficient_original_sources", result["reasons"])

    def test_same_publisher_is_not_independent(self):
        self.assertFalse(audit_independent_sources([source("A", "1"), source("a", "2")], T)["accepted"])

    def test_capture_at_decision_rejected(self):
        self.assertFalse(audit_independent_sources([source("A", "1", first_captured_at=T),
                                                   source("B", "2")], T)["accepted"])

    def test_capture_before_publication_rejected(self):
        self.assertFalse(audit_independent_sources([source("A", "1", first_captured_at=T-timedelta(hours=4)),
                                                   source("B", "2")], T)["accepted"])

    def test_naive_timestamp_rejected(self):
        self.assertFalse(audit_independent_sources([source("A", "1", published_at=T.replace(tzinfo=None)),
                                                   source("B", "2")], T)["accepted"])

    def test_bad_url_rejected(self):
        self.assertFalse(audit_independent_sources([source("A", "1", evidence_url="http://example.org"),
                                                   source("B", "2")], T)["accepted"])

    def test_empty_identity_rejected(self):
        self.assertFalse(audit_independent_sources([source("A", " "), source("B", "2")], T)["accepted"])

    def test_no_records_rejected(self):
        self.assertFalse(audit_independent_sources([], T)["accepted"])

    def test_boolean_min_publishers_rejected(self):
        with self.assertRaises(ValueError):
            audit_independent_sources([source("A", "1")], T, True)


if __name__ == "__main__":
    unittest.main()
