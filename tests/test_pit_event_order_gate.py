import unittest
from research.pit_event_order_gate import assess_event

BASE = dict(event_id="a", published_at="2026-01-01T10:00:00Z",
            first_seen_at="2026-01-01T10:01:00Z",
            effective_at="2026-01-01T11:00:00Z",
            source_id="publisher", archive_id="archive")
DECISION = "2026-01-01T10:05:00Z"

class PITEventOrderTests(unittest.TestCase):
    def test_valid_order_is_only_time_pass(self):
        self.assertEqual(assess_event(BASE, DECISION)["status"], "PIT_TIME_PASS_ONLY")
    def test_future_capture_rejected(self):
        self.assertEqual(assess_event({**BASE, "first_seen_at": "2026-01-01T10:06:00Z"}, DECISION)["reason"], "not_known_at_decision")
    def test_publication_after_capture_rejected(self):
        self.assertEqual(assess_event({**BASE, "published_at": "2026-01-01T10:02:00Z"}, DECISION)["reason"], "publication_after_capture")
    def test_effective_before_publication_rejected(self):
        self.assertEqual(assess_event({**BASE, "effective_at": "2026-01-01T09:59:00Z"}, DECISION)["reason"], "effective_before_publication")
    def test_naive_timestamp_rejected(self):
        self.assertEqual(assess_event({**BASE, "published_at": "2026-01-01T10:00:00"}, DECISION)["reason"], "invalid_timestamp")
    def test_missing_archive_rejected(self):
        self.assertEqual(assess_event({**BASE, "archive_id": ""}, DECISION)["reason"], "missing_evidence")
    def test_offset_normalized(self):
        self.assertEqual(assess_event({**BASE, "first_seen_at": "2026-01-01T11:01:00+01:00"}, DECISION)["status"], "PIT_TIME_PASS_ONLY")

if __name__ == "__main__":
    unittest.main()
