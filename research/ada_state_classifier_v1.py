"""Causal four-hour ADA state-classifier feature and execution engine."""
from dataclasses import dataclass, replace
from math import isfinite, log
import numpy as np

HOUR_MS = 3_600_000
BAR_MS = 4 * HOUR_MS


@dataclass(frozen=True)
class Config:
    long_probability: float = 0.60
    short_probability: float = 0.40
    stop_loss: float = 0.06
    take_profit: float = 0.08
    maximum_hold_bars: int = 6
    cooldown_bars: int = 2
    position_fraction: float = 0.20
    fee_rate: float = 0.00095
    slippage_rate: float = 0.00020
    short_borrow_annual: float = 0.08
    initial_equity: float = 10_000.0


def resample_4h(hourly):
    groups = {}
    for bar in hourly:
        bucket = bar["timestamp"] // BAR_MS * BAR_MS
        groups.setdefault(bucket, []).append(bar)
    result = []
    for stamp in sorted(groups):
        part = groups[stamp]
        if [bar["timestamp"] for bar in part] != list(range(stamp, stamp + BAR_MS, HOUR_MS)):
            continue
        result.append({"timestamp": stamp, "open": part[0]["open"], "high": max(b["high"] for b in part),
                       "low": min(b["low"] for b in part), "close": part[-1]["close"],
                       "quote_volume": sum(b["quote_volume"] for b in part)})
    return result


def validate(bars):
    stamps = []
    for bar in bars:
        values = [bar[k] for k in ("open", "high", "low", "close", "quote_volume")]
        if not all(isfinite(value) for value in values): raise ValueError("Non-finite input")
        if not (0 < bar["low"] <= min(bar["open"], bar["close"]) <= max(bar["open"], bar["close"]) <= bar["high"]):
            raise ValueError("Invalid OHLC")
        if bar["quote_volume"] < 0 or bar["timestamp"] % BAR_MS: raise ValueError("Invalid timestamp or volume")
        stamps.append(bar["timestamp"])
    if any(stamps[i] <= stamps[i - 1] for i in range(1, len(stamps))): raise ValueError("Unordered bars")


def feature_at(bars, index):
    if index < 30 or bars[index]["timestamp"] - bars[index - 30]["timestamp"] != 30 * BAR_MS: return None
    closes = np.array([bar["close"] for bar in bars[index - 30:index + 1]], dtype=float)
    log_returns = np.diff(np.log(closes))
    recent = bars[index - 5:index + 1]; baseline = bars[index - 23:index - 5]
    baseline_volume = np.mean([bar["quote_volume"] for bar in baseline])
    if baseline_volume <= 0: return None
    return np.array([log(closes[-1] / closes[-7]), log(closes[-1] / closes[-19]),
                     float(np.std(log_returns[-18:], ddof=0)),
                     max(bar["high"] for bar in recent) / min(bar["low"] for bar in recent) - 1,
                     np.mean([bar["quote_volume"] for bar in recent]) / baseline_volume - 1,
                     closes[-1] / np.mean(closes[-30:]) - 1], dtype=float)


def backtest(bars, scores, start_ts, end_ts, config=Config()):
    validate(bars); equity = config.initial_equity; peak = equity; max_drawdown = 0.0
    position = None; trades = []; cooldown_until = start_ts; last_bar = None

    def close(raw, timestamp, reason):
        nonlocal equity, position, cooldown_until
        side = position["side"]; fill = raw * (1 - config.slippage_rate * side)
        gross = side * position["quantity"] * (fill - position["entry"])
        exit_fee = position["quantity"] * fill * config.fee_rate
        hours = max(0, (timestamp - position["entry_ts"]) / HOUR_MS)
        borrow = position["notional"] * config.short_borrow_annual * hours / (365 * 24) if side == -1 else 0.0
        equity += gross - exit_fee - borrow
        net = gross - position["entry_fee"] - exit_fee - borrow
        trades.append({"entry_ts": position["entry_ts"], "exit_ts": timestamp, "side": side,
                       "entry": position["entry"], "exit": fill, "score": position["score"],
                       "reason": reason, "gross_pnl": gross, "fees": position["entry_fee"] + exit_fee,
                       "borrow": borrow, "net_pnl": net, "return_on_equity": net / position["equity_before"]})
        position = None; cooldown_until = timestamp + config.cooldown_bars * BAR_MS

    for i, bar in enumerate(bars):
        ts = bar["timestamp"]
        if ts < start_ts: continue
        if ts >= end_ts: break
        last_bar = bar
        if position:
            if position["side"] == 1:
                if bar["open"] <= position["stop"]: close(bar["open"], ts, "GAP_STOP")
                elif bar["open"] >= position["target"]: close(position["target"], ts, "GAP_TARGET")
            else:
                if bar["open"] >= position["stop"]: close(bar["open"], ts, "GAP_STOP")
                elif bar["open"] <= position["target"]: close(position["target"], ts, "GAP_TARGET")
        if position and ts - position["entry_ts"] >= config.maximum_hold_bars * BAR_MS: close(bar["open"], ts, "TIME")
        if position:
            stop_hit = bar["low"] <= position["stop"] if position["side"] == 1 else bar["high"] >= position["stop"]
            target_hit = bar["high"] >= position["target"] if position["side"] == 1 else bar["low"] <= position["target"]
            if stop_hit: close(position["stop"], ts, "STOP")
            elif target_hit: close(position["target"], ts, "TARGET")
        if not position and ts >= cooldown_until and i > 0 and ts - bars[i - 1]["timestamp"] == BAR_MS:
            score = scores.get(bars[i - 1]["timestamp"]); side = 1 if score is not None and score >= config.long_probability else (-1 if score is not None and score <= config.short_probability else 0)
            if side:
                fill = bar["open"] * (1 + config.slippage_rate * side); notional = equity * config.position_fraction
                fee = notional * config.fee_rate; before = equity; equity -= fee
                position = {"entry_ts": ts, "side": side, "entry": fill, "quantity": notional / fill,
                            "notional": notional, "stop": fill * (1 - side * config.stop_loss),
                            "target": fill * (1 + side * config.take_profit), "entry_fee": fee,
                            "score": score, "equity_before": before}
                stop_hit = bar["low"] <= position["stop"] if side == 1 else bar["high"] >= position["stop"]
                target_hit = bar["high"] >= position["target"] if side == 1 else bar["low"] <= position["target"]
                if stop_hit: close(position["stop"], ts, "STOP")
                elif position and target_hit: close(position["target"], ts, "TARGET")
        marked = equity + (position["side"] * position["quantity"] * (bar["close"] - position["entry"]) if position else 0)
        peak = max(peak, marked); max_drawdown = max(max_drawdown, (peak - marked) / peak)
    if position and last_bar: close(last_bar["close"], last_bar["timestamp"], "END")
    return {"trades": trades, "ending_equity": equity, "net_return": equity / config.initial_equity - 1,
            "max_drawdown": max_drawdown}


def with_cost_stress(config=Config()):
    return replace(config, fee_rate=config.fee_rate * 2, slippage_rate=config.slippage_rate * 2,
                   short_borrow_annual=config.short_borrow_annual * 2)
