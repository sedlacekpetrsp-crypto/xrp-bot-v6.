import asyncio
import json
import unittest

from research import max_effect_forward as mx
from research import max_effect_forward_bot as bot

DAY = mx.DAY_MS
MONDAY = mx.first_monday(1794700800000)  # 2026-11-16
SUNDAY = MONDAY - DAY


def flat_closes(decision, bumps):
    """Každé aktivum: plochá cena 100 a jeden skok o `bump` uvnitř okna."""
    end = decision - 2 * DAY
    out = {}
    for symbol in mx.ASSETS:
        series = {end - k * DAY: 100.0 for k in range(mx.L_DAYS + 1)}
        jump_day = end - 5 * DAY
        for day in series:
            if day >= jump_day:
                series[day] = 100.0 * (1 + bumps[symbol])
        out[symbol] = series
    return out


BUMPS = {s: 0.01 * (i + 1) for i, s in enumerate(sorted(mx.ASSETS))}
CLOSES = flat_closes(MONDAY, BUMPS)
PRICES = {s: 100.0 for s in mx.ASSETS}


def opened():
    waiting = mx.step(mx.fresh(), SUNDAY + 1000, CLOSES, {}, PRICES, {}, "sun")
    return mx.step(waiting, MONDAY + 60000, CLOSES, {}, PRICES, {}, "mon")


class SignalTests(unittest.TestCase):
    def test_first_monday(self):
        self.assertEqual(mx.first_monday(0), 4 * DAY)  # 1970-01-05
        self.assertEqual(mx.first_monday(MONDAY), MONDAY)
        self.assertEqual(mx.first_monday(MONDAY + DAY), MONDAY + 7 * DAY)
        self.assertEqual(mx.first_monday(SUNDAY), MONDAY)

    def test_max_score_matches_manual(self):
        scores = mx.max_scores(CLOSES, MONDAY)
        for symbol in mx.ASSETS:
            self.assertAlmostEqual(scores[symbol], BUMPS[symbol])

    def test_missing_day_makes_asset_ineligible(self):
        closes = {s: dict(v) for s, v in CLOSES.items()}
        del closes["BTCUSDT"][MONDAY - 9 * DAY]
        self.assertNotIn("BTCUSDT", mx.max_scores(closes, MONDAY))

    def test_decision_ignores_data_after_d_minus_2(self):
        closes = {s: dict(v) for s, v in CLOSES.items()}
        for s in closes:
            closes[s][MONDAY - DAY] = 999.0
            closes[s][MONDAY] = 1.0
        self.assertEqual(mx.max_scores(closes, MONDAY), mx.max_scores(CLOSES, MONDAY))

    def test_select_long_low_short_high(self):
        picks = mx.select(mx.max_scores(CLOSES, MONDAY))
        order = sorted(mx.ASSETS)
        self.assertEqual([p[0] for p in picks if p[1] == 1], order[:3])
        self.assertEqual([p[0] for p in picks if p[1] == -1], order[-3:])

    def test_fewer_than_six_eligible_means_cash(self):
        scores = dict(list(mx.max_scores(CLOSES, MONDAY).items())[:5])
        self.assertEqual(mx.select(scores), [])


