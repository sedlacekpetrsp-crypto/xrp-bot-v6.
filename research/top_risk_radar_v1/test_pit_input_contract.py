"""Synthetic fail-closed PIT input-contract tests; no performance evaluation."""
import unittest

from research.top_risk_radar_v1.pit_guard import (
    feature_is_available,
    label_is_mature,
    parse_utc,
)


class PitInputContractTests(unittest.TestCase):
    def test_date_only_with_timezone_cannot_be_decision_instant(self):
        for value in ("2026-11-08", "2026-11-08Z", "2026-11-08+00:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_utc(value)

    def test_horizon_requires_positive_integer_not_bool_or_float(self):
        for value in (True, False, 0, -1, 14.0, "14", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                label_is_mature("2026-11-08T00:00:00Z", "2026-11-09T00:00:00Z", value)

    def test_explicit_utc_and_offset_remain_valid(self):
        self.assertEqual(
            parse_utc("2026-11-08T01:00:00+01:00"),
            parse_utc("2026-11-08T00:00:00Z"),
        )

    def test_feature_rejects_date_only_source_timestamp(self):
        record = {
            "event_time": "2026-11-08T00:00:00Z",
            "source_published_at": "2026-11-08+00:00",
            "collector_received_at": "2026-11-08T00:01:00Z",
        }
        with self.assertRaises(ValueError):
            feature_is_available(record, "2026-11-08T00:02:00Z")


if __name__ == "__main__":
    unittest.main()
