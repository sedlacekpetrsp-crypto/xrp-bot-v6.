"""Synthetic regression coverage for descriptive anchored episode accounting.

No historical price data, model fitting, or performance backtest.
"""
import unittest
from datetime import datetime, timedelta, timezone

from research.top_risk_radar_v1.anchored_episodes import anchored_episodes

T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)


class AnchoredEpisodeBoundaryTests(unittest.TestCase):
    def test_fourteen_day_boundary_is_inclusive(self):
        dates = [T0, T0 + timedelta(days=14), T0 + timedelta(days=15)]
        result = anchored_episodes(dates, horizon_days=14)
        self.assertEqual([x["positive_decisions"] for x in result], [2, 1])
        self.assertEqual(result[0]["last_decision"], dates[1])

    def test_thirty_day_boundary_is_inclusive(self):
        dates = [T0, T0 + timedelta(days=30), T0 + timedelta(days=31)]
        result = anchored_episodes(dates, horizon_days=30)
        self.assertEqual([x["positive_decisions"] for x in result], [2, 1])

    def test_no_transitive_chaining_for_risk_horizon(self):
        dates = [T0 + timedelta(days=d) for d in (0, 10, 20, 30)]
        result = anchored_episodes(dates, horizon_days=14)
        self.assertEqual([x["positive_decisions"] for x in result], [2, 2])

    def test_duplicate_decision_rejected(self):
        with self.assertRaises(ValueError):
            anchored_episodes([T0, T0], horizon_days=14)

    def test_empty_input_is_empty(self):
        self.assertEqual(anchored_episodes([], horizon_days=30), [])


if __name__ == "__main__":
    unittest.main()
