import unittest
from tools.data_preflight.calendar_audit import audit_timestamps, canonical_json


class CalendarAuditTests(unittest.TestCase):
    def audit(self, rows, **kwargs):
        params = dict(unit="ms", start_ms=0, end_ms=180000, interval_ms=60000)
        params.update(kwargs)
        return audit_timestamps(rows, **params)

    def test_complete_grid(self):
        self.assertEqual(self.audit([0, 60000, 120000])["status"], "PASS")

    def test_leading_and_trailing_gaps(self):
        self.assertEqual(self.audit([60000])["counts"]["missing_bars"], 2)

    def test_empty_is_failure(self):
        self.assertEqual(self.audit([])["status"], "FAIL")

    def test_duplicate_cannot_hide_gap(self):
        r = self.audit([0, 60000, 60000])
        self.assertEqual(r["counts"]["missing_bars"], 1)
        self.assertIn("DUPLICATE_TIMESTAMP", r["reason_codes"])

    def test_unsorted_not_silently_repaired(self):
        r = self.audit([60000, 0, 120000])
        self.assertEqual(r["counts"]["missing_bars"], 0)
        self.assertEqual(r["status"], "FAIL")

    def test_half_open_end(self):
        self.assertEqual(self.audit([0, 60000, 180000])["counts"]["outside_rows"], 1)

    def test_explicit_microseconds(self):
        self.assertEqual(self.audit([0, 60000000, 120000000], unit="us")["status"], "PASS")

    def test_submillisecond_not_truncated(self):
        self.assertIn("OFF_GRID_TIMESTAMP", self.audit([0, 60000001, 120000000], unit="us")["reason_codes"])

    def test_unknown_unit_blocks_pass(self):
        self.assertEqual(self.audit([0, 60000, 120000], unit="auto")["status"], "UNKNOWN")

    def test_bad_values_rejected(self):
        for value in [True, 0.0, "0", None, float("nan")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.audit([value])

    def test_bad_calendar_rejected(self):
        for kwargs in [dict(interval_ms=0), dict(end_ms=0), dict(end_ms=180001), dict(start_ms=True)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.audit([], **kwargs)

    def test_utc_midnight_crossing(self):
        self.assertEqual(self.audit([86340000, 86400000], start_ms=86340000,
                                    end_ms=86460000)["status"], "PASS")

    def test_delisting_does_not_trim_calendar(self):
        self.assertEqual(self.audit([0])["counts"]["missing_bars"], 2)

    def test_determinism_order_and_calendar_fingerprints(self):
        rows = [0, 60000, 120000]
        before = rows.copy()
        a = self.audit(rows)
        self.assertEqual(canonical_json(a), canonical_json(self.audit(rows)))
        self.assertEqual(rows, before)
        self.assertNotEqual(a["input_sha256"], self.audit(rows[::-1])["input_sha256"])
        self.assertNotEqual(a["input_sha256"], self.audit(rows, end_ms=240000)["input_sha256"])

    def test_large_calendar_does_not_allocate_expected_grid(self):
        r = self.audit([], end_ms=60000*10**12)
        self.assertEqual(r["counts"]["missing_bars"], 10**12)


if __name__ == "__main__":
    unittest.main()
