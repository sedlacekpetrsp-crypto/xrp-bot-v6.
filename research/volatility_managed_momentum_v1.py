"""Offline monthly absolute-momentum portfolio with volatility-managed weights."""
from bisect import bisect_left
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from math import isfinite, log, sqrt


HOUR_MS = 3_600_000
DAY_MS = 86_400_000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")


@dataclass(frozen=True)
class Config:
    momentum_days: int = 90
    volatility_days: int = 30
    gross_allocation: float = 0.35
    max_asset_share: float = 0.50
    leg_stop: float = 0.12
    fee: float = 0.00095
    slippage: float = 0.00020
    initial_equity: float = 10_000.0


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


def daily_market(market):
    result = {}
    for symbol in SYMBOLS:
        grouped = {}
        for bar in market[symbol]:
            day = bar["timestamp"] // DAY_MS * DAY_MS
            grouped.setdefault(day, []).append(bar)
        days = []
        for day in sorted(grouped):
            part = grouped[day]
            if [bar["timestamp"] for bar in part] != list(range(day, day + DAY_MS, HOUR_MS)):
                continue
            days.append({"timestamp": day, "open": part[0]["open"],
                         "high": max(bar["high"] for bar in part),
                         "low": min(bar["low"] for bar in part),
                         "close": part[-1]["close"]})
        result[symbol] = days
    stamps = [day["timestamp"] for day in result[SYMBOLS[0]]]
    if any([day["timestamp"] for day in result[symbol]] != stamps for symbol in SYMBOLS[1:]):
        raise ValueError("Daily markets are not aligned")
    return result


def allocation(daily, completed_day_index, config=Config()):
    i = completed_day_index
    if i < max(config.momentum_days, config.volatility_days):
        return {}
    inverse_vol = {}
    for symbol in SYMBOLS:
        days = daily[symbol]
        momentum = days[i]["close"] / days[i - config.momentum_days]["close"] - 1.0
        if momentum <= 0:
            continue
        returns = [log(days[j]["close"] / days[j - 1]["close"])
                   for j in range(i - config.volatility_days + 1, i + 1)]
        mean = sum(returns) / len(returns)
        variance = sum((value - mean) ** 2 for value in returns) / len(returns)
        if variance > 0:
            inverse_vol[symbol] = 1.0 / sqrt(variance)
    total = sum(inverse_vol.values())
    if not total:
        return {}
    return {symbol: config.gross_allocation * min(value / total, config.max_asset_share)
            for symbol, value in inverse_vol.items()}


def backtest(market, start_ts, end_ts, config=Config()):
    validate(market)
    daily = daily_market(market)
    daily_stamps = [day["timestamp"] for day in daily[SYMBOLS[0]]]
    bars = market[SYMBOLS[0]]
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    legs = {}
    trades = []

    def close_leg(symbol, raw_price, timestamp, reason):
        nonlocal equity
        leg = legs.pop(symbol)
        fill = raw_price * (1.0 - config.slippage)
        gross = leg["quantity"] * (fill - leg["entry"])
        exit_fee = leg["quantity"] * fill * config.fee
        net = gross - leg["entry_fee"] - exit_fee
        equity += gross - exit_fee
        trades.append({"symbol": symbol, "entry_ts": leg["entry_ts"], "exit_ts": timestamp,
                       "entry": leg["entry"], "exit": fill, "stop": leg["stop"],
                       "reason": reason, "gross_pnl": gross,
                       "fees": leg["entry_fee"] + exit_fee, "net_pnl": net,
                       "return_on_equity": net / leg["equity_before"]})

    def mark(i):
        nonlocal peak, max_drawdown
        marked = equity + sum(leg["quantity"] * (market[symbol][i]["close"] - leg["entry"])
                              for symbol, leg in legs.items())
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak)

    for i in range(1, len(bars)):
        timestamp = bars[i]["timestamp"]
        if timestamp < start_ts:
            continue
        if timestamp >= end_ts:
            break
        moment = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
        month_start = moment.day == 1 and moment.hour == 0
        if month_start:
            for symbol in list(legs):
                close_leg(symbol, market[symbol][i]["open"], timestamp, "REBALANCE")
            completed = bisect_left(daily_stamps, timestamp) - 1
            weights = allocation(daily, completed, config) if completed >= 0 else {}
            for symbol, weight in weights.items():
                raw = market[symbol][i]["open"]
                fill = raw * (1.0 + config.slippage)
                notional = equity * weight
                entry_fee = notional * config.fee
                before = equity
                equity -= entry_fee
                legs[symbol] = {"entry_ts": timestamp, "entry": fill,
                                "quantity": notional / fill,
                                "stop": fill * (1.0 - config.leg_stop),
                                "entry_fee": entry_fee, "equity_before": before}
        else:
            for symbol in list(legs):
                if market[symbol][i]["open"] <= legs[symbol]["stop"]:
                    close_leg(symbol, market[symbol][i]["open"], timestamp, "GAP_STOP")

        for symbol in list(legs):
            if market[symbol][i]["low"] <= legs[symbol]["stop"]:
                close_leg(symbol, legs[symbol]["stop"], timestamp, "STOP")
        mark(i)

    last = max(i for i, bar in enumerate(bars) if bar["timestamp"] < end_ts)
    for symbol in list(legs):
        close_leg(symbol, market[symbol][last]["close"], bars[last]["timestamp"], "END")
    mark(last)
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1.0,
            "max_drawdown": max_drawdown}


def with_double_costs(config=Config()):
    return replace(config, fee=config.fee * 2.0, slippage=config.slippage * 2.0)
