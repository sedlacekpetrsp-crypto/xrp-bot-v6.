"""Mechanics tests on SYNTHETIC prices. They verify accounting, causality and
cost handling of the replay harness. They are NOT evidence of profitability."""
import hashlib
import io
import random
import unittest
import zipfile

from research.combined_selection_replay import run
from research.volatility_managed_momentum_v1 import (Config, SYMBOLS, allocation,
                                                     backtest, daily_market)

DAY = 86_400_000
HOUR = 3_600_000
START = 1_609_459_200_000  # 2021-01-01


def synthetic_market(days=430, seed=7):
    rng = random.Random(seed)
    market = {}
    for k, symbol in enumerate(SYMBOLS):
        price, bars = 100.0 + 10 * k, []
        drift = (0.0004, 0.0002, -0.0001, 0.0003)[k]
        for h in range(days * 24):
            o = price
            c = max(0.01, o * (1 + drift + rng.gauss(0, 0.01)))
            hi, lo = max(o, c) * (1 + abs(rng.gauss(0, 0.003))), min(o, c) * (1 - abs(rng.gauss(0, 0.003)))
            bars.append({"timestamp": START + h * HOUR, "open": o, "high": hi,
                         "low": lo, "close": c, "volume": 1.0})
            price = c
        market[symbol] = bars
    return market


class ReplayMechanics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = synthetic_market()
        cls.start, cls.end = START + 100 * DAY, START + 425 * DAY

    def test_default_rule_unchanged_by_weights_hook(self):
        a = backtest(self.market, self.start, self.end, Config())
        b = backtest(self.market, self.start, self.end, Config(), allocation)
        self.assertEqual(a, b)

    def test_weights_only_see_completed_days(self):
        calls = []
        daily_stamps = [d["timestamp"] for d in daily_market(self.market)[SYMBOLS[0]]]

        def spy(daily, i, config):
            calls.append(i)
            return run.combined_weights(daily, i, config)
        backtest(self.market, self.start, self.end, Config(), spy)
        self.assertTrue(calls)
        # Every decision index refers to a day that closed before some month-open hour.
        for i in calls:
            self.assertEqual((daily_stamps[i] + DAY) % DAY, 0)
            self.assertLessEqual(daily_stamps[i] + DAY, self.end)

    def test_combined_caps_and_accounting_identity(self):
        daily = daily_market(self.market)
        for i in range(100, len(daily[SYMBOLS[0]]), 17):
            w = run.combined_weights(daily, i, Config())
            self.assertLessEqual(len(w), 2)
            self.assertTrue(all(0 < v <= 0.10 + 1e-12 for v in w.values()))
            self.assertLessEqual(sum(w.values()), 0.20 + 1e-12)
        result = backtest(self.market, self.start, self.end, Config(), run.combined_weights)
        self.assertAlmostEqual(sum(t["net_pnl"] for t in result["trades"]),
                               result["ending_equity"] - 10_000.0, places=6)
        m = run.metrics(result)
        self.assertEqual(m["trades"], len(result["trades"]))

    def test_higher_costs_never_improve_net(self):
        nets = [run.metrics(backtest(self.market, self.start, self.end,
                                     run.scaled(Config(), x), run.combined_weights))["net_pnl"]
                for x in run.COST_MULTIPLIERS]
        self.assertGreaterEqual(nets[0], nets[1])
        self.assertGreaterEqual(nets[1], nets[2])

    def test_future_bars_do_not_change_past_trades(self):
        cut = START + 300 * DAY
        base = backtest(self.market, self.start, cut, Config(), run.combined_weights)
        altered = {s: [dict(b) for b in bars] for s, bars in self.market.items()}
        for s in SYMBOLS:
            for b in altered[s]:
                if b["timestamp"] >= cut:
                    b.update(open=b["open"] * 3, high=b["high"] * 3, low=b["low"] * 3, close=b["close"] * 3)
        again = backtest(altered, self.start, cut, Config(), run.combined_weights)
        self.assertEqual(base["trades"], again["trades"])

    def test_archive_hash_mismatch_aborts_and_microseconds_parse(self):
        rows = "\n".join(f"{(1_735_689_600_000 + h * HOUR) * 1000},1,2,0.5,1.5,10,0,0,0,0,0,0"
                         for h in range(31 * 24))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("x.csv", rows)
        payload = buf.getvalue()
        bars = run.parse_archive(payload, "BTCUSDT", 2025, 1)
        self.assertEqual(bars[0]["timestamp"], 1_735_689_600_000)
        url = "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-09.zip"
        import tempfile
        with tempfile.TemporaryDirectory() as cache:
            with self.assertRaisesRegex(ValueError, "SHA256"):
                run.load_market(cache, "2020-10-01", [{"url": url, "sha256": "0" * 64}],
                                fetch=lambda u: payload)
        self.assertNotEqual(hashlib.sha256(payload).hexdigest(), "0" * 64)


if __name__ == "__main__":
    unittest.main()
