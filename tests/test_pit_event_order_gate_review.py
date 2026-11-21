"""Claude review (dialog 0438) of 87df28f/0d4fef5. Strict xfail = known MINOR gaps, not fixed here."""
import unittest
from research.pit_event_order_gate import assess_event

BASE = dict(event_id="a", published_at="2026-01-01T10:00:00Z",
            first_seen_at="2026-01-01T10:01:00Z",
            effective_at="2026-01-01T11:00:00Z",
            source_id="publisher", archive_id="archive")
DECISION = "2026-01-01T10:05:00Z"


class ReviewPassing(unittest.TestCase):
    def test_invalid_decision_fails_closed(self):
        self.assertEqual(assess_event(BASE, None)["status"], "DATA_NO_GO")

    def test_overflow_offset_fails_closed(self):
        e = {**BASE, "published_at": "0001-01-01T00:00:00+01:00"}
        self.assertEqual(assess_event(e, DECISION)["reason"], "invalid_timestamp")

    def test_non_string_timestamp_fails_closed(self):
        self.assertEqual(assess_event({**BASE, "published_at": 1}, DECISION)["reason"], "invalid_timestamp")

    def test_date_only_fails_closed(self):
        self.assertEqual(assess_event({**BASE, "published_at": "2026-01-01"}, DECISION)["reason"], "invalid_timestamp")


class ReviewKnownGaps(unittest.TestCase):
    @unittest.expectedFailure
    def test_o1_capture_at_decision_instant_is_not_known(self):
        # O1 MINOR: seen == decision passes; no processing latency -> same-instant leakage.
        e = {**BASE, "first_seen_at": DECISION}
        self.assertEqual(assess_event(e, DECISION)["status"], "DATA_NO_GO")

    @unittest.expectedFailure
    def test_o2_whitespace_identifier_is_missing(self):
        # O2 MINOR: whitespace-only source_id counts as present.
        self.assertEqual(assess_event({**BASE, "source_id": "  "}, DECISION)["status"], "DATA_NO_GO")

    @unittest.expectedFailure
    def test_o2_bool_identifier_is_missing(self):
        # O2 MINOR: non-string identifiers (True) count as present.
        self.assertEqual(assess_event({**BASE, "event_id": True}, DECISION)["status"], "DATA_NO_GO")


if __name__ == "__main__":
    unittest.main()
