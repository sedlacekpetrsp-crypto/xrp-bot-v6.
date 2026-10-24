"""Causal ETH perpetual funding-extreme reversal backtest."""
from dataclasses import dataclass, replace
from math import isfinite

HOUR_MS = 3_600_000


@dataclass(frozen=True)
class Config:
    minimum_absolute_funding: float = 0.00020
    stop_loss: float = 0.05
    take_profit: float = 0.03
    maximum_hold_hours: int = 24
    cooldown_hours: int = 8
    position_fraction: float = 0.20
    fee_rate: float = 0.00050
    slippage_rate: float = 0.00020
    funding_credit_multiplier: float = 1.0
    funding_debit_multiplier: float = 1.0
    initial_equity: float = 10_000.0


def validate(bars, funding):
    stamps = []
    for bar in bars:
        values = [bar[k] for k in ("open", "high", "low", "close")]
        if not all(isfinite(v) for v in values):
            raise ValueError("Non-finite OHLC")
        if not (0 < bar["low"] <= min(bar["open"], bar["close"]) <= max(bar["open"], bar["close"]) <= bar["high"]):
            raise ValueError("Invalid OHLC")
        if bar["timestamp"] % HOUR_MS:
            raise ValueError("Invalid timestamp")
        stamps.append(bar["timestamp"])
    if any(stamps[i] <= stamps[i - 1] for i in range(1, len(stamps))):
        raise ValueError("Unordered bars")
    if any(ts % HOUR_MS or not isfinite(rate) for ts, rate in funding.items()):
        raise ValueError("Invalid funding")


def funding_signal(rate, config=Config()):
    if abs(rate) < config.minimum_absolute_funding:
        return None
    return -1 if rate > 0 else 1


def backtest(bars, funding, start_ts, end_ts, config=Config()):
    validate(bars, funding)
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    position = None
    trades = []
    cooldown_until = start_ts
    last_bar = None

    def close(raw_price, timestamp, reason):
        nonlocal equity, position, cooldown_until
        side = position["side"]
        fill = raw_price * (1 - config.slippage_rate * side)
        price_pnl = side * position["quantity"] * (fill - position["entry"])
        exit_fee = position["quantity"] * fill * config.fee_rate
        equity += price_pnl - exit_fee
        net = price_pnl + position["funding_pnl"] - position["entry_fee"] - exit_fee
        trades.append({
            "entry_ts": position["entry_ts"], "exit_ts": timestamp, "side": side,
            "entry": position["entry"], "exit": fill, "stop": position["stop"],
            "target": position["target"], "reason": reason,
            "signal_funding_rate": position["signal_funding_rate"],
            "price_pnl": price_pnl, "funding_pnl": position["funding_pnl"],
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
        if position and ts in funding and ts > position["entry_ts"]:
            cashflow = -position["side"] * position["notional"] * funding[ts]
            multiplier = config.funding_credit_multiplier if cashflow >= 0 else config.funding_debit_multiplier
            cashflow *= multiplier
            equity += cashflow
            position["funding_pnl"] += cashflow
        if position:
            if position["side"] == 1:
                if bar["open"] <= position["stop"]:
                    close(bar["open"], ts, "GAP_STOP")
                elif bar["open"] >= position["target"]:
                    close(position["target"], ts, "GAP_TARGET")
            else:
                if bar["open"] >= position["stop"]:
                    close(bar["open"], ts, "GAP_STOP")
                elif bar["open"] <= position["target"]:
                    close(position["target"], ts, "GAP_TARGET")
        if position and ts - position["entry_ts"] >= config.maximum_hold_hours * HOUR_MS:
            close(bar["open"], ts, "TIME")
        if position:
            stop_hit = bar["low"] <= position["stop"] if position["side"] == 1 else bar["high"] >= position["stop"]
            target_hit = bar["high"] >= position["target"] if position["side"] == 1 else bar["low"] <= position["target"]
            if stop_hit:
                close(position["stop"], ts, "STOP")
            elif target_hit:
                close(position["target"], ts, "TARGET")
        if not position and ts >= cooldown_until and i > 0 and ts - bars[i - 1]["timestamp"] == HOUR_MS:
            rate = funding.get(bars[i - 1]["timestamp"])
            side = funding_signal(rate, config) if rate is not None else None
            if side:
                fill = bar["open"] * (1 + config.slippage_rate * side)
                notional = equity * config.position_fraction
                entry_fee = notional * config.fee_rate
                before = equity
                equity -= entry_fee
                position = {
                    "entry_ts": ts, "side": side, "entry": fill, "quantity": notional / fill,
                    "notional": notional, "stop": fill * (1 - side * config.stop_loss),
                    "target": fill * (1 + side * config.take_profit), "entry_fee": entry_fee,
                    "funding_pnl": 0.0, "signal_funding_rate": rate, "equity_before": before,
                }
                stop_hit = bar["low"] <= position["stop"] if side == 1 else bar["high"] >= position["stop"]
                target_hit = bar["high"] >= position["target"] if side == 1 else bar["low"] <= position["target"]
                if stop_hit:
                    close(position["stop"], ts, "STOP")
                elif position and target_hit:
                    close(position["target"], ts, "TARGET")
        marked = equity + (position["side"] * position["quantity"] * (bar["close"] - position["entry"]) if position else 0)
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak)
    if position and last_bar:
        close(last_bar["close"], last_bar["timestamp"], "END")
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1, "max_drawdown": max_drawdown}


def with_cost_stress(config=Config()):
    return replace(config, fee_rate=config.fee_rate * 2, slippage_rate=config.slippage_rate * 2,
                   funding_credit_multiplier=0.5, funding_debit_multiplier=2.0)
