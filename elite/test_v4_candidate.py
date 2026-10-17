import unittest
from elite.v4_candidate import slow_trend
class Tests(unittest.TestCase):
    def test_flat(self):
        p=[100.0]*110
        self.assertIsNone(slow_trend(p,p,p))
    def test_too_short(self):
        p=[100.0]*50
        self.assertIsNone(slow_trend(p,p,p))
    def test_bad_high_low(self):
        p=[100.0]*110
        self.assertIsNone(slow_trend([x-1 for x in p],p,p))
    def test_crossover(self):
        p=[100.0]*100+[110.0]
        s=slow_trend([x+.1 for x in p],[x-.1 for x in p],p,min_gap=.001)
        self.assertIsNotNone(s)
        self.assertEqual(s.side,'LONG')
if __name__=='__main__':unittest.main()
