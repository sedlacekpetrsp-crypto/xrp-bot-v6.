import unittest
from datetime import datetime,timedelta,timezone
from research.top_risk_radar_v1.episodes import group_positive_episodes
T=datetime(2024,1,1,tzinfo=timezone.utc)
def days(*ds): return [T+timedelta(days=d) for d in ds]
class EpisodeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(group_positive_episodes([],[]),[])
    def test_overlapping(self):
        r=group_positive_episodes(days(0,1,2),[True,True,True])
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["positive_decisions"],3)
    def test_separated(self):
        r=group_positive_episodes(days(0,1,40),[True,False,True])
        self.assertEqual(len(r),2)
    def test_negative_gap_ignored(self):
        r=group_positive_episodes(days(0,1,2),[True,False,True])
        self.assertEqual(len(r),1)
    def test_bad_lengths(self):
        with self.assertRaises(ValueError):
            group_positive_episodes(days(0),[])
    def test_bad_order(self):
        with self.assertRaises(ValueError):
            group_positive_episodes(days(1,0),[True,True])
