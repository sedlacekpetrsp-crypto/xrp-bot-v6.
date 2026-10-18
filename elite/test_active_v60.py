import math,unittest
from elite.active_v60 import entry,decisions,activity_failures
from elite.faster_v57 import decisions as baseline


def rows(n):
    prices=[100+.0005*k+2*math.sin(k/40) for k in range(n)]
    return [(k*300000,c,c+1,c-1,c) for k,c in enumerate(prices)]


class ActiveTests(unittest.TestCase):
    def test_cross_and_short_slope_required(self):
        self.assertTrue(entry([100]*6+[99,102],[99]*6+[100,101],7))
        self.assertFalse(entry([100]*6+[102,102],[99]*6+[100,101],7))
        self.assertFalse(entry([100]*6+[99,102],[102]*6+[100,101],7))

    def test_existing_entries_and_exit_time_preserved(self):
        r=rows(6000);a=decisions(r);b=baseline(r,'v57')
        self.assertEqual(a.keys(),b.keys())
        for i in a:
            if b[i].stop_distance:self.assertEqual(a[i].stop_distance,b[i].stop_distance)
            self.assertEqual((a[i].exit,a[i].target_distance,a[i].max_bars),(b[i].exit,b[i].target_distance,b[i].max_bars))

    def test_prefix(self):
        r=rows(3000);full=decisions(r)
        for n in (1301,1999,2905):
            self.assertEqual(decisions(r[:n]),{i:d for i,d in full.items() if i<n})

    def test_three_weekly_boundary(self):
        p={'a':{'base':{'trades':78}},'b':{'base':{'trades':77}}}
        self.assertEqual(activity_failures(p,{'a':182,'b':182}),['below_three_trades_per_week_b'])
