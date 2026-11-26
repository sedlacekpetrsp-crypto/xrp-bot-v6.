"""Napojení PAPER simulátoru do FastAPI služby (xrp-fly-whale-24-7).

- běží v samostatném daemon vlákně (synchronní HTTP neblokuje event loop),
- jakákoli chyba zůstane uvnitř vlákna, hlavní boty neovlivní,
- obchody a vyhodnocení ukládá do Postgresu (tabulka pm_paper_events),
  snímky knihy jen agreguje v paměti (jinak by šly stovky tisíc řádků denně),
- vypnutí bez zásahu do kódu: proměnná PM_PAPER_ENABLED=0.

Žádné objednávky, žádné klíče. Čte jen veřejná API Polymarketu.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict

from .collector import Runner

STATE = {"started_at": None, "last_step": None, "steps": 0, "errors": 0,
         "last_error": None, "runner": None}
_thread = None


def _db_url():
    return os.getenv("DATABASE_URL")


def _connect():
    import psycopg
    return psycopg.connect(_db_url())


def init_db() -> None:
    if not _db_url():
        return
    with _connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS pm_paper_events (
            id BIGSERIAL PRIMARY KEY,
            kind TEXT NOT NULL,
            row JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW())""")
        c.execute("CREATE INDEX IF NOT EXISTS pm_paper_events_kind ON pm_paper_events(kind)")


def db_sink(kind: str, row: dict) -> None:
    with _connect() as c:
        c.execute("INSERT INTO pm_paper_events(kind,row) VALUES (%s,%s::jsonb)",
                  (kind, json.dumps(row)))


def _loop(assets, tfs, poll) -> None:
    runner = Runner(None, sink=db_sink if _db_url() else None)
    STATE["runner"] = runner
    while True:
        t0 = time.time()
        try:
            runner.step(assets, tfs)
            STATE["steps"] += 1
            STATE["last_step"] = round(t0)
        except Exception as e:
            STATE["errors"] += 1
            STATE["last_error"] = repr(e)[:300]
        time.sleep(max(0.5, poll - (time.time() - t0)))


def start() -> bool:
    """Spustí vlákno jednou. Vrací True, pokud běží."""
    global _thread
    if os.getenv("PM_PAPER_ENABLED", "1") == "0":
        return False
    if _thread and _thread.is_alive():
        return True
    try:
        init_db()
    except Exception as e:
        STATE["last_error"] = f"init_db: {e!r}"[:300]
    assets = os.getenv("PM_ASSETS", "btc,eth,sol,xrp").split(",")
    tfs = os.getenv("PM_TFS", "5m,15m").split(",")
    poll = float(os.getenv("PM_POLL_SEC", "4"))
    STATE["started_at"] = round(time.time())
    _thread = threading.Thread(target=_loop, args=(assets, tfs, poll),
                               name="pm-paper", daemon=True)
    _thread.start()
    print(f"PM PAPER started {assets} {tfs} poll={poll}s db={bool(_db_url())}", flush=True)
    return True


def _settlements_from_db() -> list[dict]:
    if not _db_url():
        return []
    with _connect() as c:
        rows = c.execute("SELECT row FROM pm_paper_events WHERE kind='settlements' "
                         "ORDER BY id").fetchall()
    return [r[0] for r in rows]


def status() -> dict:
    r = STATE["runner"]
    out = {k: v for k, v in STATE.items() if k != "runner"}
    out["running"] = bool(_thread and _thread.is_alive())
    out["mode"] = "PAPER (žádné objednávky)"
    if r:
        st = dict(r.snap_stats)
        if st["n"]:
            st["share_below_1"] = round(st["below_1"] / st["n"], 4)
            st["share_below_098"] = round(st["below_098"] / st["n"], 4)
        out["book_since_restart"] = st
        out["open_markets"] = len(r.pending)
    try:
        sett = [s for s in _settlements_from_db() if s.get("status") == "resolved"]
    except Exception as e:
        out["db_error"] = repr(e)[:200]
        sett = []
    by = defaultdict(lambda: {"markets": 0, "pnl": 0.0, "cost": 0.0, "wins": 0,
                              "unmatched_markets": 0, "worst": 0.0})
    for s in sett:
        b = by[s["strategy"]]
        b["markets"] += 1
        b["pnl"] += s["pnl"]
        b["cost"] += s["cost"]
        b["wins"] += s["pnl"] > 0
        b["unmatched_markets"] += s["shares_up"] != s["shares_dn"]
        b["worst"] = min(b["worst"], s["pnl"])
    for b in by.values():
        b["roi_on_cost"] = round(b["pnl"] / b["cost"], 4) if b["cost"] else 0.0
        b["pnl"] = round(b["pnl"], 2)
        b["cost"] = round(b["cost"], 2)
        b["worst"] = round(b["worst"], 2)
    out["strategies"] = dict(by)
    return out
