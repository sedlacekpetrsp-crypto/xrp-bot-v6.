import unittest
from research.combined_paper_execution import fresh, step


class CombinedPaperExecutionTests(unittest.TestCase):
    def test_entries_are_paper_and_idempotent(self):
        prices = {"BTCUSDT": 100, "ETHUSDT": 100}
        targets = [{"symbol": "BTCUSDT", "weight": 0.1},
                   {"symbol": "ETHUSDT", "weight": 0.1}]
        day = 1793664000000
        first = step(fresh(), day, targets, prices, "2026-11-04T00:00:00Z")
        second = step(first, day, targets, prices, "2026-11-04T00:15:00Z")
        self.assertEqual(len(first["positions"]), 2)
        self.assertEqual(first["positions"], second["positions"])
        self.assertEqual(first["cash"], second["cash"])
        self.assertEqual(first["mode"], "PAPER_ONLY")
        self.assertLess(first["equity"], 10000)

    def test_stop_closes_and_records_fees(self):
        day = 1793664000000
        first = step(fresh(), day, [{"symbol": "BTCUSDT", "weight": 0.1}],
                     {"BTCUSDT": 100}, "entry")
        stopped = step(first, day, [], {"BTCUSDT": 80}, "exit")
        self.assertEqual(stopped["open_count"], 0)
        self.assertEqual(stopped["trade_count"], 1)
        self.assertEqual(stopped["trades"][0]["reason"], "STOP")
        self.assertLess(stopped["trades"][0]["net_pnl"], 0)

    def test_rejects_invalid_price(self):
        with self.assertRaises(ValueError):
            step(fresh(), 1793664000000, [], {"BTCUSDT": 0})

    def test_monthly_rebalance_does_not_compound_intraday(self):
        day = 1793664000000
        target = [{"symbol": "BTCUSDT", "weight": 0.1}]
        first = step(fresh(), day, target, {"BTCUSDT": 100}, "entry")
        next_day = step(first, day + 86400000, target, {"BTCUSDT": 110}, "next")
        self.assertEqual(first["positions"]["BTCUSDT"]["qty"],
                         next_day["positions"]["BTCUSDT"]["qty"])
        self.assertEqual(next_day["trade_count"], 0)


if __name__ == "__main__":
    unittest.main()
