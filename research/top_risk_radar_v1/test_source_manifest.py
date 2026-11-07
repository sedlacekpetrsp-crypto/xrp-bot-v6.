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
