import unittest
from datetime import datetime, timedelta, timezone
from research.pit_availability_gate import PITError, eligible, audit

T = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)


def row(event=T-timedelta(hours=2), known=T-timedelta(minutes=1), provenance="archive-sha256", kind="outcome"):
    return {"event_at": event, "known_at": known, "provenance": provenance, "kind": kind}


class PITAvailabilityGateTests(unittest.TestCase):
    def test_available(self):
        self.assertTrue(eligible(row(), T))

    def test_future_publication_is_unavailable(self):
        self.assertFalse(eligible(row(known=T+timedelta(seconds=1)), T))

    def test_future_event_is_unavailable(self):
        self.assertFalse(eligible(row(event=T+timedelta(hours=1), known=T+timedelta(hours=1)), T))

    def test_exact_boundary(self):
        self.assertTrue(eligible(row(event=T, known=T), T))

    def test_publication_before_event_rejected(self):
        with self.assertRaises(PITError):
            eligible(row(known=T-timedelta(hours=3)), T)

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(PITError):
            eligible(row(known=T.replace(tzinfo=None)), T)

    def test_non_utc_timezone_rejected(self):
        offset = timezone(timedelta(hours=1))
        with self.assertRaises(PITError):
            eligible(row(known=(T-timedelta(minutes=1)).astimezone(offset)), T)

    def test_missing_provenance_rejected(self):
        with self.assertRaises(PITError):
            eligible(row(provenance=""), T)

    def test_missing_timestamp_rejected(self):
        with self.assertRaises(PITError):
            eligible({"event_at": T, "provenance": "x"}, T)

    def test_required_fields_cannot_disable_pit_checks(self):
        with self.assertRaisesRegex(PITError, "missing known_at"):
            eligible({"event_at": T, "provenance": "x"}, T, required_fields=())

    def test_extra_required_field(self):
        with self.assertRaisesRegex(PITError, "missing source_id"):
            eligible(row(), T, required_fields=("source_id",))

    def test_empty_audit_rejects_naive_decision_time(self):
        with self.assertRaises(PITError):
            audit([], T.replace(tzinfo=None))

    def test_empty_audit_rejects_non_utc_decision_time(self):
        with self.assertRaises(PITError):
            audit([], T.astimezone(timezone(timedelta(hours=2))))

    def test_future_announcement_known_now_is_eligible(self):
        self.assertTrue(eligible(row(event=T+timedelta(days=2),
                                     known=T-timedelta(hours=1),
                                     kind="announcement"), T))

    def test_future_announcement_not_yet_known(self):
        self.assertFalse(eligible(row(event=T+timedelta(days=2),
                                      known=T+timedelta(seconds=1),
                                      kind="announcement"), T))

    def test_outcome_cannot_be_known_before_event(self):
        with self.assertRaises(PITError):
            eligible(row(event=T+timedelta(hours=1),
                         known=T-timedelta(hours=1), kind="outcome"), T)

    def test_kind_missing_or_unknown_fails_closed(self):
        for kind in (None, "", "forecast", True):
            with self.subTest(kind=kind):
                with self.assertRaises(PITError):
                    eligible(row(kind=kind), T)

    def test_announcement_at_boundary(self):
        self.assertTrue(eligible(row(event=T+timedelta(days=1),
                                     known=T, kind="announcement"), T))

    def test_aggregate(self):
        self.assertEqual(audit([row(), row(known=T+timedelta(minutes=1))], T),
                         {"eligible": 1, "unavailable": 1})


if __name__ == "__main__":
    unittest.main()
