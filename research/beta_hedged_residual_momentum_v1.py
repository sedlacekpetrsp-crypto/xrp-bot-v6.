"""Beta-hedged altcoin residual-momentum research backtest."""
from bisect import bisect_left
from dataclasses import dataclass, replace
from math import isfinite, log


HOUR_MS = 3_600_000
DAY_MS = 86_400_000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
ALTS = SYMBOLS[1:]


@dataclass(frozen=True)
class Config:
    beta_days: int = 60
    residual_days: int = 10
    residual_threshold: float = 0.05
    minimum_beta: float = 0.25
    maximum_beta: float = 2.50
    hold_hours: int = 240
    cooldown_hours: int = 120
    gross_allocation: float = 0.35
    leg_stop: float = 0.10
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


def pair_signal(daily, completed_index, config=Config()):
    first = completed_index - config.beta_days + 1
    if first < 1:
        return None
    btc = daily["BTCUSDT"]
    if btc[completed_index]["timestamp"] - btc[first - 1]["timestamp"] != config.beta_days * DAY_MS:
        return None
    btc_returns = [log(btc[i]["close"] / btc[i - 1]["close"])
                   for i in range(first, completed_index + 1)]
    btc_mean = sum(btc_returns) / len(btc_returns)
    btc_variance = sum((value - btc_mean) ** 2 for value in btc_returns)
    if btc_variance <= 0:
        return None
    candidates = []
    for symbol in ALTS:
        alt = daily[symbol]
        alt_returns = [log(alt[i]["close"] / alt[i - 1]["close"])
                       for i in range(first, completed_index + 1)]
        alt_mean = sum(alt_returns) / len(alt_returns)
        beta = sum((a - alt_mean) * (b - btc_mean)
                   for a, b in zip(alt_returns, btc_returns)) / btc_variance
        beta = max(config.minimum_beta, min(config.maximum_beta, beta))
        residual = (sum(alt_returns[-config.residual_days:])
                    - beta * sum(btc_returns[-config.residual_days:]))
        if abs(residual) >= config.residual_threshold:
            candidates.append((abs(residual), symbol,
                               "ALT_LONG" if residual > 0 else "ALT_SHORT", beta, residual))
    return max(candidates) if candidates else None


def backtest(market, start_ts, end_ts, config=Config()):
    validate(market)
    daily = daily_market(market)
    daily_stamps = [day["timestamp"] for day in daily["BTCUSDT"]]
    bars = market["BTCUSDT"]
    equity = config.initial_equity
    peak = equity
    max_drawdown = 0.0
    position = None
    cooldown_until = 0
    trades = []

    def fill_price(raw, side, entering):
        buy = (side == "LONG") == entering
        return raw * (1.0 + config.slippage if buy else 1.0 - config.slippage)

    def close_position(raw_prices, timestamp, reason):
        nonlocal equity, position, cooldown_until
        gross = 0.0
        exit_fees = 0.0
        exits = {}
        for symbol, leg in position["legs"].items():
            fill = fill_price(raw_prices[symbol], leg["side"], False)
            direction = 1.0 if leg["side"] == "LONG" else -1.0
            gross += leg["quantity"] * direction * (fill - leg["entry"])
            exit_fees += leg["quantity"] * fill * config.fee
            exits[symbol] = fill
        equity += gross - exit_fees
        fees = position["entry_fees"] + exit_fees
        net = gross - fees - position["borrow_cost"]
        trades.append({"alt": position["alt"], "direction": position["direction"],
                       "beta": position["beta"], "residual": position["residual"],
                       "entry_ts": position["entry_ts"], "exit_ts": timestamp,
                       "reason": reason, "entries": {s: l["entry"] for s, l in position["legs"].items()},
                       "exits": exits, "gross_pnl": gross, "fees": fees,
                       "borrow_cost": position["borrow_cost"], "net_pnl": net,
                       "return_on_equity": net / position["equity_before"]})
        cooldown_until = timestamp + config.cooldown_hours * HOUR_MS
        position = None

    def mark(index):
        nonlocal peak, max_drawdown
        marked = equity
        if position:
            for symbol, leg in position["legs"].items():
                direction = 1.0 if leg["side"] == "LONG" else -1.0
                marked += leg["quantity"] * direction * (market[symbol][index]["close"] - leg["entry"])
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
            gap = any((market[symbol][i]["open"] <= leg["stop"] if leg["side"] == "LONG"
                       else market[symbol][i]["open"] >= leg["stop"])
                      for symbol, leg in position["legs"].items())
            if gap:
                close_position({s: market[s][i]["open"] for s in position["legs"]}, timestamp, "GAP_STOP")
        if position and timestamp - position["entry_ts"] >= config.hold_hours * HOUR_MS:
            close_position({s: market[s][i]["open"] for s in position["legs"]}, timestamp, "TIME")

        if not position and timestamp >= cooldown_until and timestamp % DAY_MS == 0:
            completed = bisect_left(daily_stamps, timestamp) - 1
            setup = pair_signal(daily, completed, config) if completed >= 0 else None
            if setup:
                _, alt, direction, beta, residual = setup
                alt_side = "LONG" if direction == "ALT_LONG" else "SHORT"
                btc_side = "SHORT" if alt_side == "LONG" else "LONG"
                alt_fraction = config.gross_allocation / (1.0 + beta)
                fractions = {alt: alt_fraction, "BTCUSDT": alt_fraction * beta}
                sides = {alt: alt_side, "BTCUSDT": btc_side}
                legs, entry_fees = {}, 0.0
                before = equity
                for symbol in (alt, "BTCUSDT"):
                    fill = fill_price(market[symbol][i]["open"], sides[symbol], True)
                    notional = equity * fractions[symbol]
                    fee = notional * config.fee
                    entry_fees += fee
                    legs[symbol] = {"side": sides[symbol], "entry": fill,
                                    "quantity": notional / fill,
                                    "stop": fill * (1.0 - config.leg_stop if sides[symbol] == "LONG"
                                                    else 1.0 + config.leg_stop)}
                equity -= entry_fees
                position = {"alt": alt, "direction": direction, "beta": beta,
                            "residual": residual, "entry_ts": timestamp, "legs": legs,
                            "entry_fees": entry_fees, "borrow_cost": 0.0,
                            "equity_before": before}

        if position:
            triggered = [symbol for symbol, leg in position["legs"].items()
                         if (market[symbol][i]["low"] <= leg["stop"] if leg["side"] == "LONG"
                             else market[symbol][i]["high"] >= leg["stop"])]
            if triggered:
                raw = {}
                for symbol, leg in position["legs"].items():
                    if symbol in triggered:
                        raw[symbol] = leg["stop"]
                    else:
                        raw[symbol] = (market[symbol][i]["low"] if leg["side"] == "LONG"
                                       else market[symbol][i]["high"])
                close_position(raw, timestamp, "STOP")

        if position:
            hourly = config.annual_borrow / (365.0 * 24.0)
            for symbol, leg in position["legs"].items():
                if leg["side"] == "SHORT":
                    charge = leg["quantity"] * market[symbol][i]["close"] * hourly
                    equity -= charge
                    position["borrow_cost"] += charge
        mark(i)

    if last_index is not None and position:
        close_position({s: market[s][last_index]["close"] for s in position["legs"]},
                       bars[last_index]["timestamp"], "END")
        mark(last_index)
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1.0,
            "max_drawdown": max_drawdown}


def with_double_costs(config=Config()):
    return replace(config, fee=config.fee * 2.0, slippage=config.slippage * 2.0,
                   annual_borrow=config.annual_borrow * 2.0)
