"""Claude review (dialog 0415) of research/event_episode_pit.py @ ba51f79.

Documents behaviour gaps found in review; tests marked expectedFailure describe the
behaviour the docstring/purpose promises but the code does not implement. No data,
no performance, PAPER research only.
"""
import unittest
from datetime import datetime, timedelta, timezone
from research.event_episode_pit import Event, audit_episodes

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def ev(i, symbol, source, minutes=0):
    d = T + timedelta(minutes=minutes)
    return Event(str(i), symbol, d, d, d, source)


class ReviewFindings(unittest.TestCase):
    def test_r1_shared_source_counts_as_many_episodes(self):
        # One delisting article covering 3 symbols (K11-like: 50 events / 24 articles)
        r = audit_episodes([ev(1, "AAA", "art1"), ev(2, "BBB", "art1"), ev(3, "CCC", "art1")])
        self.assertEqual(r["independent_episodes"], 3)  # current behaviour

    @unittest.expectedFailure
    def test_r1_shared_source_should_be_one_information_shock(self):
        r = audit_episodes([ev(1, "AAA", "art1"), ev(2, "BBB", "art1"), ev(3, "CCC", "art1")])
        self.assertEqual(r["independent_episodes"], 1)

    @unittest.expectedFailure
    def test_r2_docstring_promises_fail_closed_on_source_collision(self):
        # Same source_id on two symbols far apart in time = suspicious collision
        with self.assertRaises(ValueError):
            audit_episodes([ev(1, "AAA", "art1"), ev(2, "BBB", "art1", minutes=10 * 1440)])

    def test_r3_clustering_uses_decision_not_publication_time(self):
        # Two publications 3 days apart but decisions within embargo -> merged.
        a = Event("1", "AAA", T - timedelta(days=3), T - timedelta(days=3), T, "s1")
        b = Event("2", "AAA", T, T, T + timedelta(minutes=1), "s2")
        self.assertEqual(audit_episodes([a, b])["independent_episodes"], 1)

    def test_r4_transitive_chain_unbounded(self):
        # Event every 23 h for 30 days collapses into one episode.
        evs = [ev(i, "AAA", f"s{i}", minutes=i * 1380) for i in range(31)]
        self.assertEqual(audit_episodes(evs)["independent_episodes"], 1)


if __name__ == "__main__":
    unittest.main()
