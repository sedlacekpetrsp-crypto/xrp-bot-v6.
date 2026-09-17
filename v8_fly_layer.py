import json
from datetime import datetime, timezone
from fastapi.responses import HTMLResponse, JSONResponse
import v8_fly_layer_core as core
from v8_fly_layer_core import *
import v10_precision_bot as v10
import v11_evidence_bot as v11

# Runtime guard for V11 build 2: override the UTC helper so a stale typo cannot stop the loop.
v11.now = lambda: datetime.now(timezone.utc)

SCALP_BUILD = "v8-adaptive-scalp5-20260917-1"
SCALP_NET_TARGET_USDC = 5.0
SCALP_LOCK_NET_USDC = 2.0
SCALP_MAX_ENTRY_Z = 1.40
SCALP_STRONG_ADX_MIN = 23.0
SCALP_STRONG_Z_MIN = 0.65
SCALP_STRONG_VOLUME_MIN = 1.10
RESET_MARKER = "v8-scalp5-reset-10000-20260917"


def _reset_v8_scalp_once(module):
    """One-time clean slate for V8 Adaptive only; does not touch V10/V11 tables."""
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

    # V8 Adaptive gets a distinct job from V10/V11: closed-candle BREAKOUT scalp only.
    # Do not use the old armed/ANTI_STRONG_BREAKOUT or retest entry paths here.
    module.ENABLED_SETUPS = {"BREAKOUT"}
    module.FLY_LAYER_BUILD = SCALP_BUILD
    core.BUILD = SCALP_BUILD

    def confirmed_breakout_only(rows):
        candidates = []
        for row in rows:
            if row.get("signal") not in ("LONG", "SHORT"):
                continue
            if row.get("setup") != "BREAKOUT":
                continue
            if int(row.get("score") or 0) < int(module.MIN_SCORE):
                continue
            if abs(float(row.get("z_momentum") or 0.0)) > SCALP_MAX_ENTRY_Z:
                continue
            if module.last_entry_candle.get(row["symbol"]) == row.get("candle_time"):
                continue
            candidates.append(row)
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda row: (
                int(row.get("score") or 0),
                float(row.get("adx5") or 0.0),
                float(row.get("volume_ratio") or 0.0),
            ),
            reverse=True,
        )[0]

    core.choose_best = confirmed_breakout_only

    original_manage_position = core.manage_position

    async def scalp_manage_position():
        p = module.paper_position
        if p:
            price = await module.get_live_price(p["symbol"], max_age=1.0)
            entry = float(p["entry_price"])
            qty = float(p.get("qty") or 0.0)
            partial_net = float(p.get("partial_realized_pnl") or 0.0)
            running_net = module.estimated_net_per_unit(p["side"], entry, price) * qty
            net_if_closed = partial_net + running_net
            p["scalp_net_if_closed"] = net_if_closed
            p["scalp_target_usdc"] = SCALP_NET_TARGET_USDC

            if net_if_closed >= SCALP_NET_TARGET_USDC:
                try:
                    analysis = await core.strategy(p["symbol"])
                    adx = float(analysis.get("adx5") or 0.0)
                    z = float(analysis.get("z_momentum") or 0.0)
                    volume = float(analysis.get("volume_ratio") or 0.0)
                    book = float(analysis.get("book_imbalance") or 0.5)
                    spread = float(analysis.get("real_spread_pct") or 1.0)
                    if p["side"] == "LONG":
                        regime_ok = analysis.get("regime") == "TREND_LONG"
                        momentum_ok = z >= SCALP_STRONG_Z_MIN
                        book_ok = book >= module.BOOK_LONG_MIN
                    else:
                        regime_ok = analysis.get("regime") == "TREND_SHORT"
                        momentum_ok = z <= -SCALP_STRONG_Z_MIN
                        book_ok = book <= module.BOOK_SHORT_MAX
                    adx_ok = adx >= SCALP_STRONG_ADX_MIN
                    volume_ok = volume >= SCALP_STRONG_VOLUME_MIN
                    spread_ok = spread <= core.MAX_REAL_SPREAD_PCT
                    supporting = sum([adx_ok, momentum_ok, volume_ok, book_ok, spread_ok])
                    strong = bool(regime_ok and supporting >= 4)
                    p["scalp_strong_trend"] = strong
                    p["scalp_trend_checks"] = {
                        "regime": regime_ok,
                        "adx": adx_ok,
                        "momentum": momentum_ok,
                        "volume": volume_ok,
                        "book": book_ok,
                        "spread": spread_ok,
                        "supporting": supporting,
                    }
                except Exception as exc:
                    strong = False
                    p["scalp_strong_trend"] = False
                    p["scalp_trend_error"] = repr(exc)

                if not strong:
                    core.close_trade(price, "SCALP +5 NET / TREND NOT STRONG")
                    return

                # Strong trend: let the runner continue, but protect a positive net result.
                if qty > 0:
                    remaining_lock = max(0.0, SCALP_LOCK_NET_USDC - partial_net)
                    lock_price = module.target_market_for_net_profit(
                        p["side"], entry, remaining_lock / qty
                    )
                    current_stop = float(p["stop_loss"])
                    if p["side"] == "LONG":
                        p["stop_loss"] = max(current_stop, lock_price)
                    else:
                        p["stop_loss"] = min(current_stop, lock_price)
                p["scalp_runner"] = True
                p["scalp_locked_net_usdc"] = SCALP_LOCK_NET_USDC
                module.save_state()

        await original_manage_position()

    core.manage_position = scalp_manage_position
    module.manage_position = scalp_manage_position

    original_analyze = module.analyze
    original_dashboard = module.dashboard
    original_startup = module.startup
    original_shutdown = module.shutdown

    async def combined_startup():
        await original_startup()
        try:
            did_reset = _reset_v8_scalp_once(module)
            print(f"V8_SCALP_RESET applied={did_reset} balance={module.PAPER_BALANCE:.2f} history={len(module.trade_history)}", flush=True)
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
            "net_target_usdc": SCALP_NET_TARGET_USDC,
            "runner_lock_net_usdc": SCALP_LOCK_NET_USDC,
            "entry": "CONFIRMED_CLOSED_CANDLE_BREAKOUT_ONLY",
            "max_entry_z": SCALP_MAX_ENTRY_Z,
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
        html = html.replace("PAPER • pouze BREAKOUT • čisté R:R 1:1,3", "PAPER • SCALP +5 USDC NET • runner jen při silném trendu")
        html = html.replace("setInterval(refresh,10000)", "setInterval(refresh,3000)")
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