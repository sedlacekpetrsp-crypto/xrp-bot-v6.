"""Offline, long-only cross-sectional crypto rotation research engine.

Signals use only completed UTC daily candles assembled from aligned 15-minute
spot bars.  Orders are simulated at the next 15-minute open.  This module has
no exchange client and cannot submit orders.
"""
from dataclasses import dataclass, replace
from math import isfinite


DAY_MS = 86_400_000


@dataclass(frozen=True)
class Config:
    momentum_days: int = 21
    regime_ema_days: int = 60
    atr_days: int = 20
    stop_atr: float = 3.0
    allocation: float = 0.35
    fee: float = 0.00095
    slippage: float = 0.00020
    initial_equity: float = 10_000.0


def validate_market(market):
    if "BTCUSDT" not in market or len(market) < 2:
        raise ValueError("BTCUSDT and at least one peer are required")
    reference = None
    for symbol, bars in market.items():
        stamps = []
        for bar in bars:
            vals = [bar[k] for k in ("open", "high", "low", "close", "volume")]
            if not all(isfinite(v) for v in vals):
                raise ValueError(f"Non-finite input for {symbol}")
            if not (0 < bar["low"] <= min(bar["open"], bar["close"])
                    <= max(bar["open"], bar["close"]) <= bar["high"]):
                raise ValueError(f"Invalid OHLC for {symbol}")
            if bar["volume"] < 0:
                raise ValueError(f"Invalid volume for {symbol}")
            stamps.append(bar["timestamp"])
        if any(stamps[i] - stamps[i - 1] != 900_000 for i in range(1, len(stamps))):
            raise ValueError(f"Gap or duplicate for {symbol}")
        if reference is None:
            reference = stamps
        elif stamps != reference:
            raise ValueError("Markets are not timestamp-aligned")


def _daily(market):
    result = {}
    for symbol, bars in market.items():
        days = []
        for start in range(0, len(bars), 96):
            part = bars[start:start + 96]
            if len(part) != 96 or part[0]["timestamp"] % DAY_MS:
                continue
            if part[-1]["timestamp"] != part[0]["timestamp"] + 95 * 900_000:
                continue
            days.append({
                "timestamp": part[0]["timestamp"],
                "open": part[0]["open"],
                "high": max(x["high"] for x in part),
                "low": min(x["low"] for x in part),
                "close": part[-1]["close"],
            })
        result[symbol] = days
    stamps = [x["timestamp"] for x in next(iter(result.values()))]
    if any([x["timestamp"] for x in days] != stamps for days in result.values()):
        raise ValueError("Daily markets are not aligned")
    return result


def _ema(values, length):
    alpha = 2.0 / (length + 1.0)
    value = values[0]
    for item in values[1:]:
        value += alpha * (item - value)
    return value


def desired_symbol(daily, completed_day_index, config=Config()):
    """Return the desired asset using data through completed_day_index only."""
    i = completed_day_index
    warmup = max(config.regime_ema_days, config.momentum_days, config.atr_days)
    if i < warmup:
        return None
    btc = daily["BTCUSDT"]
    closes = [x["close"] for x in btc[i - config.regime_ema_days + 1:i + 1]]
    if btc[i]["close"] <= _ema(closes, config.regime_ema_days):
        return None
    scores = {}
    for symbol, days in daily.items():
        old = days[i - config.momentum_days]["close"]
        scores[symbol] = days[i]["close"] / old - 1.0
    winner = max(scores, key=lambda symbol: (scores[symbol], symbol))
    return winner if scores[winner] > 0 else None


def _atr(days, i, length):
    ranges = []
    for j in range(i - length + 1, i + 1):
        prev = days[j - 1]["close"]
        ranges.append(max(days[j]["high"] - days[j]["low"],
                          abs(days[j]["high"] - prev),
                          abs(days[j]["low"] - prev)))
    return sum(ranges) / len(ranges)


def backtest(market, start_ts, end_ts, config=Config()):
    """Simulate one shared account; end_ts is exclusive."""
    validate_market(market)
    daily = _daily(market)
    stamps = [x["timestamp"] for x in next(iter(daily.values()))]
    bars_by_symbol = {s: {b["timestamp"]: b for b in bars} for s, bars in market.items()}
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    position = None
    trades = []
    curve = []

    def close_position(raw_price, timestamp, reason):
        nonlocal equity, position
        fill = raw_price * (1.0 - config.slippage)
        gross = position["quantity"] * (fill - position["entry"])
        exit_fee = position["quantity"] * fill * config.fee
        net = gross - position["entry_fee"] - exit_fee
        equity += gross - exit_fee
        trades.append({**position, "exit_ts": timestamp, "exit": fill, "reason": reason,
                       "gross_pnl": gross, "fees": position["entry_fee"] + exit_fee,
                       "net_pnl": net, "return_on_equity": net / position["equity_before"]})
        position = None

    for day_i in range(1, len(stamps)):
        day_start = stamps[day_i]
        if day_start < start_ts:
            continue
        if day_start >= end_ts:
            break
        wanted = desired_symbol(daily, day_i - 1, config)
        if position and position["symbol"] != wanted:
            close_position(bars_by_symbol[position["symbol"]][day_start]["open"], day_start, "ROTATE")
        if not position and wanted:
            raw_entry = bars_by_symbol[wanted][day_start]["open"]
            entry = raw_entry * (1.0 + config.slippage)
            notional = equity * config.allocation
            quantity = notional / entry
            entry_fee = notional * config.fee
            atr = _atr(daily[wanted], day_i - 1, config.atr_days)
            stop = entry - config.stop_atr * atr
            if stop > 0 and entry_fee < equity:
                equity -= entry_fee
                position = {"symbol": wanted, "entry_ts": day_start, "entry": entry,
                            "quantity": quantity, "entry_fee": entry_fee, "stop": stop,
                            "equity_before": equity + entry_fee}

        if position:
            for offset in range(96):
                ts = day_start + offset * 900_000
                bar = bars_by_symbol[position["symbol"]].get(ts)
                if bar is None or ts >= end_ts:
                    break
                if bar["open"] <= position["stop"]:
                    close_position(bar["open"], ts, "GAP_STOP")
                    break
                if bar["low"] <= position["stop"]:
                    close_position(position["stop"], ts, "STOP")
                    break

        marked = equity
        if position:
            close_bar = bars_by_symbol[position["symbol"]][day_start + 95 * 900_000]
            marked += position["quantity"] * (close_bar["close"] - position["entry"])
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak)
        curve.append({"timestamp": day_start, "equity": marked})

    if position:
        last_ts = min(end_ts - 900_000, stamps[-1] + 95 * 900_000)
        bar = bars_by_symbol[position["symbol"]][last_ts]
        close_position(bar["close"], last_ts, "END")
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1.0,
            "max_drawdown": max_drawdown, "equity_curve": curve}


def with_double_costs(config=Config()):
    return replace(config, fee=config.fee * 2.0, slippage=config.slippage * 2.0)
