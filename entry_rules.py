"""Execution guards for confirmed one-minute PAPER entries."""
import math
import os
import time

ENTRY_INTERVAL = "1m"
STRATEGY_VERSION = "early-entry-all-coins-multipos-v8"
MAX_ENTRY_DEVIATION = float(os.getenv("EARLY_MAX_ENTRY_DEVIATION", "0.0020"))
MAX_SIGNAL_AGE_SECONDS = int(os.getenv("EARLY_MAX_SIGNAL_AGE_SECONDS", "90"))

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
    return None
