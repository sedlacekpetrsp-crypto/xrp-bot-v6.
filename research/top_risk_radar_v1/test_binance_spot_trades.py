import unittest
from research.top_risk_radar_v1.binance_spot_trades import epoch_to_utc,parse_spot_trades_csv

class BinanceSpotTradeTests(unittest.TestCase):
    def test_millisecond_2024(self):
        self.assertEqual(epoch_to_utc("1704067200000").year,2024)
    def test_microsecond_2025(self):
        self.assertEqual(epoch_to_utc("1735689600010866").year,2025)
    def test_headerless_two_trades_same_timestamp_allowed(self):
        rows=["1,1.00,10,10,1735689600010866,true,true","2,0.99,1,0.99,1735689600010866,false,true"]
        self.assertEqual(len(parse_spot_trades_csv(rows)),2)
    def test_header_allowed(self):
        rows=["id,price,qty,quoteQty,time,isBuyerMaker,isBestMatch","1,1,1,1,1735689600010866,true,true"]
        self.assertEqual(len(parse_spot_trades_csv(rows)),1)
    def test_reject_bad_timestamp_magnitude(self):
        with self.assertRaises(ValueError):
            epoch_to_utc("12345")
    def test_reject_nonmonotonic(self):
        rows=["1,1,1,1,1735689600010866,true,true","2,1,1,1,1735689600010865,true,true"]
        with self.assertRaises(ValueError):
            parse_spot_trades_csv(rows)
    def test_reject_wrong_columns(self):
        with self.assertRaises(ValueError):
            parse_spot_trades_csv(["1,1,1"])
