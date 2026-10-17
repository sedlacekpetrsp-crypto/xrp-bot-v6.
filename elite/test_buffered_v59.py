import unittest
from elite.buffered_v59 import exit_condition,decisions
from elite.faster_v57 import decisions as baseline


def rows(n):return [(300000*k,100+k*.001,101+k*.001,99+k*.001,100+k*.001) for k in range(n)]


class BufferedTests(unittest.TestCase):
    def test_small_dips_do_not_exit(self):
        self.assertFalse(exit_condition([99.5,99.4],[100,100],[1,1],1))

    def test_two_separate_closed_bar_thresholds(self):
        self.assertTrue(exit_condition([98,96],[100,100],[1,3],1))
        self.assertFalse(exit_condition([98,97],[100,100],[1,3],1))
        self.assertFalse(exit_condition([99.5,96],[100,100],[1,3],1))

    def test_entry_stop_target_time_unchanged(self):
        r=rows(1800);a=decisions(r);b=baseline(r,'v57')
        self.assertEqual(a.keys(),b.keys())
        for i in a:
            self.assertEqual((a[i].stop_distance,a[i].target_distance,a[i].max_bars),
                             (b[i].stop_distance,b[i].target_distance,b[i].max_bars))
            if a[i].exit:self.assertTrue(b[i].exit)

    def test_incomplete_hour_and_prefix(self):
        r=rows(1800);full=decisions(r)
        for n in (701,1211,1799):
            self.assertEqual(decisions(r[:n]),{i:d for i,d in full.items() if i<n})
