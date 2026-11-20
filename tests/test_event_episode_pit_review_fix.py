import unittest
from datetime import datetime, timedelta, timezone
from research.event_episode_pit import Event, audit_episodes

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

def event(i, symbol="XRP", minute=0, source=None, published=None):
    t = T + timedelta(minutes=minute)
    return Event(str(i), symbol, published or t, t, t, source or str(i))

class ReviewFixTests(unittest.TestCase):
    def test_shared_article_across_symbols(self):
        r = audit_episodes([event(1, "XRP", source="article"), event(2, "BTC", source="article")])
        self.assertEqual(r["independent_episodes"], 1)
        self.assertEqual(r["per_symbol_episodes"], {"BTC": 1, "XRP": 1})

    def test_source_collision_rejected(self):
        with self.assertRaisesRegex(ValueError, "collision"):
            audit_episodes([event(1, source="same"), event(2, minute=90, source="same")])

    def test_publication_not_decision_drives_window(self):
        a = event(1, minute=0)
        b = event(2, minute=2880, published=T + timedelta(minutes=2000))
        self.assertEqual(audit_episodes([a, b])["independent_episodes"], 2)

    def test_transitive_cross_symbol(self):
        r = audit_episodes([event(1, "XRP", 0, "shared"), event(2, "BTC", 0, "shared"), event(3, "BTC", 1000)])
        self.assertEqual(r["independent_episodes"], 1)
        self.assertEqual(r["max_episode_span_minutes"], 1000)

    def test_order_invariance(self):
        a = [event(1), event(2, minute=2), event(3, "BTC")]
        self.assertEqual(audit_episodes(a), audit_episodes(a[::-1]))
