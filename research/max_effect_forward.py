"""Forward PAPER: MAX efekt (hypotéza R12, varianta L14_H28). Čistá logika bez sítě.

Pravidla převzata beze změny z předregistrovaného protokolu
`research/max_effect/PROTOCOL.md` (větev research/max-effect-20261107):
pondělní rozhodnutí D, signál z denních close do D-2, MAX = nejvyšší denní
výnos za 14 dní, long 3 nejnižší / short 3 nejvyšší MAX, každá noha 10 %
equity, držení 28 dní, bez stop-lossu, likvidace short nohy při 2x vstupu.

Hypotéza byla v backtestu ZAMÍTNUTA (RESULTS.md). Tento modul slouží jen ke
sběru forward dat; není to zisková strategie. Žádné objednávky, žádné klíče.

Odchylky forward běhu od backtestu (nelze jinak, zapsáno předem):
- burza OKX USDT swapy místo Binance USDT-M (Binance futures API je ze
  serveru nedostupné),
- vstup/výstup za cenu pozorovanou při prvním skenu po 00:00 UTC, ne přesně
  za denní open,
- funding se oceňuje cenou pozorovanou při skenu, který jej zaúčtoval.
"""
from math import isfinite

STRATEGY = "MAX_EFFECT_L14_H28_FORWARD_V1"
ASSETS = ("BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT",
          "BNBUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT")
L_DAYS = 14
H_DAYS = 28
N_SIDE = 3
MIN_ELIGIBLE = 6
LEG_WEIGHT = 0.10
FEE = 0.00095
SLIP = 0.0002
LIQ_MULT = 2.0
START_EQUITY = 10_000.0
DAY_MS = 86_400_000


def day_of(ms):
    return ms // DAY_MS * DAY_MS


def first_monday(day_ms):
    """První pondělí >= daný UTC den (1970-01-01 byl čtvrtek)."""
    days = day_ms // DAY_MS
    weekday = (days + 3) % 7  # pondělí = 0
    return (days + (7 - weekday) % 7) * DAY_MS


def max_scores(closes, decision_day):
    """MAX_i z L denních výnosů končících D-2. Jen aktiva s úplným oknem."""
    end = decision_day - 2 * DAY_MS
    out = {}
    for symbol in ASSETS:
        series = closes.get(symbol) or {}
        days = [end - k * DAY_MS for k in range(L_DAYS + 1)]
        values = [series.get(day) for day in days]
        if any(v is None or not isfinite(v) or v <= 0 for v in values):
            continue
        out[symbol] = max(values[k] / values[k + 1] - 1 for k in range(L_DAYS))
    return out


def select(scores):
    """[(symbol, side, score)]; long nízký MAX, short vysoký MAX. [] = hotovost."""
    if len(scores) < MIN_ELIGIBLE:
        return []
    order = sorted(scores, key=lambda s: (scores[s], s))
    return ([(s, 1, scores[s]) for s in order[:N_SIDE]]
            + [(s, -1, scores[s]) for s in order[-N_SIDE:]])


def fresh():
    return {"mode": "PAPER_ONLY", "strategy": STRATEGY,
            "initial_equity": START_EQUITY, "realized_pnl": 0.0,
            "positions": {}, "trades": [], "started_day": None,
            "next_rebalance_day": None, "last_decision": None}


def _valid(price):
    return isinstance(price, (int, float)) and isfinite(price) and price > 0


