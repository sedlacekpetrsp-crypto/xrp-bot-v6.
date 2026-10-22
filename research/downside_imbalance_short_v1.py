"""Causal multi-asset hourly downside-imbalance short backtest."""
from dataclasses import dataclass, replace
from math import isfinite, log


HOUR_MS = 3_600_000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")


@dataclass(frozen=True)
class Config:
    lookback_hours: int = 24
    energy_ratio: float = 2.5
    minimum_negative_hours: int = 8
    maximum_lookback_return: float = -0.02
    maximum_close_location: float = 0.25
    stop: float = 0.035
    target: float = 0.04
    maximum_hold_hours: int = 8
    cooldown_hours: int = 12
    max_positions: int = 2
    position_fraction: float = 0.175
    fee: float = 0.00095
    slippage: float = 0.00020
    annual_borrow: float = 0.08
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
        if any(stamps[i] <= stamps[i - 1] or stamps[i] - stamps[i - 1] != HOUR_MS
               for i in range(1, len(stamps))):
            raise ValueError(f"Missing or unordered bars for {symbol}")
        if reference is None:
            reference = stamps
        elif stamps != reference:
            raise ValueError("Market timestamps are not aligned")


def signal(bars, completed_index, config=Config()):
    """Return signal strength using completed bars only, else None."""
    first = completed_index - config.lookback_hours + 1
    if first < 1:
        return None
    part = bars[first:completed_index + 1]
    returns = [log(bars[i]["close"] / bars[i - 1]["close"])
               for i in range(first, completed_index + 1)]
    downside = sum(value * value for value in returns if value < 0)
    upside = sum(value * value for value in returns if value > 0)
    ratio = downside / max(upside, 1e-12)
    lookback_return = bars[completed_index]["close"] / bars[first - 1]["close"] - 1.0
    high = max(bar["high"] for bar in part)
    low = min(bar["low"] for bar in part)
    location = ((bars[completed_index]["close"] - low) / (high - low)
                if high > low else 1.0)
    if (ratio >= config.energy_ratio
            and sum(value < 0 for value in returns) >= config.minimum_negative_hours
            and lookback_return <= config.maximum_lookback_return
            and location <= config.maximum_close_location):
        return ratio
    return None


def backtest(market, start_ts, end_ts, config=Config()):
    validate(market)
    bars = market[SYMBOLS[0]]
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    positions = {}
    cooldown_until = {}
    trades = []

    def close_position(symbol, raw_price, timestamp, reason):
        nonlocal equity
        position = positions.pop(symbol)
        fill = raw_price * (1.0 + config.slippage)
        gross = position["quantity"] * (position["entry"] - fill)
        exit_fee = position["quantity"] * fill * config.fee
        equity += gross - exit_fee
        net = gross - position["entry_fee"] - exit_fee - position["borrow_cost"]
        trades.append({"symbol": symbol, "entry_ts": position["entry_ts"],
                       "exit_ts": timestamp, "entry": position["entry"], "exit": fill,
                       "stop": position["stop"], "target": position["target"],
                       "reason": reason, "gross_pnl": gross,
                       "fees": position["entry_fee"] + exit_fee,
                       "borrow_cost": position["borrow_cost"], "net_pnl": net,
                       "return_on_equity": net / position["equity_before"]})
        cooldown_until[symbol] = timestamp + config.cooldown_hours * HOUR_MS

    def mark(index):
        nonlocal peak, max_drawdown
        marked = equity + sum(position["quantity"] *
                              (position["entry"] - market[symbol][index]["close"])
                              for symbol, position in positions.items())
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak)

    last_index = None
    for i in range(1, len(bars)):
        timestamp = bars[i]["timestamp"]
        if timestamp < start_ts:
            continue
        if timestamp >= end_ts:
            break
        last_index = i

        # Existing positions see the current open before any new signals are entered.
        for symbol in list(positions):
            bar = market[symbol][i]
            position = positions[symbol]
            if bar["open"] >= position["stop"]:
                close_position(symbol, bar["open"], timestamp, "GAP_STOP")
            elif bar["open"] <= position["target"]:
                close_position(symbol, position["target"], timestamp, "GAP_TARGET")
            elif i - position["entry_index"] >= config.maximum_hold_hours:
                close_position(symbol, bar["open"], timestamp, "TIME")

        # Signals are computed through i-1 and filled at bar i open.
        slots = config.max_positions - len(positions)
        candidates = []
        if slots > 0:
            for symbol in SYMBOLS:
                if symbol in positions or timestamp < cooldown_until.get(symbol, 0):
                    continue
                strength = signal(market[symbol], i - 1, config)
                if strength is not None:
                    candidates.append((strength, symbol))
        for _, symbol in sorted(candidates, reverse=True)[:slots]:
            raw = market[symbol][i]["open"]
            fill = raw * (1.0 - config.slippage)
            notional = equity * config.position_fraction
            entry_fee = notional * config.fee
            before = equity
            equity -= entry_fee
            positions[symbol] = {"entry_ts": timestamp, "entry_index": i,
                                 "entry": fill, "quantity": notional / fill,
                                 "stop": fill * (1.0 + config.stop),
                                 "target": fill * (1.0 - config.target),
                                 "entry_fee": entry_fee, "borrow_cost": 0.0,
                                 "equity_before": before}

        # Stop wins same-bar ambiguity. A newly opened trade may exit this bar.
        for symbol in list(positions):
            bar = market[symbol][i]
            position = positions[symbol]
            if bar["high"] >= position["stop"]:
                close_position(symbol, position["stop"], timestamp, "STOP")
            elif bar["low"] <= position["target"]:
                close_position(symbol, position["target"], timestamp, "TARGET")

        hourly_borrow = config.annual_borrow / (365.0 * 24.0)
        for symbol, position in positions.items():
            charge = position["quantity"] * market[symbol][i]["close"] * hourly_borrow
            equity -= charge
            position["borrow_cost"] += charge
        mark(i)

    if last_index is not None:
        timestamp = bars[last_index]["timestamp"]
        for symbol in list(positions):
            close_position(symbol, market[symbol][last_index]["close"], timestamp, "END")
        mark(last_index)
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1.0,
            "max_drawdown": max_drawdown}


def with_double_costs(config=Config()):
    return replace(config, fee=config.fee * 2.0, slippage=config.slippage * 2.0,
                   annual_borrow=config.annual_borrow * 2.0)
