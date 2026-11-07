import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from research.top_risk_radar_v1.label_events import Trade, label_decision, point_in_time_eligible

T = datetime(2025, 1, 1, 0, 5, tzinfo=timezone.utc)
def tr(seconds, price):
    return Trade(T + timedelta(seconds=seconds), Decimal(str(price)))

class TestEventLabel(unittest.TestCase):
    def test_hit_inside_window(self):
        x = label_decision(T, [tr(1, 1), tr(10, .79)], T + timedelta(days=1))
        self.assertEqual(x.outcome, 1)
    def test_exact_threshold(self):
        self.assertEqual(label_decision(T, [tr(1, 1), tr(2, .8)], T + timedelta(days=1)).outcome, 1)
    def test_unmatured_not_negative(self):
        self.assertIsNone(label_decision(T, [tr(1, 1)], T + timedelta(days=13)).outcome)
    def test_matured_requires_coverage(self):
        self.assertEqual(label_decision(T, [tr(1, 1)], T + timedelta(days=15)).status, "negative_requires_coverage_qa")
    def test_hit_outside_horizon(self):
        x = label_decision(T, [tr(1, 1), tr(336*3600+1, .5)], T + timedelta(days=15))
        self.assertEqual(x.outcome, 0)
    def test_missing_reference(self):
        self.assertEqual(label_decision(T, [tr(62, 1)], T + timedelta(days=15)).status, "missing_reference")
    def test_future_publication_not_eligible(self):
        self.assertFalse(point_in_time_eligible(T-timedelta(hours=1), T+timedelta(seconds=1), T))
    def test_timestamp_must_be_utc(self):
        with self.assertRaises(ValueError):
            tr(1, 1).__class__(datetime(2025,1,1), Decimal("1"))

if __name__ == "__main__":
    unittest.main()
