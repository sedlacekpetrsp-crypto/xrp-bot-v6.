import copy
import pathlib
import tempfile
import unittest

from research.run_btc_miner_revenue_forward_paper import BASELINE_SOURCE_SHA256, DAY, FORWARD_DAY, STARTED_AT, forward_gates, update_state, write_state_atomic


def source_rows():
    return [{"timestamp": (i + 1) * 4 * DAY, "value": 100.0 + i} for i in range(120)]


def prices(count=40):
    start = FORWARD_DAY - 30 * DAY
    return [{"timestamp": start + i * DAY, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0} for i in range(count)]


def state():
    return {"strategy": "BTC_MINER_REVENUE_RECOVERY_XRP_V1", "preregistration_commit": "fc9526123d5b6a820b44ea58fdd1c20e0d9309a2", "started_at_utc": "2026-11-05T19:58:57Z", "backfilled_forward_trades": 0, "prospective_closed_trades": 0, "prospective_net_pnl": 0.0, "prospective_stress_net_pnl": 0.0}


class ForwardPaperTests(unittest.TestCase):
    def test_no_historical_backfill(self):
        now = FORWARD_DAY + 2 * DAY
        updated = update_state(state(), source_rows(), prices(), now, BASELINE_SOURCE_SHA256, "p")
        self.assertEqual(updated["backfilled_forward_trades"], 0)
        self.assertTrue(all(row["timestamp"] < FORWARD_DAY or row["timestamp"] + DAY <= now for row in updated["price_rows"]))

    def test_repeat_is_idempotent(self):
        now = FORWARD_DAY + 2 * DAY; initial = update_state(state(), source_rows(), prices(), now, BASELINE_SOURCE_SHA256, "p")
        prior_base = copy.deepcopy(initial["base_trades"])
        repeated = update_state(initial, source_rows(), prices(), now, BASELINE_SOURCE_SHA256, "p")
        self.assertEqual(repeated["base_trades"], prior_base)

    def test_source_revision_stops(self):
        now = FORWARD_DAY + 2 * DAY; initial = update_state(state(), source_rows(), prices(), now, BASELINE_SOURCE_SHA256, "p")
        changed = source_rows(); changed[-1]["value"] += 1
        with self.assertRaisesRegex(ValueError, "revision"):
            update_state(initial, changed, prices(), now, "new", "p")

    def test_incomplete_candle_excluded(self):
        now = FORWARD_DAY + DAY // 2
        updated = update_state(state(), source_rows(), prices(), now, BASELINE_SOURCE_SHA256, "p")
        self.assertFalse(any(row["timestamp"] >= FORWARD_DAY for row in updated["price_rows"]))

    def test_forward_gates_are_explicit_and_initially_fail(self):
        updated = update_state(state(), source_rows(), prices(), FORWARD_DAY + DAY, BASELINE_SOURCE_SHA256, "p")
        self.assertEqual(updated["status"], "COLLECTING_FORWARD_PAPER")
        self.assertFalse(updated["forward_gates"]["minimum_20_trades"])
        self.assertFalse(updated["forward_gates"]["elapsed_365_days"])

    def test_forward_gate_can_pass_without_json_infinity(self):
        trades = [{"pnl": 1.0} for _ in range(20)]
        curve = [{"equity": 10000.0}, {"equity": 10020.0}]
        gates, _, stress, concentration, _, _ = forward_gates(STARTED_AT + 366 * DAY, trades, trades, curve, curve)
        self.assertTrue(all(gates.values()))
        self.assertIsNone(stress["profit_factor"])
        self.assertTrue(stress["no_losing_trades"])
        self.assertEqual(concentration, 0.05)

    def test_atomic_state_write_replaces_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "state.json"; path.write_text("old")
            write_state_atomic(path, {"ok": True})
            self.assertEqual(path.read_text(), '{\n  "ok": true\n}\n')
            self.assertFalse(path.with_name("state.json.tmp").exists())


if __name__ == "__main__": unittest.main()
