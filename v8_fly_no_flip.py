from datetime import datetime

import v8_fly_layer as base

NO_FLIP_BUILD = "v8-adaptive-market-quality-multi3-5m-candle-stop-no-flip-20260917-7"


def install(module):
    # Reuse the current V8 strategy, entries, 5m candle stops, dashboard and persistence.
    base.SCALP_BUILD = NO_FLIP_BUILD
    base.install(module)
    module.FLY_LAYER_BUILD = NO_FLIP_BUILD

    def close_trade(symbol, price, reason):
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
        if module.paper_positions:
            first_symbol = sorted(module.paper_positions.keys())[0]
            module.paper_position = module.paper_positions[first_symbol]
        else:
            module.paper_position = None
        module.save_state()
        print("CLOSE V8 NO-FLIP", symbol, reason, total_net, f"slots={len(module.paper_positions)}", flush=True)
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
        pos["scalp_target_usdc"] = base.SCALP_NET_TARGET_USDC
        pos["momentum_flip_exit_enabled"] = False

        stop = float(pos["stop_loss"])
        if (pos["side"] == "LONG" and price <= stop) or (pos["side"] == "SHORT" and price >= stop):
            close_trade(symbol, price, "MARKET STOP")
            return

        # Keep the existing +5 USDC net logic. A strong trend can still become a runner.
        if net_if_closed >= base.SCALP_NET_TARGET_USDC:
            strong = False
            try:
                analysis = await module.strategy_analysis(symbol)
                same_side_score = int(
                    (analysis.get("long_score") if pos["side"] == "LONG" else analysis.get("short_score")) or 0
                )
                z = float(analysis.get("z_momentum") or 0.0)
                z_ok = z >= base.RAPID_STRONG_Z if pos["side"] == "LONG" else z <= -base.RAPID_STRONG_Z
                strong = bool(
                    same_side_score >= base.RAPID_STRONG_SCORE
                    and float(analysis.get("adx5") or 0.0) >= base.RAPID_STRONG_ADX
                    and float(analysis.get("volume_ratio") or 0.0) >= base.RAPID_STRONG_VOLUME
                    and z_ok
                )
            except Exception:
                strong = False

            if not strong:
                close_trade(symbol, price, "MARKET +5 NET / NO STRONG CONTINUATION")
                return

            if qty > 0:
                lock_price = module.target_market_for_net_profit(
                    pos["side"], entry, base.SCALP_LOCK_NET_USDC / qty
                )
                if pos["side"] == "LONG":
                    pos["stop_loss"] = max(float(pos["stop_loss"]), lock_price)
                else:
                    pos["stop_loss"] = min(float(pos["stop_loss"]), lock_price)
            pos["scalp_runner"] = True

        # Intentionally NO momentum-flip exit here.
        # A LONG is not converted to SHORT and a SHORT is not converted to LONG.

        tp = float(pos["take_profit"])
        if (pos["side"] == "LONG" and price >= tp) or (pos["side"] == "SHORT" and price <= tp):
            close_trade(symbol, price, "MARKET TAKE PROFIT")
            return

        module.save_state()

    async def manage_positions():
        for symbol in list(module.paper_positions.keys()):
            await manage_one_position(symbol)

    def candidate_rank(row):
        return (
            int(row.get("score") or 0),
            int(row.get("quality_support") or 0),
            abs(float(row.get("z_momentum") or 0.0)),
            float(row.get("volume_ratio") or 0.0),
            float(row.get("adx5") or 0.0),
        )

    async def no_flip_cycle():
        try:
            await manage_positions()
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
            slots = max(0, base.MAX_OPEN_POSITIONS - len(module.paper_positions))
            for row in candidates[:slots]:
                price = await module.get_live_price(row["symbol"], max_age=1.0)
                if module.open_trade(row, price):
                    open_symbols.add(row["symbol"])

            module.last_cycle_at = module.utcnow().isoformat()
            module.last_error = None
        except Exception as exc:
            module.last_error = f"{type(exc).__name__}: {exc}"
            print("V8 NO-FLIP CYCLE", repr(exc), flush=True)
            module.last_cycle_at = module.utcnow().isoformat()

    module.close_trade = close_trade
    module.manage_position = manage_positions
    module.cycle = no_flip_cycle