class StepTests(unittest.TestCase):
    def test_waits_for_monday(self):
        s = mx.step(mx.fresh(), SUNDAY + 1000, CLOSES, {}, PRICES, {}, "sun")
        self.assertEqual(s["open_count"], 0)
        self.assertEqual(s["next_rebalance_day"], MONDAY)
        self.assertEqual(s["equity"], 10000.0)

    def test_opens_six_dollar_neutral_legs(self):
        s = opened()
        self.assertEqual(s["open_count"], 6)
        longs = sum(p["notional"] for p in s["positions"].values() if p["side"] > 0)
        shorts = sum(p["notional"] for p in s["positions"].values() if p["side"] < 0)
        self.assertAlmostEqual(longs, 3000.0)
        self.assertAlmostEqual(shorts, 3000.0)
        self.assertEqual(s["next_rebalance_day"], MONDAY + 28 * DAY)
        self.assertEqual(s["last_decision"]["late_days"], 0)
        self.assertLess(s["equity"], 10000.0)  # zaplacené poplatky a skluz
        json.dumps(s)

    def test_idempotent_between_rebalances(self):
        first = opened()
        second = mx.step(first, MONDAY + 3 * DAY, CLOSES, {}, PRICES, {}, "later")
        self.assertEqual({k: v["qty"] for k, v in first["positions"].items()},
                         {k: v["qty"] for k, v in second["positions"].items()})
        self.assertEqual(second["trade_count"], 0)

    def test_does_not_mutate_input(self):
        first = opened()
        frozen = json.dumps(first, sort_keys=True)
        mx.step(first, MONDAY + DAY, CLOSES, {}, {s: 120.0 for s in mx.ASSETS},
                {s: [(MONDAY + 8 * 3600000, 0.001)] for s in mx.ASSETS}, "x")
        self.assertEqual(json.dumps(first, sort_keys=True), frozen)

    def test_pnl_identity_and_direction(self):
        first = opened()
        long_symbol = next(k for k, v in first["positions"].items() if v["side"] > 0)
        prices = dict(PRICES)
        prices[long_symbol] = 110.0
        s = mx.step(first, MONDAY + DAY, CLOSES, {}, prices, {}, "x")
        self.assertGreater(s["positions"][long_symbol]["unrealized_pnl"], 90)
        self.assertAlmostEqual(s["equity"] - 10000.0,
                               s["realized_pnl"] + s["unrealized_pnl"])

    def test_funding_sign_and_single_application(self):
        first = opened()
        stamp = MONDAY + 8 * 3600000
        funding = {s: [(stamp, 0.001), (MONDAY - 3600000, 0.5)] for s in mx.ASSETS}
        s = mx.step(first, stamp + 1000, CLOSES, {}, PRICES, funding, "x")
        for pos in s["positions"].values():
            expected = -pos["side"] * 0.001 * pos["qty"] * 100.0
            self.assertAlmostEqual(pos["funding"], expected)
        again = mx.step(s, stamp + 900000, CLOSES, {}, PRICES, funding, "y")
        for symbol, pos in again["positions"].items():
            self.assertAlmostEqual(pos["funding"], s["positions"][symbol]["funding"])

    def test_short_liquidation_loses_notional(self):
        first = opened()
        short_symbol = next(k for k, v in first["positions"].items() if v["side"] < 0)
        prices = dict(PRICES)
        prices[short_symbol] = 201.0
        s = mx.step(first, MONDAY + DAY, CLOSES, {}, prices, {}, "x")
        self.assertNotIn(short_symbol, s["positions"])
        trade = s["trades"][-1]
        self.assertEqual(trade["reason"], "LIQUIDATION")
        self.assertAlmostEqual(trade["net_pnl"], -1000.0 - 1000.0 * mx.FEE)

    def test_liquidation_by_daily_high_after_entry_day_only(self):
        first = opened()
        short_symbol = next(k for k, v in first["positions"].items() if v["side"] < 0)
        same_day = mx.step(first, MONDAY + 2 * DAY, CLOSES, {short_symbol: {MONDAY: 500.0}},
                           PRICES, {}, "x")
        self.assertIn(short_symbol, same_day["positions"])
        later = mx.step(first, MONDAY + 2 * DAY, CLOSES,
                        {short_symbol: {MONDAY + DAY: 500.0}}, PRICES, {}, "x")
        self.assertNotIn(short_symbol, later["positions"])

    def test_rebalance_after_28_days_closes_and_reopens(self):
        first = opened()
        nxt = MONDAY + 28 * DAY
        s = mx.step(first, nxt + 60000, flat_closes(nxt, BUMPS), {}, PRICES, {}, "reb")
        self.assertEqual(s["trade_count"], 6)
        self.assertTrue(all(t["reason"] == "REBALANCE" for t in s["trades"]))
        self.assertEqual(s["open_count"], 6)
        self.assertLess(s["realized_pnl"], 0)  # ploché ceny => jen náklady
        self.assertEqual(s["next_rebalance_day"], nxt + 28 * DAY)
        self.assertAlmostEqual(s["equity"] - 10000.0,
                               s["realized_pnl"] + s["unrealized_pnl"])

    def test_missing_signal_data_means_cash_for_cycle(self):
        waiting = mx.step(mx.fresh(), SUNDAY, CLOSES, {}, PRICES, {}, "sun")
        s = mx.step(waiting, MONDAY + 1, {}, {}, PRICES, {}, "mon")
        self.assertEqual(s["open_count"], 0)
        self.assertEqual(s["last_decision"]["legs"], 0)
        self.assertEqual(s["next_rebalance_day"], MONDAY + 28 * DAY)

    def test_rejects_missing_price_for_open_position(self):
        first = opened()
        prices = dict(PRICES)
        prices.pop(next(iter(first["positions"])))
        with self.assertRaises(ValueError):
            mx.step(first, MONDAY + DAY, CLOSES, {}, prices, {}, "x")


