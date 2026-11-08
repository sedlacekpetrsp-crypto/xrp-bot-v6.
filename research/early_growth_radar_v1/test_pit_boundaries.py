"""Synthetic 30-day upside-radar PIT boundary regression tests (PAPER only).

No historical data, model fitting, trading, or performance evaluation.
"""
import unittest

from research.top_risk_radar_v1.pit_guard import feature_is_available, label_is_mature


class EarlyGrowthPitBoundaryTests(unittest.TestCase):
    DECISION = "2026-11-08T00:05:00Z"
    RECORD = {
        "event_time": "2026-11-07T23:59:59Z",
        "source_published_at": "2026-11-08T00:05:00Z",
        "collector_received_at": "2026-11-08T00:05:00Z",
    }

    def test_30_day_label_unmatured_one_second_before_cutoff(self):
        self.assertFalse(label_is_mature(self.DECISION, "2026-12-08T00:04:59Z", 720))

    def test_30_day_label_matures_at_exact_cutoff(self):
        self.assertTrue(label_is_mature(self.DECISION, "2026-12-08T00:05:00Z", 720))

    def test_14_day_cutoff_does_not_mature_30_day_target(self):
        self.assertFalse(label_is_mature(self.DECISION, "2026-11-22T00:05:00Z", 720))

    def test_publication_and_receipt_at_decision_are_allowed(self):
        self.assertTrue(feature_is_available(dict(self.RECORD), self.DECISION))

    def test_event_at_decision_is_forbidden_even_when_published(self):
        record = dict(self.RECORD, event_time=self.DECISION)
        self.assertFalse(feature_is_available(record, self.DECISION))

    def test_future_receipt_rejected_despite_early_publication(self):
        record = dict(self.RECORD, collector_received_at="2026-11-08T00:05:01Z")
        self.assertFalse(feature_is_available(record, self.DECISION))

    def test_missing_receipt_fails_closed(self):
        record = dict(self.RECORD)
        del record["collector_received_at"]
        with self.assertRaises(KeyError):
            feature_is_available(record, self.DECISION)


if __name__ == "__main__":
    unittest.main()
