"""Offline safety and determinism checks for the standalone PAPER monitor."""
import tempfile
import unittest
from pathlib import Path

from research.combined_best_signals_bot import save_atomic, snapshot
from research.volatility_managed_momentum_v1 import SYMBOLS


class PaperMonitorTests(unittest.TestCase):
    def sample(self, symbol):
        rates = {"BTCUSDT": 1.002, "ETHUSDT": 1.0015,
                 "SOLUSDT": 1.001, "XRPUSDT": 0.999}
        return [{"timestamp": i * 86400000, "close": 100 * rates[symbol] ** i}
                for i in range(125)]

    def test_signal_only_and_risk_caps(self):
        result = snapshot(fetch=self.sample)
        self.assertEqual(result["mode"], "PAPER_RESEARCH_ONLY")
        self.assertFalse(result["execution_enabled"])
        self.assertLessEqual(result["signal_count"], 2)
        self.assertLessEqual(sum(x["weight"] for x in result["candidates"]), 0.20 + 1e-12)

    def test_rejects_missing_day(self):
        def broken(symbol):
            rows = self.sample(symbol)
            return rows[:60] + rows[61:]
        with self.assertRaises(ValueError):
            snapshot(fetch=broken)

    def test_atomic_json_state(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "state.json"
            save_atomic(target, {"mode": "PAPER_RESEARCH_ONLY"})
            self.assertIn("PAPER_RESEARCH_ONLY", target.read_text())
            self.assertFalse(target.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
