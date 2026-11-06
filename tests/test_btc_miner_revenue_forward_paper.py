import copy
import unittest

from research.run_btc_miner_revenue_forward_paper import BASELINE_SOURCE_SHA256, DAY, FORWARD_DAY, update_state


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


if __name__ == "__main__": unittest.main()
