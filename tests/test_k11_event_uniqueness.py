import unittest
from research.k11_event_uniqueness import audit_event_uniqueness


def item(**changes):
    x = dict(cms_id="101", asset="ABC", source_url="https://example.org/a?utm=x",
             published_at="2026-01-01T10:00:00Z",
             effective_at="2026-01-02T10:00:00Z")
    x.update(changes)
    return x


class EventUniquenessTests(unittest.TestCase):
    def test_unique(self):
        self.assertEqual(audit_event_uniqueness([item()])["unique_events"], 1)

    def test_same_cms_id(self):
        self.assertEqual(audit_event_uniqueness([item(), item(asset="DEF", source_url="https://example.org/b")])["unique_events"], 1)

    def test_same_event_different_article(self):
        self.assertEqual(audit_event_uniqueness([item(), item(cms_id="102", source_url="https://example.org/b")])["unique_events"], 1)

    def test_query_tracking_not_distinct(self):
        self.assertEqual(audit_event_uniqueness([item(), item(cms_id="102", asset="DEF", source_url="https://example.org/a?utm=y")])["unique_events"], 1)

    def test_naive_time_rejected(self):
        self.assertEqual(audit_event_uniqueness([item(published_at="2026-01-01T10:00:00")])["unique_events"], 0)

    def test_publication_after_effective(self):
        self.assertEqual(audit_event_uniqueness([item(published_at="2026-01-03T10:00:00Z")])["unique_events"], 0)

    def test_non_https_rejected(self):
        self.assertEqual(audit_event_uniqueness([item(source_url="http://example.org/a")])["unique_events"], 0)

    def test_timezone_equivalent_event(self):
        self.assertEqual(audit_event_uniqueness([item(), item(cms_id="102", source_url="https://example.org/b", effective_at="2026-01-02T11:00:00+01:00")])["unique_events"], 1)

    def test_invalid_record(self):
        self.assertEqual(audit_event_uniqueness([None])["unique_events"], 0)

    def test_distinct_event(self):
        self.assertEqual(audit_event_uniqueness([item(), item(cms_id="102", asset="DEF", source_url="https://example.org/b")])["unique_events"], 2)


if __name__ == "__main__":
    unittest.main()
