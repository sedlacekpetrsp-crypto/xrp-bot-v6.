"""Isolated PAPER spot portfolio. No network, credentials, or live order execution."""
from datetime import datetime, timezone

FEE = 0.00095
SLIPPAGE = 0.00020
STOP_PCT = 0.12
START_BALANCE = 10000.0
DAY_MS = 86_400_000


def execution_month(last_completed_day_ms):
    """Month in which a rebalance decided on this completed day is executed.

    The researched rule (volatility_managed_momentum_v1.backtest) rebalances at
    the first open of a UTC month using data through the previous month's last
    completed day. The execution day is therefore last_completed_day + 1 day.
    """
    return datetime.fromtimestamp((last_completed_day_ms + DAY_MS) / 1000,
                                  timezone.utc).strftime("%Y-%m")


def fresh():
    return {"cash": START_BALANCE, "positions": {}, "trades": [],
            "last_rebalance_day": None, "mode": "PAPER_ONLY",
            "initial_equity": START_BALANCE}


def step(state, day, targets, prices, now=None):
    """Idempotent daily rebalance at current observed prices; stops checked each scan.

    No retroactive fill at prior-day prices. State is returned as a new dict.
    """
    now = now or datetime.now(timezone.utc).isoformat()
    s = {"cash": float(state["cash"]), "positions": {
        symbol: dict(pos) for symbol, pos in state["positions"].items()},
        "trades": list(state["trades"]), "last_rebalance_day": state.get("last_rebalance_day"),
        "mode": "PAPER_ONLY", "initial_equity": START_BALANCE}
    if not all(isinstance(p, (float, int)) and 0 < p < float("inf") for p in prices.values()):
        raise ValueError("Invalid market prices")
    if any(sym not in prices for sym in s["positions"]):
        raise ValueError("Missing price for open position")
    if len(s["positions"]) > 2:
        raise ValueError("Position limit exceeded")
    if any(pos["qty"] <= 0 for pos in s["positions"].values()):
        raise ValueError("Invalid position")
    def close(symbol, reason):
        pos = s["positions"].pop(symbol)
        fill = prices[symbol] * (1 - SLIPPAGE)
        gross = pos["qty"] * (fill - pos["entry"])
        exit_fee = pos["qty"] * fill * FEE
        s["cash"] += pos["qty"] * fill - exit_fee
        s["trades"].append({"symbol": symbol, "entry_at": pos["entry_at"],
                            "exit_at": now, "entry": pos["entry"], "exit": fill,
                            "qty": pos["qty"], "reason": reason,
                            "net_pnl": gross - pos["entry_fee"] - exit_fee,
                            "fees": pos["entry_fee"] + exit_fee})
    for symbol, pos in list(s["positions"].items()):
        if prices[symbol] <= pos["stop"]:
            close(symbol, "STOP")
    # Monthly portfolio reset only. No daily churn and no reentry after stop that day.
    if s["last_rebalance_day"] is None or execution_month(day) != execution_month(
            s["last_rebalance_day"]):
        for symbol in list(s["positions"]):
            close(symbol, "MONTHLY_REBALANCE")
        equity = s["cash"]
        for item in targets[:2]:
            symbol, weight = item["symbol"], float(item["weight"])
            if symbol not in prices or not 0 < weight <= 0.10:
                continue
            notional = equity * weight
            fee = notional * FEE
            if notional + fee > s["cash"]:
                continue
            fill = prices[symbol] * (1 + SLIPPAGE)
            qty = notional / fill
            s["cash"] -= notional + fee
            s["positions"][symbol] = {"qty": qty, "entry": fill,
                                     "entry_at": now, "entry_fee": fee,
                                     "stop": fill * (1 - STOP_PCT)}
        s["last_rebalance_day"] = day
    marked = s["cash"] + sum(p["qty"] * prices[sym] for sym, p in s["positions"].items())
    s["equity"] = marked
    # Net of the already paid entry fee so that, at all times,
    # equity - initial_equity == realized_pnl + unrealized_pnl.
    s["unrealized_pnl"] = sum(p["qty"] * (prices[sym] - p["entry"]) - p["entry_fee"]
                              for sym, p in s["positions"].items())
    s["realized_pnl"] = sum(t["net_pnl"] for t in s["trades"])
    s["trade_count"] = len(s["trades"])
    s["open_count"] = len(s["positions"])
    return s
