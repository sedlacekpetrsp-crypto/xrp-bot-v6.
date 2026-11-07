import unittest
from datetime import datetime,timedelta,timezone
from research.top_risk_radar_v1.anchored_episodes import anchored_episodes
T=datetime(2024,1,1,tzinfo=timezone.utc)
class AnchoredEpisodesTests(unittest.TestCase):
    def test_chaining_does_not_merge_distant_events(self):
        dates=[T+timedelta(days=d) for d in (0,10,20,30,40,50)]
        groups=anchored_episodes(dates,horizon_days=30)
        self.assertEqual(len(groups),2)
        self.assertEqual([x["positive_decisions"] for x in groups],[4,2])
    def test_single(self):
        self.assertEqual(len(anchored_episodes([T],horizon_days=14)),1)
    def test_reject_unsorted(self):
        with self.assertRaises(ValueError):
            anchored_episodes([T+timedelta(days=1),T],horizon_days=14)
    def test_reject_zero_horizon(self):
        with self.assertRaises(ValueError):
            anchored_episodes([],horizon_days=0)
