"""Causal, calendar-only weekend carry portfolio backtest."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from math import isfinite


HOUR_MS = 3_600_000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")


@dataclass(frozen=True)
class Config:
    entry_weekday: int = 5  # Saturday, UTC
    entry_hour: int = 0
    hold_hours: int = 48
    gross_allocation: float = 0.35
    leg_stop: float = 0.06
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


def is_entry_time(timestamp, config=Config()):
    moment = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
    return moment.weekday() == config.entry_weekday and moment.hour == config.entry_hour


def backtest(market, start_ts, end_ts, config=Config()):
    validate(market)
    bars = market[SYMBOLS[0]]
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    positions = {}
    basket_entry_ts = None
    trades = []

    def close_leg(symbol, raw_price, timestamp, reason):
        nonlocal equity
        leg = positions.pop(symbol)
        fill = raw_price * (1.0 - config.slippage)
        gross = leg["quantity"] * (fill - leg["entry"])
        exit_fee = leg["quantity"] * fill * config.fee
        equity += gross - exit_fee
        net = gross - leg["entry_fee"] - exit_fee
        trades.append({"symbol": symbol, "entry_ts": leg["entry_ts"],
                       "exit_ts": timestamp, "entry": leg["entry"], "exit": fill,
                       "stop": leg["stop"], "reason": reason, "gross_pnl": gross,
                       "fees": leg["entry_fee"] + exit_fee, "net_pnl": net,
                       "return_on_equity": net / leg["equity_before"]})

    def mark(index):
        nonlocal peak, max_drawdown
        marked = equity + sum(leg["quantity"] *
                              (market[symbol][index]["close"] - leg["entry"])
                              for symbol, leg in positions.items())
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak)

    last_index = None
    for i, reference_bar in enumerate(bars):
        timestamp = reference_bar["timestamp"]
        if timestamp < start_ts:
            continue
        if timestamp >= end_ts:
            break
        last_index = i

        for symbol in list(positions):
            leg = positions[symbol]
            if market[symbol][i]["open"] <= leg["stop"]:
                close_leg(symbol, market[symbol][i]["open"], timestamp, "GAP_STOP")
        if positions and timestamp - basket_entry_ts >= config.hold_hours * HOUR_MS:
            for symbol in list(positions):
                close_leg(symbol, market[symbol][i]["open"], timestamp, "TIME")
        if not positions:
            basket_entry_ts = None

        if not positions and is_entry_time(timestamp, config):
            basket_entry_ts = timestamp
            per_leg_fraction = config.gross_allocation / len(SYMBOLS)
            for symbol in SYMBOLS:
                raw = market[symbol][i]["open"]
                fill = raw * (1.0 + config.slippage)
                notional = equity * per_leg_fraction
                entry_fee = notional * config.fee
                before = equity
                equity -= entry_fee
                positions[symbol] = {"entry_ts": timestamp, "entry": fill,
                                     "quantity": notional / fill,
                                     "stop": fill * (1.0 - config.leg_stop),
                                     "entry_fee": entry_fee, "equity_before": before}

        for symbol in list(positions):
            if market[symbol][i]["low"] <= positions[symbol]["stop"]:
                close_leg(symbol, positions[symbol]["stop"], timestamp, "STOP")
        if not positions:
            basket_entry_ts = None
        mark(i)

    if last_index is not None:
        timestamp = bars[last_index]["timestamp"]
        for symbol in list(positions):
            close_leg(symbol, market[symbol][last_index]["close"], timestamp, "END")
        mark(last_index)
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1.0,
            "max_drawdown": max_drawdown}


def with_double_costs(config=Config()):
    return replace(config, fee=config.fee * 2.0, slippage=config.slippage * 2.0)
