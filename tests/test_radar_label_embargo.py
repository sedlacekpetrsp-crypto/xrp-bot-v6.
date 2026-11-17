"""Synthetic non-performance tests for radar label PIT gate."""
import unittest
from datetime import datetime, timedelta, timezone
from research.radar_label_embargo import eligible_training_label, LabelEligibilityError

T = datetime(2026, 1, 1, tzinfo=timezone.utc)
def gate(**changes):
    args = dict(feature_at=T, cutoff_at=T + timedelta(days=31),
                horizon_days=30, label_available_at=T + timedelta(days=30),
                data_available_at=T)
    args.update(changes)
    return eligible_training_label(**args)

class RadarLabelEmbargoTests(unittest.TestCase):
    def test_complete_30_day_label(self):
        self.assertTrue(gate())
    def test_complete_14_day_label(self):
        self.assertTrue(gate(horizon_days=14, cutoff_at=T + timedelta(days=14),
                             label_available_at=T + timedelta(days=14)))
    def test_horizon_not_elapsed(self):
        self.assertFalse(gate(cutoff_at=T + timedelta(days=29)))
    def test_label_arrived_after_cutoff(self):
        self.assertFalse(gate(label_available_at=T + timedelta(days=32)))
    def test_feature_not_prior_to_cutoff(self):
        self.assertFalse(gate(feature_at=T + timedelta(days=31),
                              label_available_at=T + timedelta(days=61),
                              data_available_at=T + timedelta(days=31)))
    def test_feature_published_late(self):
        self.assertFalse(gate(data_available_at=T + timedelta(hours=1)))
    def test_missing_label_time_fails_closed(self):
        with self.assertRaises(LabelEligibilityError):
            gate(label_available_at=None)
    def test_naive_timestamp_fails_closed(self):
        with self.assertRaises(LabelEligibilityError):
            gate(cutoff_at=datetime(2026, 2, 1))
    def test_non_utc_offset_fails_closed(self):
        with self.assertRaises(LabelEligibilityError):
            gate(cutoff_at=T.astimezone(timezone(timedelta(hours=1))))
    def test_bool_horizon_fails_closed(self):
        with self.assertRaises(LabelEligibilityError):
            gate(horizon_days=True)
    def test_label_before_horizon_fails_closed(self):
        with self.assertRaises(LabelEligibilityError):
            gate(label_available_at=T + timedelta(days=29))
    def test_past_observation_available_before_feature_is_valid(self):
        self.assertTrue(gate(data_available_at=T - timedelta(days=2)))
    def test_past_observation_at_feature_time_is_valid(self):
        self.assertTrue(gate(data_available_at=T))
    def test_future_observation_unavailable_at_feature_is_rejected(self):
        self.assertFalse(gate(data_available_at=T + timedelta(microseconds=1)))

if __name__ == "__main__":
    unittest.main()
