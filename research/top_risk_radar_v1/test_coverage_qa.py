import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from research.top_risk_radar_v1.label_events import Trade
from research.top_risk_radar_v1.coverage_qa import audit_coverage

T = datetime(2025,1,1,0,5,tzinfo=timezone.utc)
def make(seconds):
    return Trade(T+timedelta(seconds=seconds),Decimal("1"))

class CoverageTests(unittest.TestCase):
    def test_missing_endpoint_rejected(self):
        r=audit_coverage(T,[make(1),make(60)],T+timedelta(days=15))
        self.assertFalse(r.acceptable)
        self.assertFalse(r.window_end_covered)
    def test_missing_reference_rejected(self):
        r=audit_coverage(T,[make(120),make(14*86400)],T+timedelta(days=15))
        self.assertFalse(r.reference_covered)
    def test_large_gap_rejected(self):
        r=audit_coverage(T,[make(1),make(3600),make(14*86400)],T+timedelta(days=15))
        self.assertFalse(r.acceptable)
    def test_duplicate_timestamps_rejected(self):
        r=audit_coverage(T,[make(1),make(1),make(14*86400)],T+timedelta(days=15))
        self.assertEqual(r.duplicate_timestamps,1)
        self.assertFalse(r.acceptable)
    def test_complete_synthetic_minute_grid_heuristic_only(self):
        rows=[make(i*60+1) for i in range(14*24*60)]
        r=audit_coverage(T,rows,T+timedelta(days=15))
        self.assertTrue(r.acceptable)
        self.assertEqual(r.reason,"heuristic_pass_requires_independent_source_qa")
    def test_unmatured_window_rejected(self):
        rows=[make(i*60+1) for i in range(14*24*60)]
        r=audit_coverage(T,rows,T+timedelta(days=13))
        self.assertFalse(r.acceptable)
