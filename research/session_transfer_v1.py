"""Causal BTC session-to-session continuation backtest."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from math import isfinite


HOUR_MS = 3_600_000


@dataclass(frozen=True)
class Config:
    signal_hours: int = 8
    entry_hour: int = 8
    threshold: float = 0.0075
    hold_hours: int = 8
    position_fraction: float = 0.20
    stop: float = 0.025
    target: float = 0.025
    fee: float = 0.00095
    slippage: float = 0.00020
    annual_borrow: float = 0.08
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


def signal(bars, entry_index, config=Config()):
    """Return LONG/SHORT from the completed 00:00-07:59 UTC session."""
    if entry_index < config.signal_hours:
        return None
    timestamp = bars[entry_index]["timestamp"]
    moment = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
    first = entry_index - config.signal_hours
    if moment.hour != config.entry_hour:
        return None
    if (bars[first]["timestamp"] != timestamp - config.signal_hours * HOUR_MS
            or bars[entry_index - 1]["timestamp"] != timestamp - HOUR_MS):
        return None
    if any(bars[j]["timestamp"] - bars[j - 1]["timestamp"] != HOUR_MS
           for j in range(first + 1, entry_index)):
        return None
    session_return = bars[entry_index - 1]["close"] / bars[first]["open"] - 1.0
    if session_return >= config.threshold:
        return "LONG"
    if session_return <= -config.threshold:
        return "SHORT"
    return None


def backtest(bars, start_ts, end_ts, config=Config()):
    validate(bars)
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    position = None
    trades = []

    def close_position(raw_price, timestamp, reason):
        nonlocal equity, position
        adverse = 1.0 - config.slippage if position["side"] == "LONG" else 1.0 + config.slippage
        fill = raw_price * adverse
        direction = 1.0 if position["side"] == "LONG" else -1.0
        gross = position["quantity"] * direction * (fill - position["entry"])
        exit_fee = position["quantity"] * fill * config.fee
        equity += gross - exit_fee
        net = gross - position["entry_fee"] - exit_fee - position["borrow_cost"]
        trades.append({"side": position["side"], "entry_ts": position["entry_ts"],
                       "exit_ts": timestamp, "entry": position["entry"], "exit": fill,
                       "stop": position["stop"], "target": position["target"],
                       "reason": reason, "gross_pnl": gross,
                       "fees": position["entry_fee"] + exit_fee,
                       "borrow_cost": position["borrow_cost"], "net_pnl": net,
                       "return_on_equity": net / position["equity_before"]})
        position = None

    def mark(index):
        nonlocal peak, max_drawdown
        marked = equity
        if position:
            direction = 1.0 if position["side"] == "LONG" else -1.0
            marked += position["quantity"] * direction * (bars[index]["close"] - position["entry"])
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

        if position:
            if position["side"] == "LONG":
                if bar["open"] <= position["stop"]:
                    close_position(bar["open"], timestamp, "GAP_STOP")
                elif bar["open"] >= position["target"]:
                    close_position(position["target"], timestamp, "GAP_TARGET")
            else:
                if bar["open"] >= position["stop"]:
                    close_position(bar["open"], timestamp, "GAP_STOP")
                elif bar["open"] <= position["target"]:
                    close_position(position["target"], timestamp, "GAP_TARGET")
        if position and timestamp - position["entry_ts"] >= config.hold_hours * HOUR_MS:
            close_position(bar["open"], timestamp, "TIME")

        side = signal(bars, i, config) if not position else None
        if side:
            adverse = 1.0 + config.slippage if side == "LONG" else 1.0 - config.slippage
            fill = bar["open"] * adverse
            notional = equity * config.position_fraction
            entry_fee = notional * config.fee
            before = equity
            equity -= entry_fee
            position = {"side": side, "entry_ts": timestamp, "entry": fill,
                        "quantity": notional / fill,
                        "stop": fill * (1.0 - config.stop if side == "LONG" else 1.0 + config.stop),
                        "target": fill * (1.0 + config.target if side == "LONG" else 1.0 - config.target),
                        "entry_fee": entry_fee, "borrow_cost": 0.0,
                        "equity_before": before}

        if position:
            stop_hit = (bar["low"] <= position["stop"] if position["side"] == "LONG"
                        else bar["high"] >= position["stop"])
            target_hit = (bar["high"] >= position["target"] if position["side"] == "LONG"
                          else bar["low"] <= position["target"])
            if stop_hit:
                close_position(position["stop"], timestamp, "STOP")
            elif target_hit:
                close_position(position["target"], timestamp, "TARGET")

        if position and position["side"] == "SHORT":
            charge = position["quantity"] * bar["close"] * config.annual_borrow / (365.0 * 24.0)
            equity -= charge
            position["borrow_cost"] += charge
        mark(i)

    if last_index is not None and position:
        close_position(bars[last_index]["close"], bars[last_index]["timestamp"], "END")
        mark(last_index)
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1.0,
            "max_drawdown": max_drawdown}


def with_double_costs(config=Config()):
    return replace(config, fee=config.fee * 2.0, slippage=config.slippage * 2.0,
                   annual_borrow=config.annual_borrow * 2.0)
