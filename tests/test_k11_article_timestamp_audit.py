"""Synthetic-only checks for K11 announcement cluster timestamps."""
import unittest
from research.k11_article_timestamp_audit import audit_article_timestamps


def e(article="a", time="2026-01-01T12:00:00Z"):
    return {"article_id": article, "announced_at": time}


class ClusterTimestampTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(audit_article_timestamps([])["articles"], 0)

    def test_same_article_same_instant(self):
        self.assertEqual(audit_article_timestamps([e(), e(time="2026-01-01T13:00:00+01:00")])["articles"], 1)

    def test_distinct_articles_can_differ(self):
        self.assertEqual(audit_article_timestamps([e(), e("b", "2026-01-02T12:00:00Z")])["articles"], 2)

    def test_same_article_conflicting_time(self):
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            audit_article_timestamps([e(), e(time="2026-01-01T12:01:00Z")])

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            audit_article_timestamps([e(time="2026-01-01T12:00:00")])

    def test_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            audit_article_timestamps([e(time="not-a-date")])

    def test_missing_article_rejected(self):
        with self.assertRaises(ValueError):
            audit_article_timestamps([{"announced_at": "2026-01-01T12:00:00Z"}])

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            audit_article_timestamps([None])


if __name__ == "__main__":
    unittest.main()
