import asyncio
import json
from datetime import datetime, timezone

from fastapi.responses import HTMLResponse, JSONResponse

import v8_fly_layer_core as core
from v8_fly_layer_core import *
import v10_precision_bot as v10
import v11_evidence_bot as v11

v11.now = lambda: datetime.now(timezone.utc)

SCALP_BUILD = "v8-adaptive-market-quality-multi3-5m-candle-stop-20260917-6"
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
MAX_OPEN_POSITIONS = 3
MAX_POSITION_NOTIONAL_SHARE = 0.33
MAX_TOTAL_NOTIONAL_SHARE = 0.90
CANDLE_STOP_LOOKBACK = 5
CANDLE_STOP_BUFFER_PCT = 0.00010
RESET_MARKER = "v8-scalp5-reset-10000-20260917"


def _reset_v8_scalp_once(module):
    if not module.DATABASE_URL:
        return False
    state = {
        "paper_balance": 10000.0,
        "paper_position": None,
        "paper_positions": {},
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
    module.paper_positions = {}
    module.trade_history = []
    module.last_entry_candle = {}
    module.cooldown_until = None
    module.last_analysis = {}
    module.save_state()
    return True


def install(module):
    core.install(module)

    module.FLY_LAYER_BUILD = SCALP_BUILD
    core.BUILD = SCALP_BUILD
    module.LOOP_SECONDS = RAPID_LOOP_SECONDS
    module.RISK_PER_TRADE = 0.0015
    module.MIN_STOP_RATE = 0.0015
    module.MAX_STOP_RATE = 0.0060
    module.MAX_NOTIONAL_SHARE = MAX_POSITION_NOTIONAL_SHARE
    module.SETUP_PARAMS["RAPID_MOMENTUM"] = {"atr_mult": 0.55, "rr": 0.90}
    module.ENABLED_SETUPS = {"RAPID_MOMENTUM"}
    module.paper_positions = {}

    original_load_state = module.load_state

    def sync_compat_position():
        positions = getattr(module, "paper_positions", {}) or {}
        if positions:
            first_symbol = sorted(positions.keys())[0]
            module.paper_position = positions[first_symbol]
        else:
            module.paper_position = None

    def multi_load_state():
        original_load_state()
        positions = {}
        try:
            if module.DATABASE_URL:
                with module.get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT state FROM v8fixed_state WHERE id=1")
                        row = cur.fetchone()
                state = (row[0] if row else {}) or {}
                saved_positions = state.get("paper_positions")
                if isinstance(saved_positions, dict):
                    positions = {
                        str(symbol): dict(pos)
                        for symbol, pos in saved_positions.items()
                        if isinstance(pos, dict) and pos.get("symbol")
                    }
        except Exception as exc:
            print("MULTI LOAD STATE", repr(exc), flush=True)
        if not positions and module.paper_position:
            positions = {module.paper_position["symbol"]: module.paper_position}
        module.paper_positions = positions
        sync_compat_position()

    def multi_save_state():
        sync_compat_position()
        if not module.DATABASE_URL:
            return
        state = {
            "paper_balance": module.PAPER_BALANCE,
            "paper_position": module.paper_position,
            "paper_positions": module.paper_positions,
            "last_entry_candle": module.last_entry_candle,
            "cooldown_until": module.cooldown_until.isoformat() if module.cooldown_until else None,
        }
        try:
            with module.get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO v8fixed_state(id,state) VALUES(1,%s::jsonb)
                        ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state
                    """, (json.dumps(state),))
                conn.commit()
        except Exception as exc:
            print("MULTI SAVE STATE", repr(exc), flush=True)

    module.load_state = multi_load_state
    module.save_state = multi_save_state

    async def aggressive_strategy(symbol):
        k1, k5, bk = await asyncio.gather(
            module.get_klines(symbol, "1m"),
            module.get_klines(symbol, "5m"),
            core.book(symbol),
        )
        a1, a5 = k1[:-1], k5[:-1]
        o = [float(x[1]) for x in a1]
        h = [float(x[2]) for x in a1]
        l = [float(x[3]) for x in a1]
        c = [float(x[4]) for x in a1]
        v = [float(x[5]) for x in a1]
        o5 = [float(x[1]) for x in a5]
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

        # Stop anchor now comes from completed 5-minute candles.
        start5 = max(0, len(c5) - CANDLE_STOP_LOOKBACK)
        long_anchor_index = next((i for i in range(len(c5) - 1, start5 - 1, -1) if c5[i] > o5[i]), None)
        short_anchor_index = next((i for i in range(len(c5) - 1, start5 - 1, -1) if c5[i] < o5[i]), None)
        long_stop_anchor_low = l5[long_anchor_index] if long_anchor_index is not None else l5[-1]
        short_stop_anchor_high = h5[short_anchor_index] if short_anchor_index is not None else h5[-1]
        long_anchor_time = int(a5[long_anchor_index][0]) if long_anchor_index is not None else int(a5[-1][0])
        short_anchor_time = int(a5[short_anchor_index][0]) if short_anchor_index is not None else int(a5[-1][0])

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
            "long_stop_anchor_low": long_stop_anchor_low,
            "short_stop_anchor_high": short_stop_anchor_high,
            "long_stop_anchor_time": long_anchor_time,
            "short_stop_anchor_time": short_anchor_time,
            "stop_anchor_timeframe": "5m",
            "reason": reason,
        }

    core.strategy = aggressive_strategy
    module.strategy_analysis = aggressive_strategy

    def candidate_rank(row):
        return (
            int(row.get("score") or 0),
            int(row.get("quality_support") or 0),
            abs(float(row.get("z_momentum") or 0.0)),
            float(row.get("volume_ratio") or 0.0),
            float(row.get("adx5") or 0.0),
        )

    def multi_open_trade(a, price):
        symbol = a.get("symbol")
        if not symbol or symbol in module.paper_positions:
            return False
        if len(module.paper_positions) >= MAX_OPEN_POSITIONS or not a.get("atr"):
            return False

        params = module.SETUP_PARAMS.get(a.get("setup") or "RAPID_MOMENTUM", module.SETUP_PARAMS["RAPID_MOMENTUM"])
        baseline_dist = max(float(a["atr"]) * params["atr_mult"], price * module.MIN_STOP_RATE)
        side = a["signal"]
        entry = price * (1 + module.SLIPPAGE_RATE if side == "LONG" else 1 - module.SLIPPAGE_RATE)

        # Keep the existing take-profit calculation exactly as before, using the
        # old ATR/min-stop baseline. Only stop-loss changes to 5m candle structure.
        baseline_sl = entry - baseline_dist if side == "LONG" else entry + baseline_dist
        baseline_net_loss_per_unit = -module.estimated_net_per_unit(side, entry, baseline_sl)
        if baseline_net_loss_per_unit <= 0:
            return False
        tp = module.target_market_for_net_profit(
            side, entry, baseline_net_loss_per_unit * module.NET_RISK_REWARD
        )

        spread_buffer = price * max(float(a.get("real_spread_pct") or 0.0) * 1.5, CANDLE_STOP_BUFFER_PCT)
        if side == "LONG":
            anchor = float(a.get("long_stop_anchor_low") or (entry - baseline_dist))
            sl = anchor - spread_buffer
            anchor_time = a.get("long_stop_anchor_time")
            anchor_color = "GREEN_5M"
            if sl >= entry:
                sl = entry - baseline_dist
                anchor_time = None
                anchor_color = "FALLBACK_ATR"
        else:
            anchor = float(a.get("short_stop_anchor_high") or (entry + baseline_dist))
            sl = anchor + spread_buffer
            anchor_time = a.get("short_stop_anchor_time")
            anchor_color = "RED_5M"
            if sl <= entry:
                sl = entry + baseline_dist
                anchor_time = None
                anchor_color = "FALLBACK_ATR"

        actual_net_loss_per_unit = -module.estimated_net_per_unit(side, entry, sl)
        if actual_net_loss_per_unit <= 0:
            return False

        risk = module.PAPER_BALANCE * module.RISK_PER_TRADE
        existing_notional = sum(
            abs(float(pos.get("entry_price") or 0.0) * float(pos.get("qty") or 0.0))
            for pos in module.paper_positions.values()
        )
        total_limit = max(module.PAPER_BALANCE, 0.0) * MAX_TOTAL_NOTIONAL_SHARE
        available_notional = max(0.0, total_limit - existing_notional)
        per_position_limit = max(module.PAPER_BALANCE, 0.0) * MAX_POSITION_NOTIONAL_SHARE
        qty = min(
            risk / actual_net_loss_per_unit,
            per_position_limit / entry if entry > 0 else 0.0,
            available_notional / entry if entry > 0 else 0.0,
        )
        if qty <= 1e-12:
            module.log_signal(a, "REJECT", "MULTI_NOTIONAL_LIMIT")
            return False

        pos = {
            "symbol": symbol,
            "side": side,
            "setup": a.get("setup") or "RAPID_MOMENTUM",
            "regime": a.get("regime"),
            "score": int(a.get("score") or 0),
            "entry_price": entry,
            "qty": qty,
            "initial_qty": qty,
            "stop_loss": sl,
            "take_profit": tp,
            "risk_distance": abs(entry - sl),
            "baseline_tp_distance": baseline_dist,
            "initial_risk_usdc": qty * actual_net_loss_per_unit,
            "net_rr": module.NET_RISK_REWARD,
            "mae_r": 0.0,
            "mfe_r": 0.0,
            "breakeven_moved": False,
            "partial_taken": False,
            "partial_fraction": 0.0,
            "partial_qty": 0.0,
            "partial_exit_price": None,
            "partial_realized_gross": 0.0,
            "partial_realized_fees": 0.0,
            "partial_realized_pnl": 0.0,
            "profit_mode": False,
            "z_entry": float(a.get("z_momentum") or 0.0),
            "entry_trigger": float(a.get("entry_trigger") or price),
            "entry_spread_pct": float(a.get("real_spread_pct") or 0.0),
            "entry_book_imbalance": float(a.get("book_imbalance") or 0.5),
            "entry_volume_ratio": float(a.get("volume_ratio") or 0.0),
            "entry_kind": "MARKET_QUALITY_MULTI",
            "stop_mode": "BELOW_GREEN_5M_CANDLE" if side == "LONG" else "ABOVE_RED_5M_CANDLE",
            "stop_anchor_color": anchor_color,
            "stop_anchor_price": anchor,
            "stop_anchor_time": anchor_time,
            "stop_anchor_timeframe": "5m",
            "stop_buffer": spread_buffer,
            "scalp_target_usdc": SCALP_NET_TARGET_USDC,
            "opened_at": module.utcnow().isoformat(),
        }
        module.paper_positions[symbol] = pos
        module.last_entry_candle[symbol] = a.get("candle_time")
        sync_compat_position()
        module.save_state()
        module.log_signal(
            a,
            "ENTER",
            f"MULTI 5m-candle-stop={anchor_color} anchor={anchor:.8f} sl={sl:.8f} slot={len(module.paper_positions)}/{MAX_OPEN_POSITIONS}",
        )
        print(
            "OPEN V8 MULTI",
            symbol,
            side,
            entry,
            "SL",
            sl,
            anchor_color,
            "TP",
            tp,
            f"slots={len(module.paper_positions)}",
            flush=True,
        )
        return True

    def multi_close_trade(symbol, price, reason):
        pos = module.paper_positions.get(symbol)
        if not pos:
            return False
        entry = float(pos["entry_price"])
        qty = float(pos.get("qty") or 0.0)
        initial_qty = float(pos.get("initial_qty") or qty)
        if pos["side"] == "LONG":
            exit_exec = price * (1 - module.SLIPPAGE_RATE)
            gross = (exit_exec - entry) * qty
        else:
            exit_exec = price * (1 + module.SLIPPAGE_RATE)
            gross = (entry - exit_exec) * qty
        fees = (entry * qty + exit_exec * qty) * module.FEE_RATE
        net = gross - fees
        partial_gross = float(pos.get("partial_realized_gross") or 0.0)
        partial_fees = float(pos.get("partial_realized_fees") or 0.0)
        partial_net = float(pos.get("partial_realized_pnl") or 0.0)
        total_gross = partial_gross + gross
        total_fees = partial_fees + fees
        total_net = partial_net + net
        risk = max(float(pos.get("initial_risk_usdc") or 0.0), 1e-12)
        rr = total_net / risk
        age = (module.utcnow() - datetime.fromisoformat(pos["opened_at"])).total_seconds() / 60.0
        detail = (
            f"{reason} | R={rr:.2f} MFE={float(pos.get('mfe_r', 0)):.2f} "
            f"MAE={float(pos.get('mae_r', 0)):.2f} DUR={age:.1f}m Z={float(pos.get('z_entry', 0)):.2f}"
        )
        module.PAPER_BALANCE += net
        now = module.utcnow()
        trade = {
            **pos,
            "qty": initial_qty,
            "remaining_qty_at_final_exit": qty,
            "exit_price": exit_exec,
            "gross_pnl": total_gross,
            "fees": total_fees,
            "pnl": total_net,
            "reason": detail,
            "closed_at": now.isoformat(),
        }
        module.save_trade(trade)
        module.trade_history.insert(0, trade)
        module.trade_history = module.trade_history[:500]
        module.paper_positions.pop(symbol, None)
        module.cooldown_until = None
        sync_compat_position()
        module.save_state()
        print("CLOSE V8 MULTI", symbol, reason, total_net, f"slots={len(module.paper_positions)}", flush=True)
        return True

    async def manage_one_position(symbol):
        pos = module.paper_positions.get(symbol)
        if not pos:
            return
        price = await module.get_live_price(symbol, max_age=1.0)
        entry = float(pos["entry_price"])
        qty = float(pos.get("qty") or 0.0)
        dist = max(float(pos.get("risk_distance") or 0.0), 1e-12)
        mr = (price - entry) / dist if pos["side"] == "LONG" else (entry - price) / dist
        pos["mfe_r"] = max(float(pos.get("mfe_r", 0.0)), mr)
        pos["mae_r"] = min(float(pos.get("mae_r", 0.0)), mr)
        partial_net = float(pos.get("partial_realized_pnl") or 0.0)
        net_if_closed = partial_net + module.estimated_net_per_unit(pos["side"], entry, price) * qty
        pos["scalp_net_if_closed"] = net_if_closed
        pos["scalp_target_usdc"] = SCALP_NET_TARGET_USDC

        stop = float(pos["stop_loss"])
        if (pos["side"] == "LONG" and price <= stop) or (pos["side"] == "SHORT" and price >= stop):
            multi_close_trade(symbol, price, "MARKET STOP")
            return

        try:
            analysis = await aggressive_strategy(symbol)
        except Exception:
            analysis = None

        if net_if_closed >= SCALP_NET_TARGET_USDC:
            strong = False
            if analysis:
                same_side_score = int((analysis.get("long_score") if pos["side"] == "LONG" else analysis.get("short_score")) or 0)
                z = float(analysis.get("z_momentum") or 0.0)
                z_ok = z >= RAPID_STRONG_Z if pos["side"] == "LONG" else z <= -RAPID_STRONG_Z
                strong = bool(
                    same_side_score >= RAPID_STRONG_SCORE
                    and float(analysis.get("adx5") or 0.0) >= RAPID_STRONG_ADX
                    and float(analysis.get("volume_ratio") or 0.0) >= RAPID_STRONG_VOLUME
                    and z_ok
                )
            if not strong:
                multi_close_trade(symbol, price, "MARKET +5 NET / NO STRONG CONTINUATION")
                return
            if qty > 0:
                lock_price = module.target_market_for_net_profit(pos["side"], entry, SCALP_LOCK_NET_USDC / qty)
                if pos["side"] == "LONG":
                    pos["stop_loss"] = max(float(pos["stop_loss"]), lock_price)
                else:
                    pos["stop_loss"] = min(float(pos["stop_loss"]), lock_price)
            pos["scalp_runner"] = True

        if analysis:
            own = int((analysis.get("long_score") if pos["side"] == "LONG" else analysis.get("short_score")) or 0)
            opp = int((analysis.get("short_score") if pos["side"] == "LONG" else analysis.get("long_score")) or 0)
            opposite_signal = analysis.get("signal") == ("SHORT" if pos["side"] == "LONG" else "LONG")
            if opposite_signal and opp >= max(6, own + 2):
                multi_close_trade(symbol, price, "MARKET MOMENTUM FLIP")
                return

        tp = float(pos["take_profit"])
        if (pos["side"] == "LONG" and price >= tp) or (pos["side"] == "SHORT" and price <= tp):
            multi_close_trade(symbol, price, "MARKET TAKE PROFIT")
            return
        module.save_state()

    async def multi_manage_positions():
        for symbol in list(module.paper_positions.keys()):
            await manage_one_position(symbol)

    async def multi_cycle():
        try:
            await multi_manage_positions()
            rows = await module.analyze_all()
            open_symbols = set(module.paper_positions.keys())
            candidates = []
            for row in rows:
                if row.get("signal") not in ("LONG", "SHORT"):
                    continue
                symbol = row.get("symbol")
                if symbol in open_symbols:
                    continue
                if module.last_entry_candle.get(symbol) == row.get("candle_time"):
                    continue
                candidates.append(row)
            candidates.sort(key=candidate_rank, reverse=True)
            slots = max(0, MAX_OPEN_POSITIONS - len(module.paper_positions))
            for row in candidates[:slots]:
                price = await module.get_live_price(row["symbol"], max_age=1.0)
                if multi_open_trade(row, price):
                    open_symbols.add(row["symbol"])
            module.last_cycle_at = module.utcnow().isoformat()
            module.last_error = None
        except Exception as exc:
            module.last_error = f"{type(exc).__name__}: {exc}"
            print("V8 MULTI CYCLE", repr(exc), flush=True)
            module.last_cycle_at = module.utcnow().isoformat()

    core.open_trade = multi_open_trade
    module.open_trade = multi_open_trade
    core.manage_position = multi_manage_positions
    module.manage_position = multi_manage_positions
    module.cycle = multi_cycle

    original_analyze = module.analyze
    original_dashboard = module.dashboard
    original_startup = module.startup
    original_shutdown = module.shutdown

    async def combined_startup():
        await original_startup()
        try:
            did_reset = _reset_v8_scalp_once(module)
            print(
                f"V8_SCALP_RESET applied={did_reset} balance={module.PAPER_BALANCE:.2f} history={len(module.trade_history)} positions={len(module.paper_positions)}",
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
        position_rows = []
        total_gross = 0.0
        total_net = 0.0
        total_costs = 0.0
        for symbol in sorted(module.paper_positions.keys()):
            pos = module.paper_positions[symbol]
            row = dict(pos)
            cached = module.price_cache.get(symbol)
            gross = net = costs = 0.0
            if cached:
                px = float(cached["price"])
                entry = float(pos["entry_price"])
                qty = float(pos.get("qty") or 0.0)
                gross = ((px - entry) if pos["side"] == "LONG" else (entry - px)) * qty
                partial_net = float(pos.get("partial_realized_pnl") or 0.0)
                net = module.estimated_net_per_unit(pos["side"], entry, px) * qty + partial_net
                costs = max(gross - (net - partial_net), 0.0)
                row["current_price"] = px
            row["unrealized_gross_pnl"] = gross
            row["unrealized_net_pnl"] = net
            row["estimated_costs"] = costs
            position_rows.append(row)
            total_gross += gross
            total_net += net
            total_costs += costs

        data["positions"] = position_rows
        data["position"] = position_rows[0] if position_rows else None
        data["open_positions"] = len(position_rows)
        data["unrealized_gross_pnl"] = total_gross
        data["unrealized_pnl"] = total_net
        data["estimated_costs"] = total_costs
        data["equity"] = float(module.PAPER_BALANCE) + total_net
        data["paper_balance"] = float(module.PAPER_BALANCE)
        data["multi_position_mode"] = {
            "enabled": True,
            "max_open_positions": MAX_OPEN_POSITIONS,
            "one_position_per_symbol": True,
            "max_position_notional_share": MAX_POSITION_NOTIONAL_SHARE,
            "max_total_notional_share": MAX_TOTAL_NOTIONAL_SHARE,
        }
        data["scalp_mode"] = {
            "build": SCALP_BUILD,
            "mode": "MARKET_QUALITY_MULTI3_5M_CANDLE_STOP_NO_TIME_EXIT",
            "min_score": RAPID_MIN_SCORE,
            "scan_seconds": RAPID_LOOP_SECONDS,
            "time_exit": False,
            "stop_mode_long": "BELOW_GREEN_5M_CANDLE",
            "stop_mode_short": "ABOVE_RED_5M_CANDLE",
            "candle_stop_lookback": CANDLE_STOP_LOOKBACK,
            "stop_anchor_timeframe": "5m",
            "take_profit_logic": "UNCHANGED_BASELINE",
            "net_target_usdc_per_trade": SCALP_NET_TARGET_USDC,
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
        new = "const ps=d.positions||[]; document.getElementById('position').innerHTML=ps.length?ps.map(p=>`<div style=\"padding:8px 0;border-bottom:1px solid #29343e\"><b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)}<br><span class=\"muted\">SL: ${p.stop_mode||'původní'}${p.stop_anchor_price?' @ '+f(p.stop_anchor_price,6):''}</span><br>Čistý P/L <b class=\"${Number(p.unrealized_net_pnl)>=0?'green':'red'}\">${Number(p.unrealized_net_pnl)>=0?'+':''}${f(p.unrealized_net_pnl,2)} USDC</b> • Náklady ${f(p.estimated_costs,2)} USDC</div>`).join(''):'Žádná otevřená pozice';"
        html = html.replace(old, new)
        html = html.replace("<h2>📌 Otevřená pozice</h2>", "<h2>📌 Otevřené pozice (max 3)</h2>")
        html = html.replace("PAPER • pouze BREAKOUT • čisté R:R 1:1,3", "PAPER • MARKET QUALITY MULTI • SL podle 5m svíčky • bez time exitu • +5 USDC NET/obchod")
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