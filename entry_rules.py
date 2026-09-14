"""Execution guards for confirmed one-minute PAPER entries.

The scanner can optionally use live order-flow as an execution confirmation.
When enabled, 15m EMA direction is treated as a bonus: aligned trades get
slightly easier order-flow thresholds while counter-trend trades need stronger
book/tape confirmation. Order-flow failures are fail-open by default so a
public market-data outage cannot freeze PAPER trading.
"""
import math
import os
import time

import httpx

ENTRY_INTERVAL = "1m"
STRATEGY_VERSION = "early-entry-orderflow-all-coins-multipos-v9"
MAX_ENTRY_DEVIATION = float(os.getenv("EARLY_MAX_ENTRY_DEVIATION", "0.0020"))
MAX_SIGNAL_AGE_SECONDS = int(os.getenv("EARLY_MAX_SIGNAL_AGE_SECONDS", "90"))

# Optional order-flow execution confirmation. It is enabled only on the
# scanner service through Render env vars, so older/fixed bots importing this
# module keep their previous behaviour.
ORDERFLOW_ENABLED = os.getenv("ORDERFLOW_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
ORDERFLOW_FAIL_OPEN = os.getenv("ORDERFLOW_FAIL_OPEN", "true").lower() in {"1", "true", "yes", "on"}
ORDERFLOW_API = os.getenv("ORDERFLOW_API", os.getenv("BINANCE_API", "https://data-api.binance.vision")).rstrip("/")
ORDERFLOW_DEPTH_LIMIT = int(os.getenv("ORDERFLOW_DEPTH_LIMIT", "20"))
ORDERFLOW_TRADES_LIMIT = int(os.getenv("ORDERFLOW_TRADES_LIMIT", "200"))
ORDERFLOW_TIMEOUT_SECONDS = float(os.getenv("ORDERFLOW_TIMEOUT_SECONDS", "2.5"))
ORDERFLOW_SAMPLE_DELAY = float(os.getenv("ORDERFLOW_SAMPLE_DELAY", "0.35"))

# 15m alignment is a bonus, never a hard gate here.
ORDERFLOW_DEPTH_ALIGNED = float(os.getenv("ORDERFLOW_DEPTH_ALIGNED", "0.56"))
ORDERFLOW_DEPTH_COUNTER = float(os.getenv("ORDERFLOW_DEPTH_COUNTER", "0.62"))
ORDERFLOW_TAPE_ALIGNED = float(os.getenv("ORDERFLOW_TAPE_ALIGNED", "0.52"))
ORDERFLOW_TAPE_COUNTER = float(os.getenv("ORDERFLOW_TAPE_COUNTER", "0.58"))
ORDERFLOW_OPPOSITE_HARD = float(os.getenv("ORDERFLOW_OPPOSITE_HARD", "0.38"))
ORDERFLOW_WALL_DOMINANCE = float(os.getenv("ORDERFLOW_WALL_DOMINANCE", "1.20"))
ORDERFLOW_WALL_RETAIN = float(os.getenv("ORDERFLOW_WALL_RETAIN", "0.50"))
ORDERFLOW_WALL_PRICE_TOL = float(os.getenv("ORDERFLOW_WALL_PRICE_TOL", "0.0008"))
ORDERFLOW_MIN_SCORE = int(os.getenv("ORDERFLOW_MIN_SCORE", "2"))


def _finite_positive(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(value) and value > 0


def _depth_metrics(payload):
    """Return near-book imbalance and largest bid/ask walls by quote notional."""
    bids = payload.get("bids") or []
    asks = payload.get("asks") or []
    if not bids or not asks:
        raise ValueError("empty depth")

    def levels(rows):
        out = []
        for row in rows:
            if len(row) < 2:
                continue
            px, qty = float(row[0]), float(row[1])
            if px <= 0 or qty < 0 or not math.isfinite(px) or not math.isfinite(qty):
                continue
            out.append((px, px * qty))
        if not out:
            raise ValueError("invalid depth")
        return out

    b = levels(bids)
    a = levels(asks)
    bid_total = sum(n for _, n in b)
    ask_total = sum(n for _, n in a)
    total = bid_total + ask_total
    if total <= 0:
        raise ValueError("zero depth")
    bid_wall = max(b, key=lambda x: x[1])
    ask_wall = max(a, key=lambda x: x[1])
    return {
        "bid_ratio": bid_total / total,
        "bid_total": bid_total,
        "ask_total": ask_total,
        "bid_wall_price": bid_wall[0],
        "bid_wall_notional": bid_wall[1],
        "ask_wall_price": ask_wall[0],
        "ask_wall_notional": ask_wall[1],
    }


def _aggressive_buy_ratio(trades):
    """Quote-notional share of buyer-initiated recent aggregate trades.

    Binance aggTrades field `m` means 'buyer is maker'. Therefore m=False is
    buyer-initiated (market buy) and m=True is seller-initiated (market sell).
    """
    buy = 0.0
    sell = 0.0
    for trade in trades or []:
        try:
            notional = float(trade["p"]) * float(trade["q"])
        except (KeyError, TypeError, ValueError):
            continue
        if notional <= 0 or not math.isfinite(notional):
            continue
        if bool(trade.get("m")):
            sell += notional
        else:
            buy += notional
    total = buy + sell
    if total <= 0:
        raise ValueError("empty tape")
    return buy / total


def _same_wall(price1, price2):
    if not _finite_positive(price1) or not _finite_positive(price2):
        return False
    return abs(float(price2) / float(price1) - 1.0) <= ORDERFLOW_WALL_PRICE_TOL


def _persistent_wall(side, first, second):
    if side == "LONG":
        n1 = first["bid_wall_notional"]
        n2 = second["bid_wall_notional"]
        opposing = max(first["ask_wall_notional"], second["ask_wall_notional"], 1e-12)
        return (
            _same_wall(first["bid_wall_price"], second["bid_wall_price"])
            and n2 >= n1 * ORDERFLOW_WALL_RETAIN
            and max(n1, n2) >= opposing * ORDERFLOW_WALL_DOMINANCE
        )
    n1 = first["ask_wall_notional"]
    n2 = second["ask_wall_notional"]
    opposing = max(first["bid_wall_notional"], second["bid_wall_notional"], 1e-12)
    return (
        _same_wall(first["ask_wall_price"], second["ask_wall_price"])
        and n2 >= n1 * ORDERFLOW_WALL_RETAIN
        and max(n1, n2) >= opposing * ORDERFLOW_WALL_DOMINANCE
    )


def _orderflow_snapshot(signal):
    symbol = str(signal.get("symbol") or "").upper()
    if not symbol:
        raise ValueError("missing symbol")

    with httpx.Client(timeout=ORDERFLOW_TIMEOUT_SECONDS) as client:
        r1 = client.get(
            f"{ORDERFLOW_API}/api/v3/depth",
            params={"symbol": symbol, "limit": ORDERFLOW_DEPTH_LIMIT},
        )
        r1.raise_for_status()
        first = _depth_metrics(r1.json())

        if ORDERFLOW_SAMPLE_DELAY > 0:
            time.sleep(ORDERFLOW_SAMPLE_DELAY)

        r2 = client.get(
            f"{ORDERFLOW_API}/api/v3/depth",
            params={"symbol": symbol, "limit": ORDERFLOW_DEPTH_LIMIT},
        )
        r2.raise_for_status()
        second = _depth_metrics(r2.json())

        rt = client.get(
            f"{ORDERFLOW_API}/api/v3/aggTrades",
            params={"symbol": symbol, "limit": ORDERFLOW_TRADES_LIMIT},
        )
        rt.raise_for_status()
        buy_ratio = _aggressive_buy_ratio(rt.json())

    side = signal.get("side")
    aligned_15m = str(signal.get("trend") or "").upper() == side
    depth_threshold = ORDERFLOW_DEPTH_ALIGNED if aligned_15m else ORDERFLOW_DEPTH_COUNTER
    tape_threshold = ORDERFLOW_TAPE_ALIGNED if aligned_15m else ORDERFLOW_TAPE_COUNTER

    avg_bid_ratio = (first["bid_ratio"] + second["bid_ratio"]) / 2.0
    wall_ok = _persistent_wall(side, first, second)

    if side == "LONG":
        depth_ok = avg_bid_ratio >= depth_threshold
        tape_ok = buy_ratio >= tape_threshold
        opposite_hard = avg_bid_ratio <= ORDERFLOW_OPPOSITE_HARD and buy_ratio <= ORDERFLOW_OPPOSITE_HARD
    elif side == "SHORT":
        ask_ratio = 1.0 - avg_bid_ratio
        sell_ratio = 1.0 - buy_ratio
        depth_ok = ask_ratio >= depth_threshold
        tape_ok = sell_ratio >= tape_threshold
        opposite_hard = ask_ratio <= ORDERFLOW_OPPOSITE_HARD and sell_ratio <= ORDERFLOW_OPPOSITE_HARD
    else:
        raise ValueError("invalid side")

    score = int(depth_ok) + int(tape_ok) + int(wall_ok)
    return {
        "score": score,
        "required_score": ORDERFLOW_MIN_SCORE,
        "aligned_15m": aligned_15m,
        "avg_bid_ratio": avg_bid_ratio,
        "aggressive_buy_ratio": buy_ratio,
        "persistent_wall": wall_ok,
        "depth_ok": depth_ok,
        "tape_ok": tape_ok,
        "opposite_hard": opposite_hard,
    }


def _orderflow_rejection(signal):
    if not ORDERFLOW_ENABLED:
        return None
    try:
        flow = _orderflow_snapshot(signal)
        signal["orderflow"] = flow
    except Exception as exc:
        signal["orderflow"] = {"available": False, "error": type(exc).__name__}
        if ORDERFLOW_FAIL_OPEN:
            return None
        return "ORDER FLOW: data nejsou dostupná"

    if flow["opposite_hard"]:
        return "ORDER FLOW: silný tlak proti směru vstupu"
    if flow["score"] < flow["required_score"]:
        return (
            f"ORDER FLOW nepotvrdil vstup ({flow['score']}/{flow['required_score']}; "
            f"book {flow['avg_bid_ratio']*100:.0f}% bid, "
            f"market-buy {flow['aggressive_buy_ratio']*100:.0f}%)"
        )
    return None


def rejection(signal, market, now_ms=None):
    now_ms = time.time() * 1000 if now_ms is None else now_ms
    reference = float(signal["entry"])
    if not math.isfinite(market) or market <= 0 or not math.isfinite(reference) or reference <= 0:
        return "Neplatná aktuální cena"
    age = (now_ms - int(signal["candle_time"]) - 60000) / 1000
    if age < 0 or age > MAX_SIGNAL_AGE_SECONDS:
        return f"Signální svíčka není uzavřená nebo je starší než {MAX_SIGNAL_AGE_SECONDS} sekund"
    if abs(market / reference - 1) > MAX_ENTRY_DEVIATION:
        return f"NO CHASE: cena je více než {MAX_ENTRY_DEVIATION*100:.2f} % od potvrzení"
    level = float(signal["trigger_level"])
    if signal["side"] == "LONG":
        if market <= level or market <= float(signal["pattern_low"]):
            return "Průraz LONG už neplatí"
    elif signal["side"] == "SHORT":
        if market >= level or market >= float(signal["pattern_high"]):
            return "Průraz SHORT už neplatí"
    else:
        return "Neplatný směr"

    return _orderflow_rejection(signal)
