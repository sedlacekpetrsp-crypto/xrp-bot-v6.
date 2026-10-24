"""Causal long-only BNB volume-dry-up reversal backtest."""
from dataclasses import dataclass, replace
from math import isfinite

HOUR_MS = 3_600_000


@dataclass(frozen=True)
class Config:
    return_lookback_hours: int = 48
    recent_volume_hours: int = 6
    baseline_volume_hours: int = 48
    maximum_return: float = -0.03
    maximum_volume_ratio: float = 0.70
    stop_loss: float = 0.04
    take_profit: float = 0.06
    maximum_hold_hours: int = 36
    cooldown_hours: int = 24
    position_fraction: float = 0.25
    fee_rate: float = 0.00095
    slippage_rate: float = 0.00020
    initial_equity: float = 10_000.0


def validate(bars):
    stamps = []
    for bar in bars:
        values = [bar[k] for k in ("open", "high", "low", "close", "quote_volume")]
        if not all(isfinite(v) for v in values):
            raise ValueError("Non-finite input")
        if not (0 < bar["low"] <= min(bar["open"], bar["close"]) <= max(bar["open"], bar["close"]) <= bar["high"]):
            raise ValueError("Invalid OHLC")
        if bar["quote_volume"] < 0 or bar["timestamp"] % HOUR_MS:
            raise ValueError("Invalid timestamp or volume")
        stamps.append(bar["timestamp"])
    if any(stamps[i] <= stamps[i - 1] for i in range(1, len(stamps))):
        raise ValueError("Unordered timestamps")


def signal(bars, completed, config=Config()):
    """Use only candles at or before completed; return None across any hourly gap."""
    first = completed - config.recent_volume_hours - config.baseline_volume_hours + 1
    return_first = completed - config.return_lookback_hours
    if min(first, return_first) < 0:
        return None
    start = min(first, return_first)
    if bars[completed]["timestamp"] - bars[start]["timestamp"] != (completed - start) * HOUR_MS:
        return None
    price_return = bars[completed]["close"] / bars[return_first]["close"] - 1
    recent_first = completed - config.recent_volume_hours + 1
    baseline = bars[first:recent_first]
    recent = bars[recent_first:completed + 1]
    baseline_mean = sum(b["quote_volume"] for b in baseline) / len(baseline)
    recent_mean = sum(b["quote_volume"] for b in recent) / len(recent)
    volume_ratio = recent_mean / baseline_mean if baseline_mean > 0 else float("inf")
    if price_return > config.maximum_return or volume_ratio > config.maximum_volume_ratio:
        return None
    return {"price_return": price_return, "volume_ratio": volume_ratio}


def backtest(bars, start_ts, end_ts, config=Config()):
    validate(bars)
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    position = None
    trades = []
    cooldown_until = start_ts
    last_bar = None

    def close(raw_price, timestamp, reason):
        nonlocal equity, position, cooldown_until
        fill = raw_price * (1 - config.slippage_rate)
        gross = position["quantity"] * (fill - position["entry"])
        exit_fee = position["quantity"] * fill * config.fee_rate
        equity += gross - exit_fee
        net = gross - position["entry_fee"] - exit_fee
        trades.append({
            "entry_ts": position["entry_ts"], "exit_ts": timestamp,
            "entry": position["entry"], "exit": fill, "stop": position["stop"],
            "target": position["target"], "reason": reason,
            "signal_return": position["signal_return"],
            "volume_ratio": position["volume_ratio"], "gross_pnl": gross,
            "fees": position["entry_fee"] + exit_fee, "net_pnl": net,
            "return_on_equity": net / position["equity_before"],
        })
        position = None
        cooldown_until = timestamp + config.cooldown_hours * HOUR_MS

    for i, bar in enumerate(bars):
        ts = bar["timestamp"]
        if ts < start_ts:
            continue
        if ts >= end_ts:
            break
        last_bar = bar
        if position:
            if bar["open"] <= position["stop"]:
                close(bar["open"], ts, "GAP_STOP")
            elif bar["open"] >= position["target"]:
                close(position["target"], ts, "GAP_TARGET")
        if position and ts - position["entry_ts"] >= config.maximum_hold_hours * HOUR_MS:
            close(bar["open"], ts, "TIME")
        if position:
            # Unknown intrabar ordering is resolved against the strategy.
            if bar["low"] <= position["stop"]:
                close(position["stop"], ts, "STOP")
            elif bar["high"] >= position["target"]:
                close(position["target"], ts, "TARGET")
        if not position and ts >= cooldown_until and i > 0:
            setup = signal(bars, i - 1, config)
            if setup and bar["timestamp"] - bars[i - 1]["timestamp"] == HOUR_MS:
                fill = bar["open"] * (1 + config.slippage_rate)
                notional = equity * config.position_fraction
                fee = notional * config.fee_rate
                before = equity
                equity -= fee
                position = {
                    "entry_ts": ts, "entry": fill, "quantity": notional / fill,
                    "stop": fill * (1 - config.stop_loss),
                    "target": fill * (1 + config.take_profit),
                    "entry_fee": fee, "equity_before": before,
                    "signal_return": setup["price_return"],
                    "volume_ratio": setup["volume_ratio"],
                }
                if bar["low"] <= position["stop"]:
                    close(position["stop"], ts, "STOP")
                elif position and bar["high"] >= position["target"]:
                    close(position["target"], ts, "TARGET")
        marked = equity + (position["quantity"] * (bar["close"] - position["entry"]) if position else 0)
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak)
    if position and last_bar:
        close(last_bar["close"], last_bar["timestamp"], "END")
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1, "max_drawdown": max_drawdown}


def with_double_costs(config=Config()):
    return replace(config, fee_rate=config.fee_rate * 2, slippage_rate=config.slippage_rate * 2)
