"""Synthetic-only regression checks; no historical performance run."""
import unittest
from datetime import datetime, timedelta, timezone
from research.k11_execution_feasibility import Quote, execution_gate

NOW = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)


def quote(**changes):
    fields = dict(observed_at=NOW - timedelta(seconds=2),
                  available_at=NOW - timedelta(seconds=1),
                  bid=0.999, ask=1.001,
                  bid_depth_usd=10000, ask_depth_usd=10000)
    fields.update(changes)
    return Quote(**fields)


class TestK11ExecutionFeasibility(unittest.TestCase):
    def test_clean_diagnostic(self):
        result = execution_gate(quote(), NOW, 1000)
        self.assertTrue(result.eligible)
        self.assertAlmostEqual(result.round_trip_cost_bps, 34.0)

    def test_pit_future_availability(self):
        self.assertEqual(execution_gate(quote(available_at=NOW + timedelta(seconds=1)), NOW, 1000).reason, "pit_unavailable")

    def test_pit_availability_before_observation(self):
        self.assertEqual(execution_gate(quote(available_at=NOW - timedelta(seconds=3)), NOW, 1000).reason, "pit_unavailable")

    def test_stale(self):
        self.assertEqual(execution_gate(quote(observed_at=NOW - timedelta(seconds=40)), NOW, 1000).reason, "stale_quote")

    def test_naive_time(self):
        self.assertEqual(execution_gate(quote(), NOW.replace(tzinfo=None), 1000).reason, "timezone_missing")

    def test_crossed(self):
        self.assertEqual(execution_gate(quote(ask=0.998), NOW, 1000).reason, "crossed_or_locked")

    def test_depth(self):
        self.assertEqual(execution_gate(quote(bid_depth_usd=1999), NOW, 1000).reason, "insufficient_depth")

    def test_high_spread(self):
        self.assertEqual(execution_gate(quote(bid=0.99, ask=1.01), NOW, 1000).reason, "cost_exceeds_cap")

    def test_nonfinite(self):
        self.assertEqual(execution_gate(quote(bid=float("nan")), NOW, 1000).reason, "nonfinite")

    def test_zero_notional(self):
        self.assertEqual(execution_gate(quote(), NOW, 0).reason, "invalid_input")


if __name__ == "__main__":
    unittest.main()
