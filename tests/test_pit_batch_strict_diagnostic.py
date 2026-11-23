import unittest
from datetime import datetime, timedelta, timezone
from research.pit_batch_strict_diagnostic import audit_batch

T = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)

def event(key, seen, published=None):
    return {"event_id": key, "published_at": published or seen, "first_seen_at": seen}

class PitBatchStrictTests(unittest.TestCase):
    def test_valid_event(self):
        ok, bad = audit_batch([event("a", T-timedelta(seconds=2))], T)
        self.assertEqual(len(ok), 1)
        self.assertFalse(bad)

    def test_equal_decision_is_not_eligible(self):
        ok, bad = audit_batch([event("a", T)], T)
        self.assertFalse(ok)
        self.assertEqual(bad[0][1], "not_yet_available")

    def test_future_row_does_not_suppress_valid_row(self):
        ok, bad = audit_batch([event("a", T-timedelta(minutes=2)), event("b", T+timedelta(minutes=1))], T)
        self.assertEqual([x["event_id"] for x in ok], ["a"])
        self.assertEqual(bad[0][1], "not_yet_available")

    def test_duplicate_both_quarantined(self):
        ok, bad = audit_batch([event("a", T-timedelta(minutes=2))]*2, T)
        self.assertFalse(ok)
        self.assertEqual([reason for _,reason in bad], ["duplicate_identity"]*2)

    def test_publication_after_observation(self):
        ok, bad = audit_batch([event("a", T-timedelta(minutes=2), T-timedelta(minutes=1))], T)
        self.assertFalse(ok)
        self.assertEqual(bad[0][1], "impossible_provenance")

    def test_naive_timestamp(self):
        ok, bad = audit_batch([event("a", datetime(2026,11,23,11))], T)
        self.assertFalse(ok)
        self.assertEqual(bad[0][1], "invalid_timestamp")

    def test_latency_strict_boundary(self):
        ok, bad = audit_batch([event("a", T-timedelta(seconds=5))], T, 5)
        self.assertFalse(ok)
        self.assertEqual(bad[0][1], "not_yet_available")

    def test_invalid_latency(self):
        for latency in (-1, float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                audit_batch([], T, latency)

if __name__ == "__main__":
    unittest.main()
