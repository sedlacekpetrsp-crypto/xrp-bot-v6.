"""Claude review (dialog 0458) of excluded-gap semantics. Characterization only.

Grouping depends solely on distances between evaluated positive decisions, so an
excluded (None) row is equivalent to a negative or to an absent row. Its only
possible effect is the *opposite* of bridging: if the hidden label had been
positive it could have chained two positives > 14 d apart, so exclusion can
split (never merge) episodes, i.e. it can only raise the episode count.
"""
import unittest
from datetime import datetime, timedelta, timezone
from research.top_risk_radar_v1.g1_power_pregate import _episodes

T = datetime(2024, 3, 1, 0, 5, tzinfo=timezone.utc)


class ExcludedRowEquivalence(unittest.TestCase):
    def test_none_equivalent_to_false_and_to_absent(self):
        d = [T, T + timedelta(days=5), T + timedelta(days=10)]
        none = _episodes(d, [True, None, True], range(3))
        false = _episodes(d, [True, False, True], range(3))
        absent = _episodes([d[0], d[2]], [True, True], range(2))
        self.assertEqual(none, false)
        self.assertEqual(none, absent)

    def test_exclusion_can_split_but_not_merge(self):
        d = [T, T + timedelta(days=10), T + timedelta(days=20)]
        excluded = _episodes(d, [True, None, True], range(3))
        hidden_positive = _episodes(d, [True, True, True], range(3))
        self.assertEqual(len(excluded), 2)
        self.assertEqual(len(hidden_positive), 1)


if __name__ == "__main__":
    unittest.main()
