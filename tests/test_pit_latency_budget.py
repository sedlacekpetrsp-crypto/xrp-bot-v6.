import unittest

from research.pit_latency_budget import assess_event_availability as assess


class PITLatencyBudgetTests(unittest.TestCase):
    def setUp(self):
        self.pub = "2026-01-01T10:00:00Z"
        self.cap = "2026-01-01T10:00:05Z"
        self.dec = "2026-01-01T10:00:10Z"

    def test_valid_lead(self):
        self.assertTrue(assess(self.pub, self.cap, self.dec, 4, 2)["eligible"])

    def test_exact_boundary_rejected(self):
        self.assertFalse(assess(self.pub, self.cap, self.dec, 5, 0)["eligible"])

    def test_late_capture_rejected(self):
        self.assertFalse(assess(self.pub, "2026-01-01T10:00:11Z", self.dec, 0, 0)["eligible"])

    def test_capture_before_publication_rejected(self):
        self.assertEqual(assess(self.pub, "2026-01-01T09:59:59Z", self.dec, 0, 0)["reason"],
                         "capture_precedes_publication")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            assess("2026-01-01T10:00:00", self.cap, self.dec, 0, 0)

    def test_nonfinite_latency_rejected(self):
        for value in (float("nan"), float("inf"), -1, True, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess(self.pub, self.cap, self.dec, value, 0)

    def test_timezone_normalization(self):
        self.assertTrue(assess("2026-01-01T11:00:00+01:00", self.cap, self.dec, 4, 0)["eligible"])


if __name__ == "__main__":
    unittest.main()
