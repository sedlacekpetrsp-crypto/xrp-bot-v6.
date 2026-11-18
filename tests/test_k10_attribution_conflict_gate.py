import unittest
from datetime import datetime, timezone, timedelta
from research.k10_attribution_conflict_gate import Evidence, validate_attribution

T = datetime(2024, 1, 2, tzinfo=timezone.utc)
def e(exchange="A", source="one", published=None, captured=None):
    return Evidence("rTEST", exchange, source, published or T, captured or T)

class ConflictGateTests(unittest.TestCase):
    def test_two_publishers(self):
        self.assertEqual(validate_attribution([e(), e(source="two")], T), {"rTEST": "A"})
    def test_one_publisher_two_snapshots_not_independent(self):
        self.assertEqual(validate_attribution([e(), e(captured=T+timedelta(minutes=1))], T+timedelta(minutes=2)), {})
    def test_conflict_fails_closed(self):
        with self.assertRaises(ValueError):
            validate_attribution([e(), e(exchange="B", source="two")], T)
    def test_future_capture(self):
        with self.assertRaises(ValueError):
            validate_attribution([e(captured=T+timedelta(seconds=1))], T)
    def test_future_publication(self):
        with self.assertRaises(ValueError):
            validate_attribution([e(published=T+timedelta(seconds=1))], T)
    def test_naive_datetime(self):
        with self.assertRaises(ValueError):
            validate_attribution([e()], T.replace(tzinfo=None))
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate_attribution([e(), e()], T)
    def test_one_source_not_enough(self):
        self.assertEqual(validate_attribution([e()], T), {})
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            validate_attribution([e()], T, min_sources=1)

if __name__ == "__main__":
    unittest.main()
