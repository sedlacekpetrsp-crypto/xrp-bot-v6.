import unittest
from research.top_risk_radar_v1.source_manifest import validate_manifest

GOOD=dict(source_id="xrp-spot-1",provider="example",market_type="spot",venue="example",symbol="XRPUSDT",timezone="UTC",start_utc="2025-01-01T00:00:00Z",end_utc="2025-02-01T00:00:00Z",event_timestamp_field="trade_time",granularity="trade",acquisition_utc="2025-02-02T00:00:00Z",raw_sha256="a"*64,row_count=100,point_in_time_supported=True,qa_status="pending")

class ManifestTests(unittest.TestCase):
    def test_valid_metadata(self):
        self.assertEqual(validate_manifest(GOOD),[])
    def test_missing_required(self):
        self.assertIn("missing:provider",validate_manifest({**GOOD,"provider":""}))
    def test_bad_hash(self):
        self.assertIn("invalid_sha256",validate_manifest({**GOOD,"raw_sha256":"not-a-hash"}))
    def test_bad_range(self):
        self.assertIn("invalid_coverage_range",validate_manifest({**GOOD,"start_utc":GOOD["end_utc"]}))
    def test_non_utc(self):
        self.assertIn("non_utc:start_utc",validate_manifest({**GOOD,"start_utc":"2025-01-01T00:00:00+01:00"}))
    def test_pit_type(self):
        self.assertIn("invalid_pit_flag",validate_manifest({**GOOD,"point_in_time_supported":"yes"}))
    def test_zero_rows(self):
        self.assertIn("invalid_row_count",validate_manifest({**GOOD,"row_count":0}))

    def test_naive_timestamp_is_not_utc(self):
        for field in ("start_utc", "end_utc", "acquisition_utc"):
            with self.subTest(field=field):
                manifest = {**GOOD, field: "2025-01-01T00:00:00"}
                self.assertIn("non_utc:" + field, validate_manifest(manifest))

    def test_acquisition_cannot_precede_covered_trades(self):
        manifest = {**GOOD, "acquisition_utc": "2025-01-31T23:59:59Z"}
        self.assertIn("acquisition_before_coverage_end", validate_manifest(manifest))

    def test_acquisition_at_end_is_acceptable(self):
        manifest = {**GOOD, "acquisition_utc": GOOD["end_utc"]}
        self.assertNotIn("acquisition_before_coverage_end", validate_manifest(manifest))

    def test_naive_start_does_not_crash_range_comparison(self):
        manifest = {**GOOD, "start_utc": "2025-01-01T00:00:00"}
        self.assertIn("non_utc:start_utc", validate_manifest(manifest))

    def test_naive_end_does_not_crash_range_comparison(self):
        manifest = {**GOOD, "end_utc": "2025-02-01T00:00:00"}
        self.assertIn("non_utc:end_utc", validate_manifest(manifest))

    def test_naive_acquisition_does_not_crash_range_comparison(self):
        manifest = {**GOOD, "acquisition_utc": "2025-02-02T00:00:00"}
        self.assertIn("non_utc:acquisition_utc", validate_manifest(manifest))

    def test_whitespace_only_required_metadata_fails_closed(self):
        for field in ("source_id", "provider", "venue", "symbol", "event_timestamp_field", "granularity", "qa_status"):
            with self.subTest(field=field):
                manifest = {**GOOD, field: " \t "}
                self.assertIn("missing:" + field, validate_manifest(manifest))

    def test_whitespace_only_hash_does_not_bypass_required_field(self):
        manifest = {**GOOD, "raw_sha256": " " * 64}
        self.assertIn("missing:raw_sha256", validate_manifest(manifest))
