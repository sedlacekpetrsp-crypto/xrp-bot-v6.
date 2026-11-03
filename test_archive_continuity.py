import unittest
from research.archive_validation.continuity import segments

def row(b,run='a',complete=True):return dict(bucket=b,run_id=run,complete=complete)

class ContinuityTests(unittest.TestCase):
    def test_gap_breaks_even_all_complete(self):
        r=segments([row(3),row(0),row(1)])
        self.assertEqual(r['missing_minutes'],1)
        self.assertEqual(r['longest_segment_samples'],2)
        self.assertEqual(len(r['continuous_segments']),2)
    def test_context_change_splits(self):
        r=segments([row(0),row(1,'b'),row(2,'b')])
        self.assertEqual(r['missing_minutes'],0)
        self.assertEqual([s['samples'] for s in r['continuous_segments']],[1,2])
    def test_incomplete_is_not_forward_filled(self):
        r=segments([row(0),row(1,complete=False),row(2)])
        self.assertEqual(r['incomplete_samples'],1)
        self.assertEqual(r['longest_segment_samples'],1)
    def test_bad_metadata_rejected(self):
        for rows in ([row(0),row(0)],[row(-1)],[row(True)],[row(1,run='')],[row(1,complete='true')]):
            with self.assertRaises(ValueError):segments(rows)
    def test_empty(self):self.assertEqual(segments([])['longest_segment_samples'],0)

if __name__=='__main__':unittest.main()
