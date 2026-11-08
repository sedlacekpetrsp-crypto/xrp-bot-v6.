"""Unit checks for fail-closed PIT guard; no market data or performance backtest."""
import unittest

from research.top_risk_radar_v1.pit_guard import feature_is_available, label_is_mature, parse_utc


class PitGuardTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "event_time": "2026-11-07T23:58:00Z",
            "source_published_at": "2026-11-08T00:01:00Z",
            "collector_received_at": "2026-11-08T00:04:59Z",
        }
        self.decision = "2026-11-08T00:05:00Z"

    def test_valid_record(self):
        self.assertTrue(feature_is_available(self.record, self.decision))

    def test_future_publication_is_rejected(self):
        self.record["source_published_at"] = "2026-11-08T00:05:01Z"
        self.assertFalse(feature_is_available(self.record, self.decision))

    def test_late_collector_receipt_is_rejected(self):
        self.record["collector_received_at"] = "2026-11-08T00:05:01Z"
        self.assertFalse(feature_is_available(self.record, self.decision))

    def test_future_event_is_rejected(self):
        self.record["event_time"] = "2026-11-08T00:05:00Z"
        self.assertFalse(feature_is_available(self.record, self.decision))

    def test_missing_publication_fails_closed(self):
        del self.record["source_published_at"]
        with self.assertRaises(KeyError):
            feature_is_available(self.record, self.decision)

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            parse_utc("2026-11-08T00:05:00")

    def test_offsets_are_normalized(self):
        self.record["collector_received_at"] = "2026-11-08T01:04:59+01:00"
        self.assertTrue(feature_is_available(self.record, self.decision))

    def test_negative_label_requires_full_horizon(self):
        self.assertFalse(label_is_mature(self.decision, "2026-11-22T00:04:59Z", 336))
        self.assertTrue(label_is_mature(self.decision, "2026-11-22T00:05:00Z", 336))

    def test_invalid_horizon_rejected(self):
        with self.assertRaises(ValueError):
            label_is_mature(self.decision, self.decision, 0)


if __name__ == "__main__":
    unittest.main()
