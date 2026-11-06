import unittest
from tools.data_preflight.aggregate import aggregate
from tools.data_preflight.calendar_audit import audit_timestamps

H = 3_600_000
REQ = ["calendar", "listing_provenance", "archive_conflicts"]


def cal_pass():
    return audit_timestamps([0, H, 2 * H], unit="ms", start_ms=0, end_ms=3 * H, interval_ms=H)


class AggregateTests(unittest.TestCase):
    def test_calendar_pass_but_provenance_missing_is_unknown(self):
        r = aggregate({"calendar": cal_pass()}, required=REQ)
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual(r["components"]["listing_provenance"]["reason_codes"], ["COMPONENT_MISSING"])

    def test_unresolved_archive_conflict_blocks(self):
        r = aggregate({"calendar": cal_pass(),
                       "listing_provenance": {"status": "PASS", "reason_codes": []},
                       "archive_conflicts": {"status": "UNKNOWN", "reason_codes": ["CONFLICT_UNRESOLVED"]}},
                      required=REQ)
        self.assertEqual(r["status"], "UNKNOWN")

    def test_fail_dominates_unknown(self):
        r = aggregate({"calendar": {"status": "FAIL", "reason_codes": ["MISSING_BARS"]}}, required=REQ)
        self.assertEqual(r["status"], "FAIL")

    def test_all_pass(self):
        ok = {"status": "PASS", "reason_codes": []}
        r = aggregate({"calendar": cal_pass(), "listing_provenance": ok, "archive_conflicts": ok}, required=REQ)
        self.assertEqual(r["status"], "PASS")

    def test_lowercase_or_garbage_status_not_pass(self):
        for bad in [{"status": "pass"}, {"status": True}, None, "PASS", {}]:
            with self.subTest(bad=bad):
                r = aggregate({"calendar": bad}, required=["calendar"])
                self.assertEqual(r["status"], "UNKNOWN")

    def test_pass_with_reason_codes_is_not_pass(self):
        r = aggregate({"calendar": {"status": "PASS", "reason_codes": ["X"]}}, required=["calendar"])
        self.assertEqual(r["status"], "UNKNOWN")

    def test_extra_failing_component_still_counts(self):
        r = aggregate({"calendar": cal_pass(), "extra": {"status": "FAIL", "reason_codes": ["E"]}},
                      required=["calendar"])
        self.assertEqual(r["status"], "FAIL")

    def test_bad_required(self):
        for req in [[], ["a", "a"]]:
            with self.subTest(req=req), self.assertRaises(ValueError):
                aggregate({}, required=req)

    def test_deterministic(self):
        a = aggregate({"calendar": cal_pass()}, required=REQ)
        self.assertEqual(a, aggregate({"calendar": cal_pass()}, required=list(reversed(REQ))))


class CalendarAdversarialTests(unittest.TestCase):
    """Cases not covered by the 15 tests in 5a5073f."""

    def test_local_time_shift_one_bar_on_hourly_fails(self):
        # Stream shifted by +1h (e.g. CET export) stays on the hourly grid; must still FAIL.
        r = audit_timestamps([H, 2 * H, 3 * H], unit="ms", start_ms=0, end_ms=3 * H, interval_ms=H)
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(set(r["reason_codes"]), {"OUTSIDE_CALENDAR", "MISSING_BARS"})

    def test_seconds_declared_as_ms_fails(self):
        r = audit_timestamps([0, 3600, 7200], unit="ms", start_ms=0, end_ms=3 * H, interval_ms=H)
        self.assertEqual(r["status"], "FAIL")

    def test_us_data_declared_as_ms_fails(self):
        # Binance Vision spot switched to microseconds in 2025; mislabel must not pass.
        r = audit_timestamps([0, H * 1000, 2 * H * 1000], unit="ms", start_ms=0, end_ms=3 * H, interval_ms=H)
        self.assertEqual(r["status"], "FAIL")

    def test_numpy_like_int_subclass_rejected(self):
        # Integrator footgun: pandas/numpy ints are not `int`; must be converted explicitly, not silently pass.
        class NpInt(int):
            pass
        with self.assertRaises(ValueError):
            audit_timestamps([NpInt(0)], unit="ms", start_ms=0, end_ms=H, interval_ms=H)


if __name__ == "__main__":
    unittest.main()
