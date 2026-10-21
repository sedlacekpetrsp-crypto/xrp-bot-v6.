"""Offline SOL/ETH market-neutral pairs research; never submits orders."""
from dataclasses import dataclass, replace
from math import isfinite, log, sqrt


HOUR_MS = 3_600_000


@dataclass(frozen=True)
class Config:
    lookback_hours: int = 720
    entry_z: float = 2.25
    exit_z: float = 0.40
    spread_stop_z: float = 4.0
    max_hold_hours: int = 336
    leg_stop: float = 0.12
    gross_allocation: float = 0.35
    fee: float = 0.00095
    slippage: float = 0.00020
    short_borrow_annual: float = 0.08
    initial_equity: float = 10_000.0


def validate(market):
    if set(market) != {"SOLUSDT", "ETHUSDT"}:
        raise ValueError("Exactly SOLUSDT and ETHUSDT are required")
    reference = None
    for symbol, bars in market.items():
        stamps = []
        for bar in bars:
            values = [bar[k] for k in ("open", "high", "low", "close", "volume")]
            if not all(isfinite(x) for x in values):
                raise ValueError(f"Non-finite input for {symbol}")
            if not (0 < bar["low"] <= min(bar["open"], bar["close"])
                    <= max(bar["open"], bar["close"]) <= bar["high"]):
                raise ValueError(f"Invalid OHLC for {symbol}")
            if bar["volume"] < 0 or bar["timestamp"] % HOUR_MS:
                raise ValueError(f"Invalid volume or timestamp for {symbol}")
            stamps.append(bar["timestamp"])
        if any(stamps[i] <= stamps[i - 1] or (stamps[i] - stamps[i - 1]) % HOUR_MS
               for i in range(1, len(stamps))):
            raise ValueError(f"Unordered timestamps for {symbol}")
        if reference is None:
            reference = stamps
        elif stamps != reference:
            raise ValueError("Pair timestamps are not aligned")


def ratio_series(market):
    return [log(sol["close"] / eth["close"])
            for sol, eth in zip(market["SOLUSDT"], market["ETHUSDT"])]


def zscore(ratios, i, config=Config()):
    if i < config.lookback_hours - 1:
        return None
    window = ratios[i - config.lookback_hours + 1:i + 1]
    mean = sum(window) / len(window)
    variance = sum((x - mean) ** 2 for x in window) / len(window)
    if variance <= 0:
        return None
    return (ratios[i] - mean) / sqrt(variance)


def _entry_fill(raw, side, config):
    return raw * (1.0 + config.slippage if side > 0 else 1.0 - config.slippage)


def _exit_fill(raw, side, config):
    return raw * (1.0 - config.slippage if side > 0 else 1.0 + config.slippage)


