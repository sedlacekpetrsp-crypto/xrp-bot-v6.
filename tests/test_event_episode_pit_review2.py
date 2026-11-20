"""Claude review 2 (dialog 0417): source-collision check must not depend on input order."""
import itertools
import unittest
from datetime import datetime, timedelta, timezone

from research.event_episode_pit import Event, audit_episodes

T = datetime(2024, 1, 1, tzinfo=timezone.utc)


def ev(i, sym, sec):
    p = T + timedelta(seconds=sec)
    return Event(i, sym, p, p, p + timedelta(hours=1), "SRC")


class CollisionOrderInvariance(unittest.TestCase):
    def test_spread_over_60s_rejected_in_every_order(self):
        rows = [ev("a", "X", 0), ev("b", "Y", 50), ev("c", "Z", 100)]
        for perm in itertools.permutations(rows):
            with self.assertRaises(ValueError):
                audit_episodes(list(perm))

    def test_spread_within_60s_accepted_in_every_order(self):
        rows = [ev("a", "X", 0), ev("b", "Y", 30), ev("c", "Z", 60)]
        for perm in itertools.permutations(rows):
            r = audit_episodes(list(perm))
            self.assertEqual(r["independent_episodes"], 1)
            self.assertEqual(r["per_symbol_episodes"], {"X": 1, "Y": 1, "Z": 1})


if __name__ == "__main__":
    unittest.main()
