import datetime as dt
import unittest

from research.pit_manifest_hash_preflight import validate_manifest

NOW = dt.datetime(2026, 11, 22, 12, tzinfo=dt.timezone.utc)
GOOD = {"path": "snapshots/xrp.json", "sha256": "a" * 64, "asof_utc": "2026-11-21T12:00:00Z"}


class ManifestPreflightTests(unittest.TestCase):
    def check_bad(self, records, expected):
        ok, errors = validate_manifest(records, NOW)
        self.assertFalse(ok)
        self.assertTrue(any(expected in e for e in errors), errors)

    def test_valid(self):
        self.assertEqual(validate_manifest([GOOD], NOW), (True, []))

    def test_empty(self):
        self.check_bad([], "empty")

    def test_duplicate(self):
        self.check_bad([GOOD, GOOD.copy()], "duplicate_path")

    def test_traversal(self):
        self.check_bad([{**GOOD, "path": "../secret"}], "invalid_path")

    def test_absolute(self):
        self.check_bad([{**GOOD, "path": "/tmp/a"}], "invalid_path")

    def test_windows_separator(self):
        self.check_bad([{**GOOD, "path": "a\\b"}], "invalid_path")

    def test_bad_hash(self):
        self.check_bad([{**GOOD, "sha256": "A" * 64}], "invalid_sha256")

    def test_future(self):
        self.check_bad([{**GOOD, "asof_utc": "2026-11-23T12:00:00Z"}], "future_evidence")

    def test_timezone_missing(self):
        self.check_bad([{**GOOD, "asof_utc": "2026-11-21T12:00:00"}], "invalid_asof")

    def test_invalid_record(self):
        self.check_bad([None], "invalid_record")

    def test_naive_decision(self):
        self.check_bad([GOOD], "invalid_decision_time")


if __name__ == "__main__":
    unittest.main()
