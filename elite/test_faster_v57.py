import unittest
from elite.faster_v57 import decisions,frequency_failures


def rows(n):
    return [(300000*k,100+k*.001,101+k*.001,99+k*.001,100+k*.001) for k in range(n)]


class FasterTests(unittest.TestCase):
    def test_signal_clocks_and_time_limits(self):
        r=rows(900)
        for name,count in [('v57',12),('v58',3)]:
            out=decisions(r,name)
            self.assertTrue(out)
            self.assertTrue(all((i+1)%count==0 for i in out))
            self.assertTrue(all(d.max_bars==84*count for d in out.values()))

    def test_incomplete_bars_do_not_leak(self):
        r=rows(900)
        for name in ('v57','v58'):
            full=decisions(r,name)
            for n in (701,713,799):
                self.assertEqual(decisions(r[:n],name),{i:d for i,d in full.items() if i<n})

    def test_frequency_boundary_per_period(self):
        p={'a':{'base':{'trades':26}},'b':{'base':{'trades':25}}}
        self.assertEqual(frequency_failures(p,{'a':182,'b':182}),['below_one_trade_per_week_b'])
        self.assertEqual(frequency_failures({'a':{'base':{'trades':26}}},{'a':184}),['below_one_trade_per_week_a'])

    def test_unknown_name_rejected(self):
        with self.assertRaises(ValueError):decisions(rows(900),'v59')
