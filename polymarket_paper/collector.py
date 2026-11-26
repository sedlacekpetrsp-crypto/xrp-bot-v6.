"""PAPER běh: čte veřejná data Polymarketu a simuluje strategie.

Spuštění:  python -m polymarket_paper.collector
Proměnné:  PM_ASSETS=btc,eth,sol,xrp  PM_TFS=5m,15m  PM_POLL_SEC=3
           PM_DATA_DIR=data/polymarket_paper

Neodesílá žádné objednávky, nepotřebuje klíče ani peněženku.
Výstup: JSONL soubory (fills, settlements, snapshots) v PM_DATA_DIR.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

from .core import DOWN, UP, InstantPair, LegIn, Position, parse_asks

GAMMA = "https://gamma-api.polymarket.com/events?slug={slug}"
BOOK = "https://clob.polymarket.com/book?token_id={tid}"
TF_SEC = {"5m": 300, "15m": 900}
DEFAULT_RATE = 0.07  # záložní (nejvyšší krypto) sazba, když trh feeSchedule nemá


def http_json(url: str, timeout: float = 10.0):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def window_slug(asset: str, tf: str, now: float) -> tuple[str, int]:
    start = int(now) // TF_SEC[tf] * TF_SEC[tf]
    return f"{asset}-updown-{tf}-{start}", start


def market_from_event(ev: dict) -> dict | None:
    if not ev or not ev.get("markets"):
        return None
    m = ev["markets"][0]
    outcomes = json.loads(m["outcomes"])
    tokens = json.loads(m["clobTokenIds"])
    idx = {o.lower(): i for i, o in enumerate(outcomes)}
    if "up" not in idx or "down" not in idx:
        return None
    fee = m.get("feeSchedule") or {}
    rate = float(fee.get("rate", DEFAULT_RATE)) if m.get("feesEnabled", True) else 0.0
    return {
        "slug": m.get("slug") or ev.get("slug"),
        "tokens": [tokens[idx["up"]], tokens[idx["down"]]],
        "rate": rate,
        "closed": bool(m.get("closed")),
        "prices": [float(x) for x in json.loads(m.get("outcomePrices") or "[0,0]")],
        "up_idx": idx["up"],
    }


def winner_from_market(m: dict) -> int | None:
    """Vítěz po vyhodnocení: cena 1 u Up => UP, jinak DOWN."""
    if not m or not m["closed"]:
        return None
    p_up = m["prices"][m["up_idx"]]
    p_dn = m["prices"][1 - m["up_idx"]]
    if p_up >= 0.99:
        return UP
    if p_dn >= 0.99:
        return DOWN
    return None


class Runner:
    def __init__(self, data_dir: Path, fetch=http_json):
        self.fetch = fetch
        self.dir = data_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.strategies = [InstantPair(), LegIn()]
        self.markets: dict[str, dict] = {}   # slug -> market info
        self.ends: dict[str, int] = {}       # slug -> unix konec okna
        self.pos: dict[tuple[str, str], Position] = {}
        self.pending: set[str] = set()       # skončené trhy čekající na výsledek

    def log(self, name: str, row: dict) -> None:
        row["ts"] = round(time.time(), 3)
        with open(self.dir / f"{name}.jsonl", "a") as f:
            f.write(json.dumps(row) + "\n")

    def load_market(self, slug: str) -> dict | None:
        evs = self.fetch(GAMMA.format(slug=slug))
        return market_from_event(evs[0] if evs else None)

    def step(self, assets, tfs, now: float | None = None) -> None:
        now = now or time.time()
        for asset in assets:
            for tf in tfs:
                slug, start = window_slug(asset, tf, now)
                try:
                    if slug not in self.markets:
                        m = self.load_market(slug)
                        if not m:
                            continue
                        self.markets[slug] = m
                        self.ends[slug] = start + TF_SEC[tf]
                    self.trade(slug, self.ends[slug] - now)
                except Exception as e:  # jeden trh nesmí zastavit ostatní
                    self.log("errors", {"slug": slug, "error": repr(e)[:300]})
        self.settle(now)

    def trade(self, slug: str, secs_left: float) -> None:
        m = self.markets[slug]
        if secs_left <= 2:
            return
        asks_up = parse_asks(self.fetch(BOOK.format(tid=m["tokens"][UP])))
        asks_dn = parse_asks(self.fetch(BOOK.format(tid=m["tokens"][DOWN])))
        if not asks_up or not asks_dn:
            return
        self.log("snapshots", {"slug": slug, "secs_left": round(secs_left, 1),
                               "ask_up": asks_up[0][0], "ask_dn": asks_dn[0][0],
                               "sum": round(asks_up[0][0] + asks_dn[0][0], 4)})
        for s in self.strategies:
            pos = self.pos.setdefault((s.name, slug), Position())
            kw = {"secs_left": secs_left} if isinstance(s, LegIn) else {}
            for side, shares, cost in s.on_book(pos, asks_up, asks_dn, m["rate"], **kw):
                pos.add(side, shares, cost)
                self.log("fills", {"strategy": s.name, "slug": slug,
                                   "side": "UP" if side == UP else "DOWN",
                                   "shares": shares, "cost": round(cost, 4),
                                   "secs_left": round(secs_left, 1)})
        self.pending.add(slug)

    def settle(self, now: float) -> None:
        for slug in list(self.pending):
            if now < self.ends[slug] + 30:   # dát trhu čas na vyhodnocení
                continue
            m = self.load_market(slug)
            w = winner_from_market(m)
            if w is None:
                if now > self.ends[slug] + 3600:   # po hodině vzdát, zalogovat
                    self.log("settlements", {"slug": slug, "status": "unresolved"})
                    self.pending.discard(slug)
                continue
            for s in self.strategies:
                pos = self.pos.pop((s.name, slug), None)
                if pos and pos.fills:
                    self.log("settlements", {
                        "strategy": s.name, "slug": slug, "status": "resolved",
                        "winner": "UP" if w == UP else "DOWN",
                        "shares_up": pos.shares[UP], "shares_dn": pos.shares[DOWN],
                        "matched": pos.matched, "cost": round(sum(pos.cost), 4),
                        "pnl": round(pos.settle(w), 4), "fills": pos.fills})
            self.pending.discard(slug)
            self.markets.pop(slug, None)


def main() -> None:
    assets = os.getenv("PM_ASSETS", "btc,eth,sol,xrp").split(",")
    tfs = os.getenv("PM_TFS", "5m,15m").split(",")
    poll = float(os.getenv("PM_POLL_SEC", "3"))
    r = Runner(Path(os.getenv("PM_DATA_DIR", "data/polymarket_paper")))
    print(f"PAPER Polymarket: {assets} {tfs} každé {poll}s -> {r.dir}", flush=True)
    while True:
        t0 = time.time()
        try:
            r.step(assets, tfs)
        except Exception as e:  # síť / API výpadek nesmí shodit běh
            r.log("errors", {"error": repr(e)[:300]})
        time.sleep(max(0.0, poll - (time.time() - t0)))


if __name__ == "__main__":
    main()
