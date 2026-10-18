import unittest
from elite.v2_candidate import compression_expansion

class CandidateTests(unittest.TestCase):
    def test_constant_bars(self):
        values=[1.0]*60
        self.assertIsNone(compression_expansion(values,values,values))

    def test_insufficient_bars(self):
        values=[1.0]*10
        self.assertIsNone(compression_expansion(values,values,values))

    def test_long_after_compression(self):
        high=[100.5]*24+[100.1]*24+[102.0]
        low=[99.5]*24+[99.9]*24+[99.0]
        close=[100.0]*24+[100.0]*24+[101.5]
        signal=compression_expansion(high,low,close)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.side,"LONG")

    def test_short_after_compression(self):
        high=[100.5]*24+[100.1]*24+[101.0]
        low=[99.5]*24+[99.9]*24+[98.0]
        close=[100.0]*24+[100.0]*24+[98.5]
        signal=compression_expansion(high,low,close)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.side,"SHORT")

if __name__=="__main__":
    unittest.main()
