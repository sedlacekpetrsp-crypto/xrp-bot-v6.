import unittest
from research.k11_eligibility_census import audit_events


def event(i=1, **changes):
    row = dict(event_id=f"e{i}", article_id=f"a{i}",
               announcement_at="2025-01-01T00:00:00Z",
               capture_at="2025-01-01T00:01:00Z",
               decision_at="2025-01-01T01:00:00Z",
               perp_tradable=True, coverage_fraction=0.96)
    row.update(changes)
    return row


class CensusTests(unittest.TestCase):
    def test_empty_no_go(self):
        self.assertEqual(audit_events([])["verdict"], "DATA_NO_GO")

    def test_all_thresholds(self):
        result = audit_events([event(i) for i in range(60)])
        self.assertEqual(result["verdict"], "DATA_GO_PRELIMINARY")

    def test_mirrored_articles_do_not_inflate_independence(self):
        result = audit_events([event(i, article_id="same") for i in range(60)])
        self.assertFalse(result["checks"]["independent_articles"])

    def test_capture_at_decision_is_unverified(self):
        result = audit_events([event(capture_at="2025-01-01T01:00:00Z")])
        self.assertEqual(result["pit_unverified"], 1)

    def test_no_timezone_rejected(self):
        with self.assertRaises(ValueError):
            audit_events([event(capture_at="2025-01-01T00:01:00")])

    def test_duplicate_event_rejected(self):
        with self.assertRaises(ValueError):
            audit_events([event(), event()])

    def test_bool_coverage_rejected(self):
        with self.assertRaises(ValueError):
            audit_events([event(coverage_fraction=True)])

    def test_nan_coverage_rejected(self):
        with self.assertRaises(ValueError):
            audit_events([event(coverage_fraction=float("nan"))])

    def test_unverified_denominator(self):
        rows = [event(i) for i in range(7)] + [event(i, capture_at=None) for i in range(7, 11)]
        self.assertEqual(audit_events(rows)["pit_unverified_fraction"], 0.4)

    def test_unknown_price_field_rejected(self):
        with self.assertRaises(ValueError):
            audit_events([event(price=2.0)])


if __name__ == "__main__":
    unittest.main()
