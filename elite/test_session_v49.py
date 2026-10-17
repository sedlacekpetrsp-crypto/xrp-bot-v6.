import unittest
from elite.session_v49 import decisions

class SessionTests(unittest.TestCase):
    def rows(self,name,days=1,signal_hour=6):
        rows=[]
        for day in range(days):
            for hour in range(24):
                candle=(100,103,97,100) if hour<6 else (100,100.5,99.5,100)
                if hour in (signal_hour,signal_hour+2):
                    candle=(100,105,99,104) if name=='v49' else (98,99,96.9,98)
                for j in range(12):rows.append(((day*288+hour*12+j)*300000,*candle))
        return rows

    def test_one_signal_per_day_and_reset(self):
        for name in ('v49','v50'):
            s=decisions(self.rows(name,2),name)
            self.assertEqual(list(s),[83,371])
            self.assertEqual(s[83].max_bars,204)
            self.assertGreater(s[83].stop_distance,0)

    def test_no_opening_or_late_entry(self):
        for name in ('v49','v50'):
            self.assertFalse(decisions(self.rows(name,signal_hour=22),name))
            self.assertFalse(decisions(self.rows(name)[:72],name))

    def test_incomplete_initial_day_rejected(self):
        for name in ('v49','v50'):
            self.assertFalse(decisions(self.rows(name)[12:],name))

    def test_prefix_and_no_lookahead_range(self):
        for name in ('v49','v50'):
            rows=self.rows(name,2);full=decisions(rows,name)
            short=decisions(rows[:100],name)
            self.assertEqual(short,{i:d for i,d in full.items() if i<100})
            self.assertTrue(all((i+1)%12==0 for i in full))
            self.assertEqual(decisions(rows[:83],name),{})
