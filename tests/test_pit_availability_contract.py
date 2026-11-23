import unittest

from research.pit_availability_contract import (
    PITAvailabilityError, audit_event_availability,
)


class PITAvailabilityContractTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "event_id": "a",
            "publication_at": "2026-01-01T10:00:00Z",
            "observed_at": "2026-01-01T10:05:00+00:00",
        }
        self.decision = "2026-01-01T10:06:00Z"

    def test_valid(self):
        self.assertEqual(audit_event_availability([self.row], self.decision), ("a",))

    def test_observation_after_decision_fails(self):
        with self.assertRaises(PITAvailabilityError):
            audit_event_availability([self.row], "2026-01-01T10:04:00Z")

    def test_missing_observation_fails(self):
        with self.assertRaises(PITAvailabilityError):
            audit_event_availability([{k: v for k, v in self.row.items() if k != "observed_at"}], self.decision)

    def test_naive_time_fails(self):
        with self.assertRaises(PITAvailabilityError):
            audit_event_availability([self.row], "2026-01-01T10:06:00")

    def test_duplicate_fails(self):
        with self.assertRaises(PITAvailabilityError):
            audit_event_availability([self.row, self.row], self.decision)

    def test_observed_before_published_fails(self):
        row = dict(self.row, observed_at="2026-01-01T09:59:00Z")
        with self.assertRaises(PITAvailabilityError):
            audit_event_availability([row], self.decision)

    def test_timezone_normalization(self):
        self.assertEqual(audit_event_availability([self.row], "2026-01-01T11:06:00+01:00"), ("a",))


if __name__ == "__main__":
    unittest.main()
