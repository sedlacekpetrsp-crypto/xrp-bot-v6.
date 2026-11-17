import unittest
from research.k9_placebo_audit.placebo_audit import audit_placebo_minutes

H = '2026-11-17T09'
def k(m, asset='XRPUSDT', hour=H): return (asset, hour, m)

class PlaceboAuditTests(unittest.TestCase):
    def test_other_signal_same_hour_is_contamination(self):
        r = audit_placebo_minutes([k(1), k(9)], [k(9), k(12)])
        self.assertEqual((r['verdict'], r['contaminated_draws']), ('INCONCLUSIVE', 1))
    def test_unrelated_asset_is_clean(self):
        self.assertEqual(audit_placebo_minutes([k(9)], [k(9, 'BTCUSDT')])['verdict'], 'PASS')
    def test_unrelated_hour_is_clean(self):
        self.assertEqual(audit_placebo_minutes([k(9)], [k(9, hour='2026-11-17T10')])['verdict'], 'PASS')
    def test_duplicate_draws_fail_closed(self):
        self.assertEqual(audit_placebo_minutes([], [k(2), k(2)])['duplicate_draws'], 1)
    def test_insufficient_support(self):
        self.assertEqual(audit_placebo_minutes([], [k(2)], min_clean_support=2)['verdict'], 'INCONCLUSIVE')
    def test_empty_support(self):
        self.assertEqual(audit_placebo_minutes([], [])['verdict'], 'INCONCLUSIVE')
    def test_invalid_minute(self):
        with self.assertRaises(ValueError): audit_placebo_minutes([], [k(True)])
    def test_invalid_hour(self):
        with self.assertRaises(ValueError): audit_placebo_minutes([], [('XRPUSDT','2026-02-30T09',1)])
    def test_lowercase_asset_rejected_in_signals(self):
        with self.assertRaises(ValueError): audit_placebo_minutes([k(1, 'xrpusdt')], [k(1)])
    def test_whitespace_asset_rejected_in_placebos(self):
        with self.assertRaises(ValueError): audit_placebo_minutes([k(1)], [k(1, ' XRPUSDT')])
    def test_canonical_asset_still_valid(self):
        self.assertEqual(audit_placebo_minutes([k(1)], [k(1)])['contaminated_draws'], 1)
    def test_bad_support(self):
        with self.assertRaises(ValueError): audit_placebo_minutes([], [], min_clean_support=0)

if __name__ == '__main__': unittest.main()
