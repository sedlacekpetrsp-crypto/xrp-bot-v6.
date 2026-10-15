import unittest
from elite.daily_v40 import decisions, signal

class DailyTests(unittest.TestCase):
    def test_breakout_excludes_current_high(self):
        bars=[(i,100,101,99,100) for i in range(61)]
        bars[-1]=(60,100,110,99,105)
        self.assertGreater(signal(bars,60,'v40').stop_distance,0)
        bars[-1]=(60,100,110,99,101)
        self.assertEqual(signal(bars,60,'v40').stop_distance,0)

    def test_exit_prior_channel(self):
        bars=[(i,100,101,99,100) for i in range(61)]
        bars[-1]=(60,100,101,90,98)
        self.assertTrue(signal(bars,60,'v40').exit)

    def test_pullback_recovery_and_expiry(self):
        bars=[(i,100+i,101+i,99+i,100+i) for i in range(64)]
        bars[61]=(61,160,161,158,159)
        bars[62]=(62,159,160,157,158)
        bars[63]=(63,158,163,157,162)
        d=signal(bars,63,'v41')
        self.assertGreater(d.stop_distance,0)
        self.assertEqual(d.target_distance,2*d.stop_distance)
        self.assertEqual(d.max_bars,5760)
        bars[62]=(62,159,160,157,159)
        self.assertEqual(signal(bars,63,'v41').stop_distance,0)

    def test_causality_and_incomplete_day(self):
        rows=[(i*300000,100,101,99,100) for i in range(63*288+17)]
        for name in ('v40','v41'):
            full=decisions(rows,name)
            prefix=decisions(rows[:62*288+10],name)
            self.assertEqual(prefix,{i:d for i,d in full.items() if i<62*288+10})
            self.assertTrue(all((i+1)%288==0 for i in full))
            self.assertEqual(len(full),3)
