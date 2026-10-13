import unittest
from elite.v3_candidate import multi_horizon_momentum

class V3Tests(unittest.TestCase):
    def test_flat_prices(self):
        p=[100.0]*110
        self.assertIsNone(multi_horizon_momentum(p,p,p))
    def test_insufficient_bars(self):
        p=[100.0]*20
        self.assertIsNone(multi_horizon_momentum(p,p,p))
    def test_positive_momentum(self):
        p=[100+i*.03 for i in range(110)]
        s=multi_horizon_momentum([x+.1 for x in p],[x-.1 for x in p],p)
        self.assertIsNotNone(s)
        self.assertEqual(s.side,'LONG')
    def test_negative_momentum(self):
        p=[110-i*.03 for i in range(110)]
        self.assertIsNone(multi_horizon_momentum([x+.1 for x in p],[x-.1 for x in p],p))
if __name__=='__main__':unittest.main()
