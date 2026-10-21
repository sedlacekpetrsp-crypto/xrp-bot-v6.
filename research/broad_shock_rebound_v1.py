"""Offline broad-market liquidation-shock rebound research engine."""
from dataclasses import dataclass, replace
from math import isfinite


HOUR_MS = 3_600_000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")


@dataclass(frozen=True)
class Config:
    return_hours: int = 6
    volume_baseline_hours: int = 48
    shock_return: float = -0.03
    volume_multiple: float = 1.35
    min_down_assets: int = 3
    max_hold_hours: int = 18
    cooldown_hours: int = 12
    leg_stop: float = 0.06
    gross_allocation: float = 0.35
    fee: float = 0.00095
    slippage: float = 0.00020
    initial_equity: float = 10_000.0


def _median(values):
    ordered = sorted(values)
    size = len(ordered)
    middle = size // 2
    return ordered[middle] if size % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0


def validate(market):
    if set(market) != set(SYMBOLS):
        raise ValueError("The fixed four-asset universe is required")
    reference = None
    for symbol in SYMBOLS:
        stamps = []
        for bar in market[symbol]:
            values = [bar[key] for key in ("open", "high", "low", "close", "volume")]
            if not all(isfinite(value) for value in values):
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
            raise ValueError("Market timestamps are not aligned")


def signal(market, i, config=Config()):
    warmup = config.return_hours + config.volume_baseline_hours
    if i < warmup:
        return None
    returns, volume_ratios = [], []
    for symbol in SYMBOLS:
        bars = market[symbol]
        returns.append(bars[i]["close"] / bars[i - config.return_hours]["close"] - 1.0)
        recent = bars[i - config.return_hours + 1:i + 1]
        baseline = bars[i - config.return_hours - config.volume_baseline_hours + 1:
                        i - config.return_hours + 1]
        mean_recent = sum(bar["volume"] for bar in recent) / len(recent)
        mean_baseline = sum(bar["volume"] for bar in baseline) / len(baseline)
        volume_ratios.append(mean_recent / mean_baseline if mean_baseline else 0.0)
    if (_median(returns) <= config.shock_return
            and sum(value < 0 for value in returns) >= config.min_down_assets
            and _median(volume_ratios) >= config.volume_multiple):
        return {"median_return": _median(returns), "median_volume_ratio": _median(volume_ratios)}
    return None


def backtest(market, start_ts, end_ts, config=Config()):
    validate(market)
    bars = market[SYMBOLS[0]]
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    position = None
    trades = []
    next_entry_index = 0

    def mark(i):
        nonlocal peak, max_drawdown
        marked = equity
        if position:
            for symbol in SYMBOLS:
                leg = position["legs"][symbol]
                marked += leg["quantity"] * (market[symbol][i]["close"] - leg["entry"])
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak)

    def close_position(raw_prices, timestamp, reason, index):
        nonlocal equity, position, next_entry_index
        gross = 0.0
        exit_fees = 0.0
        fills = {}
        for symbol in SYMBOLS:
            leg = position["legs"][symbol]
            fill = raw_prices[symbol] * (1.0 - config.slippage)
            fills[symbol] = fill
            gross += leg["quantity"] * (fill - leg["entry"])
            exit_fees += leg["quantity"] * fill * config.fee
        net = gross - position["entry_fees"] - exit_fees
        equity += gross - exit_fees
        trades.append({"entry_index": position["entry_index"], "entry_ts": position["entry_ts"],
                       "exit_ts": timestamp, "signal": position["signal"], "exit": fills,
                       "reason": reason, "gross_pnl": gross,
                       "fees": position["entry_fees"] + exit_fees, "net_pnl": net,
                       "return_on_equity": net / position["equity_before"]})
        position = None
        next_entry_index = index + config.cooldown_hours

    for i in range(1, len(bars)):
        timestamp = bars[i]["timestamp"]
        if timestamp < start_ts:
            continue
        if timestamp >= end_ts:
            break
        closed_this_bar = False
        if position:
            gap = any(market[symbol][i]["open"] <= position["legs"][symbol]["stop"]
                      for symbol in SYMBOLS)
            if gap:
                close_position({symbol: market[symbol][i]["open"] for symbol in SYMBOLS},
                               timestamp, "GAP_STOP", i)
                closed_this_bar = True
            elif i - position["entry_index"] >= config.max_hold_hours:
                close_position({symbol: market[symbol][i]["open"] for symbol in SYMBOLS},
                               timestamp, "TIME", i)
                closed_this_bar = True

        setup = signal(market, i - 1, config)
        if not position and not closed_this_bar and i >= next_entry_index and setup:
            per_leg = equity * config.gross_allocation / len(SYMBOLS)
            legs = {}
            entry_fees = 0.0
            for symbol in SYMBOLS:
                fill = market[symbol][i]["open"] * (1.0 + config.slippage)
                legs[symbol] = {"entry": fill, "quantity": per_leg / fill,
                                "stop": fill * (1.0 - config.leg_stop)}
                entry_fees += per_leg * config.fee
            before = equity
            equity -= entry_fees
            position = {"entry_index": i, "entry_ts": timestamp, "equity_before": before,
                        "entry_fees": entry_fees, "signal": setup, "legs": legs}

        if position:
            hit = {symbol: market[symbol][i]["low"] <= position["legs"][symbol]["stop"]
                   for symbol in SYMBOLS}
            if any(hit.values()):
                prices = {symbol: (position["legs"][symbol]["stop"] if hit[symbol]
                                   else market[symbol][i]["close"]) for symbol in SYMBOLS}
                close_position(prices, timestamp, "STOP", i)
        mark(i)

    if position:
        last = max(i for i, bar in enumerate(bars) if bar["timestamp"] < end_ts)
        close_position({symbol: market[symbol][last]["close"] for symbol in SYMBOLS},
                       bars[last]["timestamp"], "END", last)
        mark(last)
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1.0,
            "max_drawdown": max_drawdown}


def with_double_costs(config=Config()):
    return replace(config, fee=config.fee * 2.0, slippage=config.slippage * 2.0)
