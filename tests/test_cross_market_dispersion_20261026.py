import unittest
from research.cross_market_dispersion_20261026.strategy import ASSETS,validate,backtest,percentile,Config

def markets(n=24*190):
    return {a:[dict(timestamp=i*3600000,open=100.,high=101.,low=99.,close=100.) for i in range(n)] for a in ASSETS}

class Tests(unittest.TestCase):
    def test_percentile(self): self.assertEqual(percentile([1,2,3,4,5],.5),3)
    def test_no_signal_flat(self): self.assertEqual(backtest(markets()),[])
    def test_gap_rejected(self):
        m=markets(100);m["BTCUSDT"][2]["timestamp"]+=1
        with self.assertRaises(ValueError):validate(m)
    def test_misalignment_rejected(self):
        m=markets(100)
        for row in m["BTCUSDT"]:row["timestamp"]+=3600000
        with self.assertRaises(ValueError):validate(m)
    def test_bad_ohlc_rejected(self):
        m=markets(100);m["XRPUSDT"][0]["low"]=102
        with self.assertRaises(ValueError):validate(m)
    def test_cost_stress_flat(self):self.assertEqual(backtest(markets(),Config(),True),[])

if __name__=="__main__":unittest.main()
