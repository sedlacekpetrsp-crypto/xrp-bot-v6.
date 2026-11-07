"""Mechanics tests for the per-trade ledger export (SYNTHETIC prices, not profitability evidence)."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.combined_selection_replay import export_trades as ex
from research.combined_selection_replay import run
from tests.test_combined_selection_replay import DAY, START, synthetic_market

BLOCKS = (("A", "2021-04-11", "2021-09-01", "development"),
          ("B", "2021-09-01", "2022-02-01", "contaminated_check"))


class LedgerExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = synthetic_market(days=430)
        with patch.multiple(run, BLOCKS=BLOCKS, CONTAMINATED_ALL=("2021-06-01", "2022-02-01"),
                            FORWARD_START="2022-01-01"):
            cls.rows, cls.summary = ex.ledger(cls.market, "2022-03-01")
            cls.reference = run.evaluate(cls.market, "2022-03-01")

    def test_summary_equals_unchanged_replay(self):
        self.assertEqual(ex.compare(self.summary, self.reference), [])

    def test_legs_reconcile_with_block_metrics(self):
        totals = ex.per_block_totals(self.rows)
        for cost, blocks in self.summary.items():
            for name, m in blocks.items():
                t = totals.get((cost, name), {"legs": 0, "net_pnl": 0.0})
                self.assertEqual(t["legs"], m["trades"])
                self.assertAlmostEqual(t["net_pnl"], m["net_pnl"], places=6)
        self.assertGreater(len(self.rows), 0)

    def test_costs_scale_and_rows_are_chronological(self):
        for cost in ("cost_x1", "cost_x2", "cost_x3"):
            self.assertIn(cost, self.summary)
        x1 = sum(r["fees"] for r in self.rows if r["cost_multiplier"] == 1.0 and r["block"] == "A")
        x2 = sum(r["fees"] for r in self.rows if r["cost_multiplier"] == 2.0 and r["block"] == "A")
        self.assertGreater(x2, x1)
        for r in self.rows:
            self.assertLessEqual(r["entry_ts"], r["exit_ts"])

    def test_compare_flags_changed_summary(self):
        bad = json.loads(json.dumps(self.reference))
        bad["cost_x1"]["A"]["net_pnl"] += 0.01
        self.assertTrue(any(d[2] == "net_pnl" for d in ex.compare(self.summary, bad)))

    def test_written_csv_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            hashes = ex.write(self.rows, d)
            with open(Path(d) / "trades.csv") as f:
                back = list(csv.DictReader(f))
            self.assertEqual(len(back), len(self.rows))
            self.assertAlmostEqual(float(back[0]["net_pnl"]), self.rows[0]["net_pnl"], places=12)
            self.assertEqual(set(hashes), {"trades.csv", "trades.json"})


if __name__ == "__main__":
    unittest.main()