def backtest(market, start_ts, end_ts, config=Config()):
    validate(market)
    sol = market["SOLUSDT"]
    eth = market["ETHUSDT"]
    ratios = ratio_series(market)
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    position = None
    trades = []

    def mark(prices):
        nonlocal peak, max_drawdown
        marked = equity
        if position:
            for symbol in ("SOLUSDT", "ETHUSDT"):
                leg = position["legs"][symbol]
                marked += leg["side"] * leg["quantity"] * (prices[symbol] - leg["entry"])
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak)

    def close_position(raw_prices, timestamp, reason):
        nonlocal equity, position
        gross = 0.0
        exit_fees = 0.0
        fills = {}
        for symbol, raw in raw_prices.items():
            leg = position["legs"][symbol]
            fill = _exit_fill(raw, leg["side"], config)
            fills[symbol] = fill
            gross += leg["side"] * leg["quantity"] * (fill - leg["entry"])
            exit_fees += leg["quantity"] * fill * config.fee
        net = gross - position["entry_fees"] - exit_fees - position["borrow_cost"]
        equity += gross - exit_fees
        trades.append({"entry_index": position["entry_index"], "entry_ts": position["entry_ts"],
                       "exit_ts": timestamp, "side_sol": position["legs"]["SOLUSDT"]["side"],
                       "entry_z": position["entry_z"], "exit": fills, "reason": reason,
                       "gross_pnl": gross, "fees": position["entry_fees"] + exit_fees,
                       "borrow_cost": position["borrow_cost"], "net_pnl": net,
                       "return_on_equity": net / position["equity_before"]})
        position = None

    for i in range(1, len(sol)):
        timestamp = sol[i]["timestamp"]
        if timestamp < start_ts:
            continue
        if timestamp >= end_ts:
            break
        z = zscore(ratios, i - 1, config)
        closed_this_bar = False

        if position:
            gap = False
            for symbol, bar in (("SOLUSDT", sol[i]), ("ETHUSDT", eth[i])):
                leg = position["legs"][symbol]
                if (leg["side"] > 0 and bar["open"] <= leg["stop"]) or (
                        leg["side"] < 0 and bar["open"] >= leg["stop"]):
                    gap = True
            if gap:
                close_position({"SOLUSDT": sol[i]["open"], "ETHUSDT": eth[i]["open"]},
                               timestamp, "GAP_STOP")
                closed_this_bar = True
            elif z is not None and (abs(z) <= config.exit_z or abs(z) >= config.spread_stop_z
                                    or i - position["entry_index"] >= config.max_hold_hours):
                reason = "MEAN" if abs(z) <= config.exit_z else (
                    "SPREAD_STOP" if abs(z) >= config.spread_stop_z else "TIME")
                close_position({"SOLUSDT": sol[i]["open"], "ETHUSDT": eth[i]["open"]},
                               timestamp, reason)
                closed_this_bar = True

        if not position and not closed_this_bar and z is not None and abs(z) >= config.entry_z:
            side_sol = -1 if z > 0 else 1
            sides = {"SOLUSDT": side_sol, "ETHUSDT": -side_sol}
            per_leg = equity * config.gross_allocation / 2.0
            legs = {}
            entry_fees = 0.0
            for symbol, bar in (("SOLUSDT", sol[i]), ("ETHUSDT", eth[i])):
                fill = _entry_fill(bar["open"], sides[symbol], config)
                quantity = per_leg / fill
                stop = fill * (1.0 - config.leg_stop if sides[symbol] > 0
                               else 1.0 + config.leg_stop)
                legs[symbol] = {"side": sides[symbol], "entry": fill,
                                "quantity": quantity, "stop": stop}
                entry_fees += per_leg * config.fee
            before = equity
            equity -= entry_fees
            position = {"entry_index": i, "entry_ts": timestamp, "entry_z": z,
                        "equity_before": before, "entry_fees": entry_fees,
                        "borrow_cost": 0.0, "legs": legs}

        if position:
            intrabar = {}
            for symbol, bar in (("SOLUSDT", sol[i]), ("ETHUSDT", eth[i])):
                leg = position["legs"][symbol]
                hit = (leg["side"] > 0 and bar["low"] <= leg["stop"]) or (
                    leg["side"] < 0 and bar["high"] >= leg["stop"])
                intrabar[symbol] = hit
            if any(intrabar.values()):
                prices = {}
                for symbol, bar in (("SOLUSDT", sol[i]), ("ETHUSDT", eth[i])):
                    prices[symbol] = position["legs"][symbol]["stop"] if intrabar[symbol] else bar["close"]
                close_position(prices, timestamp, "STOP")
                closed_this_bar = True

        if position:
            short_symbol = next(s for s, leg in position["legs"].items() if leg["side"] < 0)
            short_price = sol[i]["close"] if short_symbol == "SOLUSDT" else eth[i]["close"]
            borrow = (position["legs"][short_symbol]["quantity"] * short_price
                      * config.short_borrow_annual / (365.0 * 24.0))
            position["borrow_cost"] += borrow
            equity -= borrow
        mark({"SOLUSDT": sol[i]["close"], "ETHUSDT": eth[i]["close"]})

    if position:
        last = max(i for i, bar in enumerate(sol) if bar["timestamp"] < end_ts)
        close_position({"SOLUSDT": sol[last]["close"], "ETHUSDT": eth[last]["close"]},
                       sol[last]["timestamp"], "END")
        mark({"SOLUSDT": sol[last]["close"], "ETHUSDT": eth[last]["close"]})
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1.0,
            "max_drawdown": max_drawdown}


def with_double_costs(config=Config()):
    return replace(config, fee=config.fee * 2.0, slippage=config.slippage * 2.0,
                   short_borrow_annual=config.short_borrow_annual * 2.0)
