"""BTC spot strategy triggered by a new hourly volatility-contraction regime."""
from dataclasses import dataclass, replace
from math import isfinite, log, sqrt


HOUR_MS = 3_600_000


@dataclass(frozen=True)
class Config:
    short_hours: int = 168
    long_hours: int = 720
    contraction_ratio: float = 0.65
    hold_hours: int = 168
    cooldown_hours: int = 168
    position_fraction: float = 0.35
    stop: float = 0.08
    fee: float = 0.00095
    slippage: float = 0.00020
    initial_equity: float = 10_000.0


def validate(bars):
    stamps = []
    for bar in bars:
        values = [bar[key] for key in ("open", "high", "low", "close", "volume")]
        if not all(isfinite(value) for value in values):
            raise ValueError("Non-finite input")
        if not (0 < bar["low"] <= min(bar["open"], bar["close"])
                <= max(bar["open"], bar["close"]) <= bar["high"]):
            raise ValueError("Invalid OHLC")
        if bar["volume"] < 0 or bar["timestamp"] % HOUR_MS:
            raise ValueError("Invalid volume or timestamp")
        stamps.append(bar["timestamp"])
    if any(stamps[i] <= stamps[i - 1] or (stamps[i] - stamps[i - 1]) % HOUR_MS
           for i in range(1, len(stamps))):
        raise ValueError("Unordered timestamps")


def volatility_ratio(bars, completed_index, config=Config()):
    first = completed_index - config.long_hours + 1
    if first < 1:
        return None
    if bars[completed_index]["timestamp"] - bars[first - 1]["timestamp"] != config.long_hours * HOUR_MS:
        return None
    if any(bars[i]["timestamp"] - bars[i - 1]["timestamp"] != HOUR_MS
           for i in range(first, completed_index + 1)):
        return None
    returns = [log(bars[i]["close"] / bars[i - 1]["close"])
               for i in range(first, completed_index + 1)]

    def volatility(values):
        mean = sum(values) / len(values)
        return sqrt(sum((value - mean) ** 2 for value in values) / len(values))

    long_vol = volatility(returns)
    short_vol = volatility(returns[-config.short_hours:])
    return short_vol / long_vol if long_vol > 0 else None


def signal(bars, entry_index, config=Config()):
    """True only on a completed-bar crossing into the contraction regime."""
    current = volatility_ratio(bars, entry_index - 1, config)
    previous = volatility_ratio(bars, entry_index - 2, config)
    return (current is not None and previous is not None
            and current <= config.contraction_ratio < previous)


def backtest(bars, start_ts, end_ts, config=Config()):
    validate(bars)
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    position = None
    cooldown_until = 0
    trades = []

    def close_position(raw_price, timestamp, reason):
        nonlocal equity, position, cooldown_until
        fill = raw_price * (1.0 - config.slippage)
        gross = position["quantity"] * (fill - position["entry"])
        exit_fee = position["quantity"] * fill * config.fee
        equity += gross - exit_fee
        net = gross - position["entry_fee"] - exit_fee
        trades.append({"entry_ts": position["entry_ts"], "exit_ts": timestamp,
                       "entry": position["entry"], "exit": fill,
                       "stop": position["stop"], "reason": reason,
                       "gross_pnl": gross, "fees": position["entry_fee"] + exit_fee,
                       "net_pnl": net, "return_on_equity": net / position["equity_before"]})
        cooldown_until = timestamp + config.cooldown_hours * HOUR_MS
        position = None

    def mark(index):
        nonlocal peak, max_drawdown
        marked = equity
        if position:
            marked += position["quantity"] * (bars[index]["close"] - position["entry"])
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak)

    last_index = None
    for i, bar in enumerate(bars):
        timestamp = bar["timestamp"]
        if timestamp < start_ts:
            continue
        if timestamp >= end_ts:
            break
        last_index = i

        if position and bar["open"] <= position["stop"]:
            close_position(bar["open"], timestamp, "GAP_STOP")
        if position and timestamp - position["entry_ts"] >= config.hold_hours * HOUR_MS:
            close_position(bar["open"], timestamp, "TIME")

        if not position and timestamp >= cooldown_until and signal(bars, i, config):
            fill = bar["open"] * (1.0 + config.slippage)
            notional = equity * config.position_fraction
            entry_fee = notional * config.fee
            before = equity
            equity -= entry_fee
            position = {"entry_ts": timestamp, "entry": fill,
                        "quantity": notional / fill, "stop": fill * (1.0 - config.stop),
                        "entry_fee": entry_fee, "equity_before": before}

        if position and bar["low"] <= position["stop"]:
            close_position(position["stop"], timestamp, "STOP")
        mark(i)

    if last_index is not None and position:
        close_position(bars[last_index]["close"], bars[last_index]["timestamp"], "END")
        mark(last_index)
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1.0,
            "max_drawdown": max_drawdown}


def with_double_costs(config=Config()):
    return replace(config, fee=config.fee * 2.0, slippage=config.slippage * 2.0)
