import unittest
from datetime import datetime, timedelta, timezone
from research.event_episode_pit import Event, audit_episodes

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

def e(i, minutes=0, symbol="XRP", published=None, received=None):
    d = T + timedelta(minutes=minutes)
    return Event(str(i), symbol, published or d, received or d, d, "source" + str(i))

class EpisodeGateTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(audit_episodes([])["independent_episodes"], 0)

    def test_same_window_cluster(self):
        r = audit_episodes([e(1), e(2, 1439)])
        self.assertEqual((r["eligible_events"], r["independent_episodes"]), (2, 1))

    def test_outside_window_separate(self):
        self.assertEqual(audit_episodes([e(1), e(2, 1441)])["independent_episodes"], 2)

    def test_transitive_chain(self):
        self.assertEqual(audit_episodes([e(1), e(2, 1000), e(3, 2000)])["independent_episodes"], 1)

    def test_cross_symbol_separate(self):
        self.assertEqual(audit_episodes([e(1), e(2, symbol="BTC")])["independent_episodes"], 2)

    def test_late_publication_excluded(self):
        x = e(1, published=T + timedelta(seconds=1))
        self.assertEqual(audit_episodes([x])["excluded"][0]["reason"], "not_point_in_time")

    def test_late_receipt_excluded(self):
        x = e(1, received=T + timedelta(seconds=1))
        self.assertEqual(audit_episodes([x])["eligible_events"], 0)

    def test_receipt_before_publication(self):
        x = e(1, published=T - timedelta(minutes=1), received=T - timedelta(minutes=2))
        self.assertEqual(audit_episodes([x])["excluded"][0]["reason"], "receipt_before_publication")

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            audit_episodes([e(1), e(1)])

    def test_naive_time_rejected(self):
        x = Event("1", "XRP", datetime(2026, 1, 1), T, T, "s")
        with self.assertRaises(ValueError):
            audit_episodes([x])

    def test_bad_embargo_rejected(self):
        with self.assertRaises(ValueError):
            audit_episodes([e(1)], embargo_minutes=True)

    def test_order_independent(self):
        a, b = e(1), e(2, 3)
        self.assertEqual(audit_episodes([a, b]), audit_episodes([b, a]))

if __name__ == "__main__":
    unittest.main()
