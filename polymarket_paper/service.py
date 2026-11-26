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


def _esc(x) -> str:
    import html
    return html.escape(str(x))


def page_html(d: dict) -> str:
    """Čitelná stránka v češtině, obnovuje se každých 30 s."""
    import datetime as _dt

    def t(ts):
        if not ts:
            return "–"
        return _dt.datetime.fromtimestamp(ts, _dt.timezone(_dt.timedelta(hours=1))).strftime("%d. %m. %H:%M:%S")

    run = "🟢 běží" if d.get("running") else "🔴 neběží"
    b = d.get("book_since_restart") or {}
    n = b.get("n", 0)
    book = (f"{n} snímků • nejnižší součet UP+DOWN <b>{b.get('min_sum') if b.get('min_sum') is not None else '–'}</b> • "
            f"pod 1,00: <b>{b.get('below_1', 0)}×</b> • pod 0,98: <b>{b.get('below_098', 0)}×</b>") if n else "zatím bez dat"
    names = {"instant_pair": "Okamžitý pár (čistá arbitráž)", "leg_in": "Postupné skládání páru (styl z tweetu)"}
    rows = ""
    for key, label in names.items():
        s = (d.get("strategies") or {}).get(key)
        if not s:
            rows += f"<tr><td>{label}</td><td colspan=6 class=muted>zatím žádný vyhodnocený trh</td></tr>"
            continue
        cls = "green" if s["pnl"] >= 0 else "red"
        wr = round(100 * s["wins"] / s["markets"], 1) if s["markets"] else 0
        rows += (f"<tr><td>{label}</td><td>{s['markets']}</td><td class={cls}><b>{s['pnl']:+.2f}</b></td>"
                 f"<td>{s['roi_on_cost'] * 100:+.2f} %</td><td>{wr} %</td><td>{s['unmatched_markets']}</td>"
                 f"<td class=red>{s['worst']:.2f}</td></tr>")
    err = f"<p class=red>Poslední chyba: {_esc(d.get('last_error'))}</p>" if d.get("last_error") else ""
    dberr = f"<p class=red>Chyba databáze: {_esc(d.get('db_error'))}</p>" if d.get("db_error") else ""
    return f"""<!doctype html><html lang=cs><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><meta http-equiv=refresh content=30>
<title>Polymarket UP/DOWN · PAPER</title><style>
body{{background:#0b1118;color:#e6edf3;font-family:system-ui,sans-serif;margin:0;padding:16px}}
.card{{background:#111a24;border:2px solid #c084fc;border-radius:14px;padding:16px;margin-bottom:14px}}
h1{{font-size:22px;margin:0 0 6px}} a{{color:#7dd3fc}} .muted{{color:#8b98a5}}
.green{{color:#5ce68b}} .red{{color:#ff6b6b}} table{{width:100%;border-collapse:collapse;font-size:14px}}
td,th{{padding:8px 6px;border-bottom:1px solid #223;text-align:left}}
.wrap{{overflow-x:auto}}</style></head><body>
<a href="/">← Přehled všech botů</a>
<div class=card><h1>🎰 Polymarket UP/DOWN · PAPER</h1>
<div class=muted>BTC / ETH / SOL / XRP • 5 a 15min trhy • nákup obou stran pod 1 USDC • žádné skutečné objednávky</div>
<p>{run} • start {t(d.get('started_at'))} • poslední krok {t(d.get('last_step'))} • kroků {d.get('steps', 0)} • chyb {d.get('errors', 0)} • otevřené trhy {d.get('open_markets', 0)}</p>
{err}{dberr}</div>
<div class=card><h2 style="margin-top:0">Výsledky (USDC, po poplatcích)</h2><div class=wrap><table>
<tr><th>Strategie</th><th>Trhů</th><th>PnL</th><th>Výnos z nákladu</th><th>Ziskových</th><th>Nespárované</th><th>Nejhorší trh</th></tr>
{rows}</table></div>
<p class=muted>Na jeden trh max. 200 kusů na stranu, nákup po 10 kusech. Simulace je spíš optimistická: plnění za zobrazenou cenu bez zpoždění a bez konkurence.</p></div>
<div class=card><h2 style="margin-top:0">Kniha objednávek od restartu</h2><p>{book}</p>
<p class=muted>Okamžitá arbitráž vyžaduje součet pod 1,00 i po poplatcích.</p></div>
<div class=card><h2 style="margin-top:0">Kritérium úspěchu</h2>
<p class=muted>Aspoň 7 dní a 300 vyhodnocených trhů na strategii, zisk po poplatcích v obou polovinách období. Stránka se obnovuje každých 30 s.</p></div>
</body></html>"""
