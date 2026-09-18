from datetime import datetime, timedelta

import v8_fly_layer as base

PROFIT_BUILD = "v8-profit-expectancy-r-20260918-1"

# Entry quality: stop taking low-volume / wrong-momentum trades just because
# the score can be assembled from weaker components.
LONG_MIN_SCORE = 7
SHORT_MIN_SCORE = 8
LONG_MIN_VOLUME = 0.60
SHORT_MIN_VOLUME = 0.80
LONG_MIN_Z = 0.10
SHORT_MAX_Z = -0.25
SHORT_MAX_BOOK = 0.49
SHORT_MIN_ADX = 18.0

# Risk/reward is now based on the *actual* 5m candle stop, not the old ATR
# baseline. This keeps the displayed/real R multiple aligned.
TARGET_NET_R = 1.30
MIN_STOP_RATE = 0.0025
MAX_STOP_RATE = 0.0060

# Profit protection. There is deliberately no time exit.
BREAKEVEN_TRIGGER_R = 0.55
BREAKEVEN_LOCK_R = 0.05
PROFIT_DECISION_R = 0.80
RUNNER_LOCK_R = 0.35
STRONG_SCORE = 8
STRONG_ADX = 20.0
STRONG_VOLUME = 0.80
STRONG_Z = 0.50

STOP_REENTRY_COOLDOWN_MIN = 5
symbol_cooldown_until = {}


