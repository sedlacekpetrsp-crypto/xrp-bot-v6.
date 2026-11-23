"""Synthetic diagnostic: excluded observations inside a 14-day G1 episode.

This is a characterization test, not a proposal to change the frozen episode
definition. It records the current behavior for independent methodological
review before any alteration to the G1 power gate.
"""
import unittest
from datetime import datetime, timedelta, timezone
from research.top_risk_radar_v1.g1_power_pregate import _episodes

UTC = timezone.utc


class ExclusionGapCharacterization(unittest.TestCase):
    def test_excluded_middle_row_does_not_create_positive_but_groups_endpoints(self):
        t = datetime(2024, 3, 1, 0, 5, tzinfo=UTC)
        decisions = [t, t + timedelta(days=5), t + timedelta(days=10)]
        labels = [True, None, True]
        episodes = _episodes(decisions, labels, range(3))
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["positive_decisions"], 2)

    def test_gap_longer_than_fourteen_days_separates_positives(self):
        t = datetime(2024, 3, 1, 0, 5, tzinfo=UTC)
        decisions = [t, t + timedelta(days=5), t + timedelta(days=15)]
        labels = [True, None, True]
        episodes = _episodes(decisions, labels, range(3))
        self.assertEqual(len(episodes), 2)

    def test_excluded_positive_never_counts_as_event(self):
        t = datetime(2024, 3, 1, 0, 5, tzinfo=UTC)
        decisions = [t, t + timedelta(days=5), t + timedelta(days=10)]
        labels = [False, None, False]
        self.assertEqual(_episodes(decisions, labels, range(3)), [])


if __name__ == "__main__":
    unittest.main()
