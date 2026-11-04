"""Deterministic regression tests for research-only candidate selection."""
import unittest
from dataclasses import replace
from research.combined_best_signals_paper import SelectionConfig, select_candidates
from research.volatility_managed_momentum_v1 import Config, SYMBOLS


def market(days=125):
    result = {}
    growth = {"BTCUSDT": 0.002, "ETHUSDT": 0.0015,
              "SOLUSDT": 0.001, "XRPUSDT": -0.001}
    for symbol in SYMBOLS:
        result[symbol] = [{"timestamp": i * 86400000,
                           "close": 100.0 * (1 + growth[symbol]) ** i}
                          for i in range(days)]
    return result


class SelectionTests(unittest.TestCase):
    def test_caps_and_paper_only(self):
        rows = select_candidates(market(), 110)
        self.assertLessEqual(len(rows), 2)
        self.assertLessEqual(sum(r["weight"] for r in rows), 0.20 + 1e-12)
        self.assertTrue(all(r["weight"] <= 0.10 for r in rows))
        self.assertTrue(all(r["mode"] == "PAPER_RESEARCH_ONLY" for r in rows))
        self.assertNotIn("XRPUSDT", [r["symbol"] for r in rows])

    def test_no_warmup_no_signal(self):
        self.assertEqual(select_candidates(market(), 89), [])

    def test_future_data_cannot_change_signal(self):
        source = market()
        first = select_candidates(source, 110)
        for symbol in SYMBOLS:
            source[symbol][120]["close"] *= 1000
        self.assertEqual(select_candidates(source, 110), first)

    def test_high_threshold_rejects_everything(self):
        strict = SelectionConfig(minimum_30d_momentum=0.90)
        self.assertEqual(select_candidates(market(), 110, selection=strict), [])

    def test_empty_base_allocation(self):
        falling = market()
        for symbol in SYMBOLS:
            for i, row in enumerate(falling[symbol]):
                row["close"] = 100 * 0.998 ** i
        self.assertEqual(select_candidates(falling, 110), [])

    def test_zero_cap(self):
        self.assertEqual(select_candidates(market(), 110,
                         selection=SelectionConfig(gross_cap=0)), [])


if __name__ == "__main__":
    unittest.main()
