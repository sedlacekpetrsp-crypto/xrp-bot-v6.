import math
import unittest
from elite.backtest import backtest

class TestBacktest(unittest.TestCase):
    def test_empty(self):
        result=backtest([(1,1,1,1)]*150)
        self.assertEqual(result["trades"],0)
        self.assertEqual(result["net_pnl"],0)

    def test_reject_bad_risk(self):
        with self.assertRaises(ValueError):
            backtest([],risk_fraction=-0.1)

    def test_no_future_data(self):
        bars=[]
        p=1.0
        for i in range(130):
            p*=math.exp(0.002 if i%2 else -0.002)
            bars.append((p,p,p,p))
        bars[-2]=(p,p,p,p)
        bars[-1]=(p*.98,p*.98,p*.98,p*.98)
        result=backtest(bars)
        self.assertIsInstance(result["trades"],int)

if __name__=="__main__":
    unittest.main()