class OkxParsingTests(unittest.TestCase):
    def test_daily_skips_unconfirmed_and_current_candle(self):
        now = MONDAY + 3600000
        rows = [[str(MONDAY), "1", "3", "0.5", "2", "0", "0", "0", "0"],
                [str(MONDAY - DAY), "1", "3", "0.5", "2", "0", "0", "0", "1"],
                [str(MONDAY - 2 * DAY), "1", "4", "0.5", "3", "0", "0", "0", "1"]]
        closes, highs = bot.parse_daily(rows, now)
        self.assertEqual(closes, {MONDAY - DAY: 2.0, MONDAY - 2 * DAY: 3.0})
        self.assertEqual(highs[MONDAY - 2 * DAY], 4.0)

    def test_daily_rejects_misaligned_candle(self):
        with self.assertRaises(ValueError):
            bot.parse_daily([[str(MONDAY + 5), "1", "3", "1", "2", "0", "0", "0", "1"]],
                            MONDAY + 2 * DAY)

    def test_prices_and_funding(self):
        prices = bot.parse_prices([{"instId": "BTC-USDT-SWAP", "last": "50000.5"},
                                   {"instId": "PEPE-USDT-SWAP", "last": "1"},
                                   {"instId": "ETH-USDT-SWAP", "last": ""}])
        self.assertEqual(prices, {"BTCUSDT": 50000.5})
        events = bot.parse_funding([
            {"fundingTime": "200", "fundingRate": "0.0002", "realizedRate": "0.0001"},
            {"fundingTime": "100", "fundingRate": "0.0003"}])
        self.assertEqual(events, [(100, 0.0003), (200, 0.0001)])

    def test_collect_treats_unlisted_instrument_as_ineligible(self):
        now = MONDAY + 3600000

        def get(path, params):
            if path == "market/candles":
                if params["instId"] == "BNB-USDT-SWAP":
                    raise bot.OkxRejected("51001", "Instrument ID doesn't exist")
                return [[str(MONDAY - DAY), "1", "3", "0.5", "2", "0", "0", "0", "1"]]
            if path == "market/tickers":
                return [{"instId": bot.inst(s), "last": "2"} for s in mx.ASSETS]
            return [{"fundingTime": str(MONDAY), "realizedRate": "0.0001"}]

        closes, highs, prices, funding, unavailable, warnings = bot.collect(
            {"BTCUSDT": {"funding_through_ms": MONDAY - 1}}, now, get=get, pause=0)
        self.assertEqual(unavailable, ["BNBUSDT"])
        self.assertNotIn("BNBUSDT", closes)
        self.assertEqual(len(prices), 8)
        self.assertEqual(funding, {"BTCUSDT": [(MONDAY, 0.0001)]})
        self.assertEqual(warnings, [])

    def test_collect_propagates_other_okx_errors(self):
        def get(path, params):
            raise bot.OkxRejected("50011", "Too many requests")
        with self.assertRaises(bot.OkxRejected):
            bot.collect({}, MONDAY, get=get, pause=0)


class WebTests(unittest.TestCase):
    def test_status_payload_ok_and_database_down(self):
        code, body = bot.status_payload(lambda: {"status": "RUNNING",
                                                 "snapshot": {"generated_at_utc": "t"},
                                                 "paper_portfolio": {"equity": 1}})
        self.assertEqual((code, body["status"], body["generated_at_utc"]), (200, "RUNNING", "t"))
        self.assertFalse(body["execution_enabled"])

        def broken():
            raise RuntimeError("no db")
        code, body = bot.status_payload(broken)
        self.assertEqual((code, body["status"]), (503, "DATABASE_UNAVAILABLE"))

    def test_install_registers_routes_and_page_renders(self):
        class App:
            def __init__(self):
                self.routes, self.startup = {}, []

            def add_api_route(self, path, endpoint, **kwargs):
                self.routes[path] = endpoint

            def on_event(self, name):
                return lambda fn: self.startup.append((name, fn)) or fn

        app = App()
        bot.install(app)
        self.assertEqual(set(app.routes), {"/max-effect", "/max-effect/status"})
        self.assertEqual(app.startup[0][0], "startup")
        response = asyncio.run(app.routes["/max-effect"]())
        self.assertIn("MAX-efekt", response.body.decode())
        self.assertNotIn("order", bot.OKX + "market/candles")


if __name__ == "__main__":
    unittest.main()
