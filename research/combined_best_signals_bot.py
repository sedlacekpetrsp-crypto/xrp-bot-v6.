"""Standalone 24/7 PAPER-only candidate monitor. No broker/exchange order endpoints.

Run: python -m research.combined_best_signals_bot
Requires public Binance spot daily candles; never authenticates or submits orders.
State is written atomically to a local JSON file. Simulated portfolio accounting uses current public prices, fees and slippage.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from research.combined_best_signals_paper import select_candidates
from research.volatility_managed_momentum_v1 import SYMBOLS
from research.combined_paper_postgres import apply

POLL_SECONDS = max(300, int(os.getenv("COMBINED_PAPER_POLL_SECONDS", "900")))
STATE_PATH = Path(os.getenv("COMBINED_PAPER_STATE", "combined_paper_state.json"))
LEDGER_PATH = Path(os.getenv("COMBINED_PAPER_LEDGER", "combined_paper_ledger.json"))
MARKET_URL = os.getenv("COMBINED_PUBLIC_MARKET_URL",
                       "https://data-api.binance.vision/api/v3/klines")
# Never use private endpoints, credentials, margin or live trading.
INITIAL_EQUITY = 10000.0


def fetch_daily(symbol):
    query = urlencode({"symbol": symbol, "interval": "1d", "limit": 160})
    request = Request(MARKET_URL + "?" + query,
                      headers={"User-Agent": "paper-research-monitor/1.0"})
    with urlopen(request, timeout=15) as response:
        raw = json.load(response)
    if not isinstance(raw, list) or len(raw) < 100:
        raise ValueError("Insufficient daily candles for " + symbol)
    now_ms = int(time.time() * 1000)
    candles = []
    for row in raw:
        # Binance kline close-time is inclusive; exclude unfinished candle.
        if int(row[6]) >= now_ms:
            continue
        close = float(row[4])
        if close <= 0:
            raise ValueError("Nonpositive close")
        candles.append({"timestamp": int(row[0]), "close": close})
    return candles


def snapshot(fetch=fetch_daily):
    market = {symbol: fetch(symbol) for symbol in SYMBOLS}
    shared = set.intersection(*(set(bar["timestamp"] for bar in rows)
                                for rows in market.values()))
    stamps = sorted(shared)
    if len(stamps) < 100:
        raise ValueError("Not enough aligned completed daily candles")
    if any(stamps[i] - stamps[i-1] != 86400000 for i in range(1, len(stamps))):
        raise ValueError("Missing day in aligned market history")
    aligned = {symbol: [next(row for row in market[symbol]
                             if row["timestamp"] == stamp) for stamp in stamps]
               for symbol in SYMBOLS}
    candidates = select_candidates(aligned, len(stamps) - 1)
    return {"mode": "PAPER_RESEARCH_ONLY", "execution_enabled": False,
            "strategy": "COMBINED_BEST_SIGNALS_V1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "last_completed_day": stamps[-1], "initial_reference_usdt": INITIAL_EQUITY,
            "candidates": candidates, "signal_count": len(candidates),
            "note": "Signals only; no simulated fills, realized PnL or orders."}


def fetch_prices():
    result = {}
    for symbol in SYMBOLS:
        query = urlencode({"symbol": symbol})
        request = Request("https://data-api.binance.vision/api/v3/ticker/price?" + query,
                          headers={"User-Agent": "paper-research-monitor/1.0"})
        with urlopen(request, timeout=15) as response:
            result[symbol] = float(json.load(response)["price"])
    return result


def save_atomic(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def run_forever():
    while True:
        try:
            result = snapshot()
            # Simulated fills use fresh observed ticker prices, never historical closes.
            prices = fetch_prices()
            result = apply(result, prices)
            # Local snapshot is only a non-authoritative cache; PostgreSQL is canonical.
            save_atomic(STATE_PATH, result)
            print(json.dumps({"event": "PAPER_SCAN", **result}), flush=True)
        except Exception as exc:
            print(json.dumps({"event": "PAPER_SCAN_ERROR",
                              "error": type(exc).__name__ + ": " + str(exc),
                              "mode": "PAPER_RESEARCH_ONLY"}), flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