def patch(module):
    module.FLY_LAYER_BUILD = PROFIT_BUILD
    module.NET_RISK_REWARD = TARGET_NET_R
    module.MIN_STOP_RATE = MIN_STOP_RATE
    module.MAX_STOP_RATE = MAX_STOP_RATE

    original_strategy = module.strategy_analysis
    original_close = module.close_trade

    def sync_compat_position():
        if module.paper_positions:
            first_symbol = sorted(module.paper_positions.keys())[0]
            module.paper_position = module.paper_positions[first_symbol]
        else:
            module.paper_position = None

    async def profit_strategy(symbol):
        row = await original_strategy(symbol)
        side = row.get("signal")
        if side not in ("LONG", "SHORT"):
            return row

        score = int(row.get("score") or 0)
        volume = float(row.get("volume_ratio") or 0.0)
        z = float(row.get("z_momentum") or 0.0)
        book = float(row.get("book_imbalance") or 0.5)
        adx = float(row.get("adx5") or 0.0)
        regime = row.get("regime")

        reject = None
        if side == "LONG":
            if score < LONG_MIN_SCORE:
                reject = f"LONG_SCORE_{score}_LT_{LONG_MIN_SCORE}"
            elif volume < LONG_MIN_VOLUME:
                reject = f"LONG_VOLUME_{volume:.2f}_LT_{LONG_MIN_VOLUME:.2f}"
            elif z < LONG_MIN_Z:
                reject = f"LONG_Z_{z:.2f}_LT_{LONG_MIN_Z:.2f}"
        else:
            if score < SHORT_MIN_SCORE:
                reject = f"SHORT_SCORE_{score}_LT_{SHORT_MIN_SCORE}"
            elif regime != "FAST_SHORT":
                reject = "SHORT_5M_NOT_ALIGNED"
            elif volume < SHORT_MIN_VOLUME:
                reject = f"SHORT_VOLUME_{volume:.2f}_LT_{SHORT_MIN_VOLUME:.2f}"
            elif z > SHORT_MAX_Z:
                reject = f"SHORT_Z_{z:.2f}_GT_{SHORT_MAX_Z:.2f}"
            elif book > SHORT_MAX_BOOK:
                reject = f"SHORT_BOOK_{book:.3f}_GT_{SHORT_MAX_BOOK:.3f}"
            elif adx < SHORT_MIN_ADX:
                reject = f"SHORT_ADX_{adx:.1f}_LT_{SHORT_MIN_ADX:.1f}"

        if reject:
            row["pre_profit_signal"] = side
            row["signal"] = "WAIT"
            row["profit_filter_reason"] = reject
            row["reason"] = f"{row.get('reason', '')} PROFIT_FILTER={reject}".strip()
        else:
            row["profit_filter_reason"] = None
        return row

    module.strategy_analysis = profit_strategy

    def profit_open_trade(a, price):
        symbol = a.get("symbol")
        if not symbol or symbol in module.paper_positions:
            return False
        if len(module.paper_positions) >= base.MAX_OPEN_POSITIONS or not a.get("atr"):
            return False
        if a.get("signal") not in ("LONG", "SHORT"):
            return False

        until = symbol_cooldown_until.get(symbol)
        if until and module.utcnow() < until:
            module.log_signal(a, "REJECT", f"STOP_COOLDOWN_UNTIL_{until.isoformat()}")
            return False

        side = a["signal"]
        entry = price * (1 + module.SLIPPAGE_RATE if side == "LONG" else 1 - module.SLIPPAGE_RATE)
        spread_buffer = price * max(
            float(a.get("real_spread_pct") or 0.0) * 1.5,
            base.CANDLE_STOP_BUFFER_PCT,
        )

        if side == "LONG":
            anchor = float(a.get("long_stop_anchor_low") or entry * (1 - MIN_STOP_RATE))
            sl = anchor - spread_buffer
            anchor_time = a.get("long_stop_anchor_time")
            anchor_color = "GREEN_5M"
            raw_dist = entry - sl
        else:
            anchor = float(a.get("short_stop_anchor_high") or entry * (1 + MIN_STOP_RATE))
            sl = anchor + spread_buffer
            anchor_time = a.get("short_stop_anchor_time")
            anchor_color = "RED_5M"
            raw_dist = sl - entry

        if raw_dist <= 0:
            module.log_signal(a, "REJECT", "INVALID_5M_STOP")
            return False

        stop_rate = raw_dist / entry
        if stop_rate > MAX_STOP_RATE:
            module.log_signal(a, "REJECT", f"5M_STOP_TOO_WIDE_{stop_rate*100:.3f}PCT")
            return False

        # If the candle stop is too tight for costs/noise, widen it while
        # preserving the same structural side of the candle.
        if stop_rate < MIN_STOP_RATE:
            raw_dist = entry * MIN_STOP_RATE
            sl = entry - raw_dist if side == "LONG" else entry + raw_dist
            stop_rate = MIN_STOP_RATE
            anchor_color += "_MINWIDTH"

        net_loss_per_unit = -module.estimated_net_per_unit(side, entry, sl)
        if net_loss_per_unit <= 0:
            module.log_signal(a, "REJECT", "NON_POSITIVE_NET_RISK")
            return False

        risk_budget = module.PAPER_BALANCE * module.RISK_PER_TRADE
        existing_notional = sum(
            abs(float(pos.get("entry_price") or 0.0) * float(pos.get("qty") or 0.0))
            for pos in module.paper_positions.values()
        )
        total_limit = max(module.PAPER_BALANCE, 0.0) * base.MAX_TOTAL_NOTIONAL_SHARE
        available_notional = max(0.0, total_limit - existing_notional)
        per_position_limit = max(module.PAPER_BALANCE, 0.0) * base.MAX_POSITION_NOTIONAL_SHARE
        qty = min(
            risk_budget / net_loss_per_unit,
            per_position_limit / entry if entry > 0 else 0.0,
            available_notional / entry if entry > 0 else 0.0,
        )
        if qty <= 1e-12:
            module.log_signal(a, "REJECT", "NOTIONAL_LIMIT")
            return False

        initial_risk_usdc = qty * net_loss_per_unit
        target_net_per_unit = net_loss_per_unit * TARGET_NET_R
        tp = module.target_market_for_net_profit(side, entry, target_net_per_unit)

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
            "initial_risk_usdc": initial_risk_usdc,
            "net_rr": TARGET_NET_R,
            "mae_r": 0.0,
            "mfe_r": 0.0,
            "breakeven_moved": False,
            "profit_lock_stage": "NONE",
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
            "entry_kind": "PROFIT_QUALITY_R",
            "stop_mode": "BELOW_GREEN_5M_CANDLE" if side == "LONG" else "ABOVE_RED_5M_CANDLE",
            "stop_anchor_color": anchor_color,
            "stop_anchor_price": anchor,
            "stop_anchor_time": anchor_time,
            "stop_anchor_timeframe": "5m",
            "stop_buffer": spread_buffer,
            "stop_rate": stop_rate,
            "profit_decision_r": PROFIT_DECISION_R,
            "target_net_r": TARGET_NET_R,
            "opened_at": module.utcnow().isoformat(),
        }

        module.paper_positions[symbol] = pos
        module.last_entry_candle[symbol] = a.get("candle_time")
        sync_compat_position()
        module.save_state()
        module.log_signal(
            a,
            "ENTER",
            (
                f"PROFIT_R stop={stop_rate*100:.3f}% target={TARGET_NET_R:.2f}R "
                f"vol={float(a.get('volume_ratio') or 0):.2f} z={float(a.get('z_momentum') or 0):.2f}"
            ),
        )
        print(
            "OPEN V8 PROFIT",
            symbol,
            side,
            f"entry={entry:.8f}",
            f"sl={sl:.8f}",
            f"tp={tp:.8f}",
            f"risk={initial_risk_usdc:.2f}",
            flush=True,
        )
        return True

    module.open_trade = profit_open_trade

    def close_with_cooldown(symbol, price, reason):
        ok = original_close(symbol, price, reason)
        if ok and "STOP" in reason:
            symbol_cooldown_until[symbol] = module.utcnow() + timedelta(minutes=STOP_REENTRY_COOLDOWN_MIN)
        return ok

    async def manage_one(symbol):
        pos = module.paper_positions.get(symbol)
        if not pos:
            return

        price = await module.get_live_price(symbol, max_age=1.0)
        entry = float(pos["entry_price"])
        qty = float(pos.get("qty") or 0.0)
        risk_usdc = max(float(pos.get("initial_risk_usdc") or 0.0), 1e-12)
        dist = max(float(pos.get("risk_distance") or abs(entry - float(pos["stop_loss"]))), 1e-12)

        mr = (price - entry) / dist if pos["side"] == "LONG" else (entry - price) / dist
        pos["mfe_r"] = max(float(pos.get("mfe_r", 0.0)), mr)
        pos["mae_r"] = min(float(pos.get("mae_r", 0.0)), mr)

        partial_net = float(pos.get("partial_realized_pnl") or 0.0)
        net_if_closed = partial_net + module.estimated_net_per_unit(pos["side"], entry, price) * qty
        net_r = net_if_closed / risk_usdc
        pos["net_r_if_closed"] = net_r

        stop = float(pos["stop_loss"])
        if (pos["side"] == "LONG" and price <= stop) or (pos["side"] == "SHORT" and price >= stop):
            close_with_cooldown(symbol, price, "MARKET STOP")
            return

        tp = float(pos["take_profit"])
        if (pos["side"] == "LONG" and price >= tp) or (pos["side"] == "SHORT" and price <= tp):
            original_close(symbol, price, "MARKET TAKE PROFIT")
            return

        # Once a trade has earned enough to cover costs and prove direction,
        # do not allow a full -1R reversal.
        if net_r >= BREAKEVEN_TRIGGER_R and pos.get("profit_lock_stage") == "NONE" and qty > 0:
            lock_per_unit = (risk_usdc * BREAKEVEN_LOCK_R) / qty
            lock_price = module.target_market_for_net_profit(pos["side"], entry, lock_per_unit)
            if pos["side"] == "LONG":
                pos["stop_loss"] = max(float(pos["stop_loss"]), lock_price)
            else:
                pos["stop_loss"] = min(float(pos["stop_loss"]), lock_price)
            pos["profit_lock_stage"] = "BREAKEVEN_PLUS"
            pos["breakeven_moved"] = True

        if net_r >= PROFIT_DECISION_R:
            strong = False
            analysis = None
            try:
                analysis = await profit_strategy(symbol)
            except Exception:
                analysis = None

            if analysis and analysis.get("signal") == pos["side"]:
                same_score = int(
                    (analysis.get("long_score") if pos["side"] == "LONG" else analysis.get("short_score")) or 0
                )
                z = float(analysis.get("z_momentum") or 0.0)
                z_ok = z >= STRONG_Z if pos["side"] == "LONG" else z <= -STRONG_Z
                strong = bool(
                    same_score >= STRONG_SCORE
                    and float(analysis.get("adx5") or 0.0) >= STRONG_ADX
                    and float(analysis.get("volume_ratio") or 0.0) >= STRONG_VOLUME
                    and z_ok
                )

            if not strong:
                original_close(symbol, price, "MARKET PROFIT LOCK / NO STRONG CONTINUATION")
                return

            if qty > 0:
                lock_per_unit = (risk_usdc * RUNNER_LOCK_R) / qty
                lock_price = module.target_market_for_net_profit(pos["side"], entry, lock_per_unit)
                if pos["side"] == "LONG":
                    pos["stop_loss"] = max(float(pos["stop_loss"]), lock_price)
                else:
                    pos["stop_loss"] = min(float(pos["stop_loss"]), lock_price)
                pos["profit_lock_stage"] = "RUNNER"
                pos["scalp_runner"] = True

        module.save_state()

    async def manage_positions():
        for symbol in list(module.paper_positions.keys()):
            await manage_one(symbol)

    def candidate_rank(row):
        return (
            int(row.get("score") or 0),
            int(row.get("quality_support") or 0),
            abs(float(row.get("z_momentum") or 0.0)),
            float(row.get("volume_ratio") or 0.0),
            float(row.get("adx5") or 0.0),
        )

    async def profit_cycle():
        try:
            await manage_positions()
            rows = await module.analyze_all()
            open_symbols = set(module.paper_positions.keys())
            candidates = []

            for row in rows:
                if row.get("signal") not in ("LONG", "SHORT"):
                    if row.get("profit_filter_reason"):
                        try:
                            module.log_signal(row, "REJECT", row["profit_filter_reason"])
                        except Exception:
                            pass
                    continue
                symbol = row.get("symbol")
                if symbol in open_symbols:
                    continue
                until = symbol_cooldown_until.get(symbol)
                if until and module.utcnow() < until:
                    continue
                if module.last_entry_candle.get(symbol) == row.get("candle_time"):
                    continue
                candidates.append(row)

            candidates.sort(key=candidate_rank, reverse=True)
            slots = max(0, base.MAX_OPEN_POSITIONS - len(module.paper_positions))
            for row in candidates[:slots]:
                price = await module.get_live_price(row["symbol"], max_age=1.0)
                if module.open_trade(row, price):
                    open_symbols.add(row["symbol"])

            module.last_cycle_at = module.utcnow().isoformat()
            module.last_error = None
        except Exception as exc:
            module.last_error = f"{type(exc).__name__}: {exc}"
            print("V8 PROFIT CYCLE", repr(exc), flush=True)
            module.last_cycle_at = module.utcnow().isoformat()

    module.manage_position = manage_positions
    module.cycle = profit_cycle

    print(
        "V8_PROFIT_PATCH_APPLIED",
        PROFIT_BUILD,
        f"target={TARGET_NET_R}R",
        f"profit_decision={PROFIT_DECISION_R}R",
        f"stop={MIN_STOP_RATE*100:.2f}-{MAX_STOP_RATE*100:.2f}%",
        flush=True,
    )
