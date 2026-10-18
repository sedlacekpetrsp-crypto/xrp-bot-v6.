import math
import unittest
from elite.strategy import signal_from_closed_bars

class TestEliteSignal(unittest.TestCase):
    def test_insufficient_data(self):
        self.assertIsNone(signal_from_closed_bars([1]*20,[1]*20,[1]*20))

    def test_constant_prices(self):
        prices=[1.0]*120
        self.assertIsNone(signal_from_closed_bars(prices,prices,prices))

    def test_extreme_down_move_long(self):
        # Oscillating returns create a ranging baseline with nonzero volatility.
        prices=[1.0]
        for i in range(110):
            prices.append(prices[-1]*math.exp(0.002 if i%2 else -0.002))
        prices.append(prices[-1]*math.exp(-0.018))
        result=signal_from_closed_bars(prices,prices,prices)
        self.assertIsNotNone(result)
        self.assertEqual(result.side,"LONG")

    def test_extreme_up_move_short(self):
        prices=[1.0]
        for i in range(110):
            prices.append(prices[-1]*math.exp(0.002 if i%2 else -0.002))
        prices.append(prices[-1]*math.exp(0.018))
        result=signal_from_closed_bars(prices,prices,prices)
        self.assertIsNotNone(result)
        self.assertEqual(result.side,"SHORT")

if __name__=="__main__":
    unittest.main()
