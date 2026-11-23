import unittest
from datetime import datetime, timezone, timedelta
from research.k11_event_independence import audit_independence

T = datetime(2026, 11, 20, tzinfo=timezone.utc)
def e(article="a", asset="XRP", announce=T, observed=T):
    return dict(article_id=article, asset=asset, announced_at=announce, observed_at=observed)

class TestK11Independence(unittest.TestCase):
    def test_distinct_articles(self):
        self.assertTrue(audit_independence([e("a"), e("b")], as_of=T, min_articles=2)["article_gate_ok"])
    def test_same_article_different_assets_counts_once(self):
        x = audit_independence([e("a","XRP"),e("a","DOGE")], as_of=T, min_articles=2)
        self.assertEqual(x["independent_articles"], 1)
    def test_duplicate_casefold(self):
        self.assertEqual(audit_independence([e("A"),e("a")],as_of=T)["rejected_indices"],[1])
    def test_future_observation(self):
        self.assertEqual(audit_independence([e(observed=T+timedelta(seconds=1))],as_of=T)["accepted_indices"],[])
    def test_announcement_after_observation(self):
        self.assertEqual(audit_independence([e(announce=T+timedelta(seconds=1))],as_of=T)["accepted_indices"],[])
    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            audit_independence([e(observed=T.replace(tzinfo=None))],as_of=T)
    def test_missing_identity_rejected(self):
        with self.assertRaises(ValueError):
            audit_independence([e(article="")],as_of=T)
    def test_boolean_threshold_rejected(self):
        with self.assertRaises(ValueError):
            audit_independence([],as_of=T,min_articles=True)

if __name__ == "__main__":
    unittest.main()
