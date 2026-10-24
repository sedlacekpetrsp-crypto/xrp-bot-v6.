import unittest
from research.autocorr_regime_v1 import Config,validate,pearson_lag_one,backtest

class RegimeTests(unittest.TestCase):
    def test_positive_serial_correlation(self):
        self.assertGreater(pearson_lag_one([1,2,3,4,5,6]),.9)
    def test_negative_serial_correlation(self):
        self.assertLess(pearson_lag_one([1,-1,1,-1,1,-1]),-.9)
    def test_missing_bar_rejected(self):
        b=[dict(timestamp=t,open=1.,high=1.1,low=.9,close=1.) for t in (0,1800000)]
        with self.assertRaises(ValueError): validate(b)
    def test_no_future_and_no_trade_flat(self):
        bars=[dict(timestamp=i*900000,open=1.,high=1.01,low=.99,close=1.) for i in range(130)]
        self.assertEqual(backtest(bars),[])
    def test_invalid_candle(self):
        with self.assertRaises(ValueError): validate([dict(open=1.,high=.9,low=.8,close=1.)])

if __name__=="__main__": unittest.main()
