import asyncio
import json
from datetime import datetime, timezone

from fastapi.responses import HTMLResponse, JSONResponse

import v8_fly_layer_core as core
from v8_fly_layer_core import *
import v10_precision_bot as v10
import v11_evidence_bot as v11

v11.now = lambda: datetime.now(timezone.utc)

SCALP_BUILD = "v8-adaptive-market-quality-no-time-exit-20260917-3"
SCALP_NET_TARGET_USDC = 5.0
SCALP_LOCK_NET_USDC = 2.0
RAPID_MIN_SCORE = 5
RAPID_LOOP_SECONDS = 5
RAPID_MAX_ENTRY_Z = 2.20
RAPID_MAX_SPREAD_PCT = 0.0010
RAPID_STRONG_SCORE = 7
RAPID_STRONG_ADX = 20.0
RAPID_STRONG_Z = 0.50
RAPID_STRONG_VOLUME = 1.00
RESET_MARKER = "v8-scalp5-reset-10000-20260917"


def _reset_v8_scalp_once(module):
    if not module.DATABASE_URL:
        return False
    state = {
        "paper_balance": 10000.0,
        "paper_position": None,
        "last_entry_candle": {},
        "cooldown_until": None,
    }
    with module.get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v8_scalp_migrations(
                    marker TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("SELECT 1 FROM v8_scalp_migrations WHERE marker=%s", (RESET_MARKER,))
            if cur.fetchone():
                return False
            cur.execute("DELETE FROM v8fixed_trades")
            cur.execute("DELETE FROM v8fixed_signals")
            cur.execute("""
                INSERT INTO v8fixed_state(id,state) VALUES(1,%s::jsonb)
                ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state
            """, (json.dumps(state),))
            cur.execute("INSERT INTO v8_scalp_migrations(marker) VALUES(%s)", (RESET_MARKER,))
        conn.commit()
    module.PAPER_BALANCE = 10000.0
    module.paper_position = None
    module.trade_history = []
    module.last_entry_candle = {}
    module.cooldown_until = None
    module.last_analysis = {}
    module.save_state()
    return True


def install(module):
    core.install(module)

    # Market-driven PAPER scalp. Trade count is never a target.
    module.FLY_LAYER_BUILD = SCALP_BUILD
    core.BUILD = SCALP_BUILD
    module.LOOP_SECONDS = RAPID_LOOP_SECONDS
    module.RISK_PER_TRADE = 0.0015
    module.MIN_STOP_RATE = 0.0015
    module.MAX_STOP_RATE = 0.0060
    module.MAX_NOTIONAL_SHARE = 0.50
    module.SETUP_PARAMS["RAPID_MOMENTUM"] = {"atr_mult": 0.55, "rr": 0.90}
    module.ENABLED_SETUPS = {"RAPID_MOMENTUM"}

    async def aggressive_strategy(symbol):
        k1, k5, bk = await asyncio.gather(
            module.get_klines(symbol, "1m"),
            module.get_klines(symbol, "5m"),
            core.book(symbol),
        )
        a1, a5 = k1[:-1], k5[:-1]
        h = [float(x[2]) for x in a1]
        l = [float(x[3]) for x in a1]
        c = [float(x[4]) for x in a1]
        v = [float(x[5]) for x in a1]
        c5 = [float(x[4]) for x in a5]
        h5 = [float(x[2]) for x in a5]
        l5 = [float(x[3]) for x in a5]
        live = float(k1[-1][4])
        candle_time = int(k1[-1][0])

        e5 = module.ema(c, 5)
        e13 = module.ema(c, 13)
        e9_5 = module.ema(c5, 9)
        e21_5 = module.ema(c5, 21)
        rv = module.rsi_wilder(c)
        av = module.atr_wilder(h, l, c)
        ad = module.adx_wilder(h5, l5, c5)
        mh, mhp = module.macd_hist(c)
        vw = module.vwap(h, l, c, v)
        z = core.z_momentum(c)
        imb = float(bk.get("imbalance") or 0.5)
        spread = float(bk.get("spread_pct") or 1.0)
        pv = v[-21:-1]
        vr = v[-1] / (sum(pv) / len(pv)) if pv and sum(pv) > 0 else 0.0

        rng = max(h[-1] - l[-1], 1e-12)
        bull = (c[-1] - l[-1]) / rng
        bear = (h[-1] - c[-1]) / rng
        prev_hi = max(h[-9:-1]) if len(h) >= 9 else h[-1]
        prev_lo = min(l[-9:-1]) if len(l) >= 9 else l[-1]
        mac_up = mh is not None and (mh >= 0 or (mhp is not None and mh > mhp))
        mac_dn = mh is not None and (mh <= 0 or (mhp is not None and mh < mhp))
        five_up = e9_5 is not None and e21_5 is not None and (e9_5 >= e21_5 or c5[-1] >= e9_5)
        five_dn = e9_5 is not None and e21_5 is not None and (e9_5 <= e21_5 or c5[-1] <= e9_5)
        spread_ok = spread <= RAPID_MAX_SPREAD_PCT

        long_score = sum([
            e5 is not None and e13 is not None and e5 >= e13,
            e5 is not None and live >= e5 * 0.9995,
            rv is not None and 45 <= rv <= 79,
            z >= 0.05,
            mac_up,
            vr >= 0.60,
            imb >= 0.49,
            vw is None or live >= vw * 0.9995,
            five_up,
            bull >= 0.48,
        ])
        short_score = sum([
            e5 is not None and e13 is not None and e5 <= e13,
            e5 is not None and live <= e5 * 1.0005,
            rv is not None and 21 <= rv <= 55,
            z <= -0.05,
            mac_dn,
            vr >= 0.60,
            imb <= 0.51,
            vw is None or live <= vw * 1.0005,
            five_dn,
            bear >= 0.48,
        ])

        long_break = live > prev_hi
        short_break = live < prev_lo
        if long_break:
            long_score += 2
        if short_break:
            short_score += 2

        signal = "WAIT"
        score = max(long_score, short_score)
        preferred = "LONG" if long_score > short_score else "SHORT" if short_score > long_score else ("LONG" if z > 0 else "SHORT" if z < 0 else None)

        # Score 6+ is enough by itself. Score 5 is allowed when the market supplies
        # at least two extra quality confirmations. This keeps it active without
        # forcing trades in dead/choppy conditions.
        if preferred == "LONG":
            quality_support = sum([
                z >= 0.18,
                vr >= 0.80,
                float(ad or 0.0) >= 18.0,
                imb >= 0.505,
                five_up,
                long_break,
            ])
        elif preferred == "SHORT":
            quality_support = sum([
                z <= -0.18,
                vr >= 0.80,
                float(ad or 0.0) >= 18.0,
                imb <= 0.495,
                five_dn,
                short_break,
            ])
        else:
            quality_support = 0

        quality_ok = score >= 6 or (score == RAPID_MIN_SCORE and quality_support >= 2)
        if spread_ok and abs(z) <= RAPID_MAX_ENTRY_Z and preferred and quality_ok:
            signal = preferred
            score = long_score if signal == "LONG" else short_score

        quality = "HIGH" if score >= 8 else "GOOD" if score >= 6 else "OK" if quality_support >= 2 else "LOW"
        regime = "FAST_LONG" if five_up else "FAST_SHORT" if five_dn else "CHOP"
        reason = (
            f"{symbol} MARKET_QUALITY={quality} signal={signal} L/S={long_score}/{short_score} "
            f"support={quality_support} z={z:.2f} vol={vr:.2f}x book={imb:.3f} "
            f"spread={spread*100:.3f}% rsi={rv:.1f} adx5={float(ad or 0):.1f}"
        )
        return {
            "symbol": symbol,
            "price": live,
            "signal": signal,
            "raw_signal": signal,
            "setup": "RAPID_MOMENTUM" if signal in ("LONG", "SHORT") else None,
            "score": int(score),
            "market_quality": quality,
            "quality_support": int(quality_support),
            "candle_time": candle_time,
            "regime": regime,
            "rsi": rv,
            "atr": av,
            "adx5": ad,
            "volume_ratio": vr,
            "book_imbalance": imb,
            "real_spread_pct": spread,
            "z_momentum": z,
            "long_score": long_score,
            "short_score": short_score,
            "reason": reason,
        }

    core.strategy = aggressive_strategy
    module.strategy_analysis = aggressive_strategy

    def aggressive_choose_best(rows):
        candidates = [r for r in rows if r.get("signal") in ("LONG", "SHORT")]
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda r: (
                int(r.get("score") or 0),
                int(r.get("quality_support") or 0),
                abs(float(r.get("z_momentum") or 0.0)),
                float(r.get("volume_ratio") or 0.0),
                float(r.get("adx5") or 0.0),
            ),
            reverse=True,
        )[0]

    core.choose_best = aggressive_choose_best

    original_close_trade = core.close_trade

    def market_close_trade(price, reason):
        original_close_trade(price, reason)
        module.cooldown_until = None
        module.save_state()

    core.close_trade = market_close_trade
    module.close_trade = market_close_trade

    async def market_manage_position():
        p = module.paper_position
        if not p:
            return
        price = await module.get_live_price(p["symbol"], max_age=1.0)
        entry = float(p["entry_price"])
        qty = float(p.get("qty") or 0.0)
        dist = max(float(p.get("risk_distance") or 0.0), 1e-12)
        mr = (price - entry) / dist if p["side"] == "LONG" else (entry - price) / dist
        p["mfe_r"] = max(float(p.get("mfe_r", 0.0)), mr)
        p["mae_r"] = min(float(p.get("mae_r", 0.0)), mr)
        partial_net = float(p.get("partial_realized_pnl") or 0.0)
        net_if_closed = partial_net + module.estimated_net_per_unit(p["side"], entry, price) * qty
        p["scalp_net_if_closed"] = net_if_closed
        p["scalp_target_usdc"] = SCALP_NET_TARGET_USDC

        sl = float(p["stop_loss"])
        if (p["side"] == "LONG" and price <= sl) or (p["side"] == "SHORT" and price >= sl):
            market_close_trade(price, "MARKET STOP")
            return

        try:
            analysis = await aggressive_strategy(p["symbol"])
        except Exception:
            analysis = None

        if net_if_closed >= SCALP_NET_TARGET_USDC:
            strong = False
            if analysis:
                same_side_score = int((analysis.get("long_score") if p["side"] == "LONG" else analysis.get("short_score")) or 0)
                z = float(analysis.get("z_momentum") or 0.0)
                z_ok = z >= RAPID_STRONG_Z if p["side"] == "LONG" else z <= -RAPID_STRONG_Z
                strong = bool(
                    same_side_score >= RAPID_STRONG_SCORE
                    and float(analysis.get("adx5") or 0.0) >= RAPID_STRONG_ADX
                    and float(analysis.get("volume_ratio") or 0.0) >= RAPID_STRONG_VOLUME
                    and z_ok
                )

            if not strong:
                market_close_trade(price, "MARKET +5 NET / NO STRONG CONTINUATION")
                return

            if qty > 0:
                lock_price = module.target_market_for_net_profit(
                    p["side"], entry, SCALP_LOCK_NET_USDC / qty
                )
                if p["side"] == "LONG":
                    p["stop_loss"] = max(float(p["stop_loss"]), lock_price)
                else:
                    p["stop_loss"] = min(float(p["stop_loss"]), lock_price)
            p["scalp_runner"] = True

        # Exit only when the market actually flips against the position.
        # There is deliberately NO age/max-hold/time-exit rule.
        if analysis:
            own = int((analysis.get("long_score") if p["side"] == "LONG" else analysis.get("short_score")) or 0)
            opp = int((analysis.get("short_score") if p["side"] == "LONG" else analysis.get("long_score")) or 0)
            opposite_signal = analysis.get("signal") == ("SHORT" if p["side"] == "LONG" else "LONG")
            if opposite_signal and opp >= max(6, own + 2):
                market_close_trade(price, "MARKET MOMENTUM FLIP")
                return

        tp = float(p["take_profit"])
        if (p["side"] == "LONG" and price >= tp) or (p["side"] == "SHORT" and price <= tp):
            market_close_trade(price, "MARKET TAKE PROFIT")
            return

        module.save_state()

    core.manage_position = market_manage_position
    module.manage_position = market_manage_position

    original_analyze = module.analyze
    original_dashboard = module.dashboard
    original_startup = module.startup
    original_shutdown = module.shutdown

    async def combined_startup():
        await original_startup()
        try:
            did_reset = _reset_v8_scalp_once(module)
            print(
                f"V8_SCALP_RESET applied={did_reset} balance={module.PAPER_BALANCE:.2f} history={len(module.trade_history)}",
                flush=True,
            )
        except Exception as exc:
            print("V8_SCALP_RESET_FAILED", repr(exc), flush=True)
        try:
            if not v10.bot_task or v10.bot_task.done():
                await v10.startup()
            print("V10_PRECISION_STARTED", v10.BUILD, flush=True)
        except Exception as exc:
            print("V10_PRECISION_START_FAILED", repr(exc), flush=True)
        try:
            if not v11.bot_task or v11.bot_task.done():
                await v11.startup()
            print("V11_EVIDENCE_STARTED", v11.BUILD, flush=True)
        except Exception as exc:
            print("V11_EVIDENCE_START_FAILED", repr(exc), flush=True)

    async def combined_shutdown():
        try:
            await v11.shutdown()
        except Exception as exc:
            print("V11_EVIDENCE_SHUTDOWN_FAILED", repr(exc), flush=True)
        try:
            await v10.shutdown()
        except Exception as exc:
            print("V10_PRECISION_SHUTDOWN_FAILED", repr(exc), flush=True)
        await original_shutdown()

    module.startup = combined_startup
    module.shutdown = combined_shutdown

    module.app.router.routes[:] = [
        route for route in module.app.router.routes
        if not (
            getattr(route, "path", None) in ("/", "/analyze")
            and "GET" in (getattr(route, "methods", set()) or set())
        )
    ]

    @module.app.get("/analyze")
    async def analyze_with_pnl_breakdown():
        data = await original_analyze()
        p = data.get("position")
        gross = net = costs = 0.0
        if p:
            cached = module.price_cache.get(p["symbol"])
            if cached:
                px = float(cached["price"])
                entry = float(p["entry_price"])
                qty = float(p["qty"])
                side = p["side"]
                gross = ((px - entry) if side == "LONG" else (entry - px)) * qty
                net = module.estimated_net_per_unit(side, entry, px) * qty + float(p.get("partial_realized_pnl") or 0.0)
                costs = max(gross - (net - float(p.get("partial_realized_pnl") or 0.0)), 0.0)
        data["unrealized_gross_pnl"] = gross
        data["unrealized_pnl"] = net
        data["estimated_costs"] = costs
        data["equity"] = float(data.get("paper_balance", 0.0)) + net
        data["scalp_mode"] = {
            "build": SCALP_BUILD,
            "mode": "MARKET_QUALITY_NO_TIME_EXIT",
            "min_score": RAPID_MIN_SCORE,
            "scan_seconds": RAPID_LOOP_SECONDS,
            "time_exit": False,
            "net_target_usdc": SCALP_NET_TARGET_USDC,
            "runner_lock_net_usdc": SCALP_LOCK_NET_USDC,
        }
        data["v10_precision"] = {
            "build": v10.BUILD,
            "running": bool(v10.bot_task and not v10.bot_task.done()),
            "last_cycle_at": v10.last_cycle_at,
            "error": v10.last_error,
            "dashboard": "/v10/",
        }
        data["v11_evidence"] = {
            "build": v11.BUILD,
            "running": bool(v11.bot_task and not v11.bot_task.done()),
            "last_cycle_at": v11.LAST_CYCLE,
            "error": v11.ERR,
            "dashboard": "/v11/",
            "validation": v11.snapshot().get("validation"),
        }
        return JSONResponse(data, headers={"Cache-Control": "no-store"})

    @module.app.get("/", response_class=HTMLResponse)
    async def dashboard_with_pnl_breakdown():
        html = await original_dashboard()
        old = "const p=d.position; document.getElementById('position').innerHTML=p?`<b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)} • uPnL ${f(d.unrealized_pnl,2)}`:'Žádná otevřená pozice';"
        new = "const p=d.position; document.getElementById('position').innerHTML=p?`<b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)}<br>Hrubý P/L <b class=\"${Number(d.unrealized_gross_pnl)>=0?'green':'red'}\">${Number(d.unrealized_gross_pnl)>=0?'+':''}${f(d.unrealized_gross_pnl,2)} USDC</b> • Čistý P/L <b class=\"${Number(d.unrealized_pnl)>=0?'green':'red'}\">${Number(d.unrealized_pnl)>=0?'+':''}${f(d.unrealized_pnl,2)} USDC</b> • Náklady ${f(d.estimated_costs,2)} USDC`:'Žádná otevřená pozice';"
        html = html.replace(old, new)
        html = html.replace("PAPER • pouze BREAKOUT • čisté R:R 1:1,3", "PAPER • MARKET QUALITY SCALP • bez time exitu • +5 USDC NET")
        html = html.replace("PAPER • AGGRESSIVE RAPID SCALP • best-score vstup • +5 USDC NET", "PAPER • MARKET QUALITY SCALP • bez time exitu • +5 USDC NET")
        html = html.replace("setInterval(refresh,10000)", "setInterval(refresh,2000)")
        html = html.replace("</body>", '<div style="max-width:900px;margin:16px auto;padding:0 16px"><a href="v10/" style="color:#8ea1b8;font-weight:700;margin-right:16px">V10 Precision XRP →</a><a href="v11/" style="color:#21d19f;font-weight:800">V11 Evidence XRP →</a></div></body>')
        return HTMLResponse(html, headers={"Cache-Control": "no-store"})

    async def v10_head():
        return HTMLResponse("", status_code=200, headers={"Cache-Control": "no-store"})

    async def v11_head():
        return HTMLResponse("", status_code=200, headers={"Cache-Control": "no-store"})

    v10.app.add_api_route("/", v10_head, methods=["HEAD"], include_in_schema=False)
    v11.app.add_api_route("/", v11_head, methods=["HEAD"], include_in_schema=False)

    module.app.mount("/v10", v10.app)
    module.app.mount("/v11", v11.app)