def step(state, now_ms, closes, highs, prices, funding, now_iso=""):
    """Jeden sken. Idempotentní; vrací nový stav, vstup nemění.

    closes/highs: {symbol: {den_ms: hodnota}} jen z UZAVŘENÝCH denních svíček.
    prices: {symbol: poslední cena}. funding: {symbol: [(čas_ms, sazba)]}.
    """
    if state.get("mode") != "PAPER_ONLY":
        raise ValueError("Unexpected portfolio mode")
    s = {"mode": "PAPER_ONLY", "strategy": STRATEGY, "initial_equity": START_EQUITY,
         "realized_pnl": float(state.get("realized_pnl", 0.0)),
         "positions": {k: dict(v) for k, v in state.get("positions", {}).items()},
         "trades": list(state.get("trades", [])),
         "started_day": state.get("started_day"),
         "next_rebalance_day": state.get("next_rebalance_day"),
         "last_decision": state.get("last_decision")}
    if len(s["positions"]) > 2 * N_SIDE:
        raise ValueError("Position limit exceeded")
    for symbol, pos in s["positions"].items():
        if not _valid(prices.get(symbol)):
            raise ValueError("Missing price for open position " + symbol)
        if pos["qty"] <= 0 or pos["side"] not in (1, -1):
            raise ValueError("Invalid position " + symbol)
    today = day_of(now_ms)
    if s["next_rebalance_day"] is None:
        s["started_day"] = today
        s["next_rebalance_day"] = first_monday(today)

    def record(symbol, pos, exit_fill, exit_fee, net, reason):
        s["realized_pnl"] += net
        s["trades"].append({
            "symbol": symbol, "side": "LONG" if pos["side"] > 0 else "SHORT",
            "entry_at": pos["entry_at"], "exit_at": now_iso,
            "entry": pos["entry"], "exit": exit_fill, "qty": pos["qty"],
            "notional": pos["notional"], "funding": pos["funding"],
            "fees": pos["entry_fee"] + exit_fee, "net_pnl": net,
            "reason": reason, "decision_day": pos["decision_day"],
            "score": pos["score"]})

    # 1) Funding: long platí kladnou sazbu, short ji dostává.
    for symbol, pos in s["positions"].items():
        for stamp, rate in sorted(funding.get(symbol, [])):
            if pos["funding_through_ms"] < stamp <= now_ms:
                pos["funding"] += -pos["side"] * rate * pos["qty"] * prices[symbol]
                pos["funding_through_ms"] = stamp

    # 2) Likvidace short nohy: cena >= 2x vstup => ztráta celého notionalu.
    for symbol, pos in list(s["positions"].items()):
        if pos["side"] > 0:
            continue
        limit = LIQ_MULT * pos["entry"]
        entry_day = day_of(pos["entry_ms"])
        seen = [h for day, h in (highs.get(symbol) or {}).items() if day > entry_day]
        if prices[symbol] >= limit or any(h >= limit for h in seen):
            del s["positions"][symbol]
            record(symbol, pos, None, 0.0,
                   -pos["notional"] - pos["entry_fee"] + pos["funding"], "LIQUIDATION")

    # 3) Rebalance v plánovaný den D (nebo při prvním skenu po něm).
    if today >= s["next_rebalance_day"]:
        decision = s["next_rebalance_day"]
        while decision + H_DAYS * DAY_MS <= today:
            decision += H_DAYS * DAY_MS
        for symbol, pos in list(s["positions"].items()):
            del s["positions"][symbol]
            fill = prices[symbol] * (1 - pos["side"] * SLIP)
            fee = pos["qty"] * fill * FEE
            net = (pos["side"] * pos["qty"] * (fill - pos["entry"])
                   + pos["funding"] - pos["entry_fee"] - fee)
            record(symbol, pos, fill, fee, net, "REBALANCE")
        equity = START_EQUITY + s["realized_pnl"]
        scores = {sym: val for sym, val in max_scores(closes, decision).items()
                  if _valid(prices.get(sym))}
        picks = select(scores) if equity > 0 else []
        for symbol, side, score in picks:
            notional = equity * LEG_WEIGHT
            fill = prices[symbol] * (1 + side * SLIP)
            s["positions"][symbol] = {
                "side": side, "qty": notional / fill, "entry": fill,
                "notional": notional, "entry_fee": notional * FEE,
                "entry_at": now_iso, "entry_ms": now_ms,
                "funding": 0.0, "funding_through_ms": now_ms,
                "decision_day": decision, "score": score}
        s["last_decision"] = {
            "decision_day": decision, "signal_through_day": decision - 2 * DAY_MS,
            "executed_at": now_iso, "late_days": (today - decision) // DAY_MS,
            "eligible": len(scores), "legs": len(picks), "scores": scores}
        s["next_rebalance_day"] = decision + H_DAYS * DAY_MS

    # 4) Ocenění. Vždy platí: equity - initial == realized + unrealized.
    unrealized = 0.0
    for symbol, pos in s["positions"].items():
        pnl = (pos["side"] * pos["qty"] * (prices[symbol] - pos["entry"])
               + pos["funding"] - pos["entry_fee"])
        pos["last_price"] = prices[symbol]
        pos["unrealized_pnl"] = pnl
        unrealized += pnl
    s["unrealized_pnl"] = unrealized
    s["equity"] = START_EQUITY + s["realized_pnl"] + unrealized
    s["trade_count"] = len(s["trades"])
    s["open_count"] = len(s["positions"])
    return s
