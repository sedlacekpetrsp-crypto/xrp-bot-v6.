"""Forward PAPER monitor MAX efektu: veřejná data OKX, stav v PostgreSQL, stránka.

Pouze veřejné tržní endpointy (svíčky, tickery, historie fundingu). Žádné
přihlášení, žádné objednávky. Při jakékoli chybě dat se sken zahodí a stav
se nemění (fail closed); další pokus za POLL_SECONDS.
"""
import json
import os
import threading
import time
from datetime import datetime, timezone
from math import isfinite
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from research.max_effect_forward import (ASSETS, DAY_MS, H_DAYS, L_DAYS, STRATEGY,
                                         fresh, step)

OKX = "https://www.okx.com/api/v5/"
POLL_SECONDS = max(300, int(os.getenv("MAX_EFFECT_PAPER_POLL_SECONDS", "900")))
NO_INSTRUMENT = "51001"
FUNDING_LIMIT = 100


class OkxRejected(ValueError):
    def __init__(self, code, message):
        super().__init__("OKX " + str(code) + ": " + str(message))
        self.code = str(code)


def inst(symbol):
    return symbol[:-4] + "-USDT-SWAP"


def _get(path, params):
    request = Request(OKX + path + "?" + urlencode(params),
                      headers={"User-Agent": "paper-research-monitor/1.0"})
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except HTTPError as exc:
        # OKX vrací chybový kód v těle i při HTTP 4xx.
        try:
            payload = json.load(exc)
        except Exception:
            raise exc
    if not isinstance(payload, dict):
        raise ValueError("Invalid OKX response")
    if payload.get("code") != "0":
        raise OkxRejected(payload.get("code"), payload.get("msg"))
    if not isinstance(payload.get("data"), list):
        raise ValueError("Invalid OKX data")
    return payload["data"]


def parse_daily(rows, now_ms):
    """-> (closes, highs) jen z uzavřených UTC denních svíček."""
    closes, highs = {}, {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 9:
            raise ValueError("Invalid OKX candle row")
        stamp = int(row[0])
        if stamp <= 0 or stamp % DAY_MS:
            raise ValueError("OKX candle is not aligned to UTC day")
        if str(row[8]) != "1" or stamp + DAY_MS > now_ms:
            continue
        high, close = float(row[2]), float(row[4])
        if not (isfinite(high) and isfinite(close) and 0 < close <= high):
            raise ValueError("Invalid OKX candle values")
        closes[stamp], highs[stamp] = close, high
    return closes, highs


def parse_prices(rows):
    wanted = {inst(symbol): symbol for symbol in ASSETS}
    out = {}
    for row in rows:
        symbol = wanted.get(row.get("instId")) if isinstance(row, dict) else None
        if symbol is None:
            continue
        try:
            price = float(row.get("last"))
        except (TypeError, ValueError):
            continue
        if isfinite(price) and price > 0:
            out[symbol] = price
    return out


def parse_funding(rows):
    out = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid OKX funding row")
        raw = row.get("realizedRate")
        if raw in (None, ""):
            raw = row.get("fundingRate")
        rate, stamp = float(raw), int(row["fundingTime"])
        if not isfinite(rate) or abs(rate) > 0.05 or stamp <= 0:
            raise ValueError("Invalid OKX funding value")
        out.append((stamp, rate))
    return sorted(out)


def collect(open_positions, now_ms, get=_get, pause=0.15):
    """Stáhne vše pro jeden sken. Chybějící instrument = nezpůsobilé aktivum."""
    closes, highs, unavailable = {}, {}, []
    for symbol in ASSETS:
        try:
            rows = get("market/candles", {"instId": inst(symbol), "bar": "1Dutc",
                                          "limit": str(L_DAYS + 20)})
        except OkxRejected as exc:
            if exc.code != NO_INSTRUMENT:
                raise
            unavailable.append(symbol)
            continue
        closes[symbol], highs[symbol] = parse_daily(rows, now_ms)
        time.sleep(pause)
    prices = parse_prices(get("market/tickers", {"instType": "SWAP"}))
    funding, warnings = {}, []
    for symbol, pos in open_positions.items():
        events = parse_funding(get("public/funding-rate-history",
                                   {"instId": inst(symbol), "limit": str(FUNDING_LIMIT)}))
        if len(events) >= FUNDING_LIMIT and events[0][0] > pos["funding_through_ms"]:
            warnings.append("funding_history_gap:" + symbol)
        funding[symbol] = events
        time.sleep(pause)
    return closes, highs, prices, funding, unavailable, warnings


# ------------------------------------------------------------------ PostgreSQL
def _connect():
    import psycopg
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL missing: fail closed, do not reset PAPER portfolio")
    return psycopg.connect(url, connect_timeout=10)


def _ensure(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS max_effect_paper_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        ledger JSONB NOT NULL,
        snapshot JSONB,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""")


def read():
    with _connect() as conn:
        with conn.cursor() as cur:
            _ensure(cur)
            cur.execute("SELECT ledger, snapshot, updated_at FROM max_effect_paper_state WHERE id=1")
            row = cur.fetchone()
        conn.commit()
    if row is None:
        return {"status": "AWAITING_FIRST_SCAN", "persistence": "postgres"}
    return {"status": "RUNNING", "persistence": "postgres", "paper_portfolio": row[0],
            "snapshot": row[1], "updated_at": row[2].isoformat()}


def scan():
    """Jeden sken v jedné transakci se zámkem řádku; při chybě rollback."""
    now_ms = int(time.time() * 1000)
    now_iso = datetime.fromtimestamp(now_ms / 1000, timezone.utc).isoformat()
    with _connect() as conn:
        with conn.cursor() as cur:
            _ensure(cur)
            cur.execute("""INSERT INTO max_effect_paper_state (id, ledger)
                           VALUES (1, %s::jsonb) ON CONFLICT (id) DO NOTHING""",
                        (json.dumps(fresh()),))
            cur.execute("SELECT ledger FROM max_effect_paper_state WHERE id=1 FOR UPDATE")
            previous = cur.fetchone()[0]
            closes, highs, prices, funding, unavailable, warnings = collect(
                previous.get("positions", {}), now_ms)
            ledger = step(previous, now_ms, closes, highs, prices, funding, now_iso)
            snapshot = {"mode": "PAPER_RESEARCH_ONLY", "execution_enabled": False,
                        "strategy": STRATEGY, "generated_at_utc": now_iso,
                        "data_source": "OKX public USDT swaps",
                        "unavailable_assets": unavailable, "warnings": warnings,
                        "note": "Simulated PAPER fills only; no exchange orders."}
            cur.execute("""UPDATE max_effect_paper_state
                           SET ledger=%s::jsonb, snapshot=%s::jsonb, updated_at=NOW()
                           WHERE id=1""", (json.dumps(ledger), json.dumps(snapshot)))
        conn.commit()
    return dict(snapshot, paper_portfolio=ledger)


def run_forever():
    while True:
        try:
            result = scan()
            book = result["paper_portfolio"]
            print(json.dumps({"event": "MAX_EFFECT_PAPER_SCAN", "strategy": STRATEGY,
                              "generated_at_utc": result["generated_at_utc"],
                              "equity": book["equity"], "open_count": book["open_count"],
                              "trade_count": book["trade_count"],
                              "next_rebalance_day": book["next_rebalance_day"],
                              "warnings": result["warnings"],
                              "unavailable_assets": result["unavailable_assets"]}), flush=True)
        except Exception as exc:
            print(json.dumps({"event": "MAX_EFFECT_PAPER_SCAN_ERROR", "strategy": STRATEGY,
                              "error": type(exc).__name__ + ": " + str(exc)[:300]}), flush=True)
        time.sleep(POLL_SECONDS)


# ------------------------------------------------------------------ web
PAGE = """<!doctype html><html lang="cs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAX-efekt L/S · PAPER</title>
<style>body{font:16px system-ui;background:#101923;color:#e9f2fb;margin:0;padding:22px}
main{max-width:900px;margin:auto}.card{background:#1c2a39;border:1px solid #33485d;border-radius:12px;padding:18px;margin:14px 0}
a{color:#8bd3ff}h1{font-size:25px}h2{font-size:18px;margin-top:0}small{color:#a8bacb}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}
strong{font-size:23px}table{width:100%;border-collapse:collapse;font-size:14px}
td,th{padding:6px 4px;border-bottom:1px solid #33485d;text-align:right}
td:first-child,th:first-child{text-align:left}.g{color:#7ee0a1}.r{color:#ff9a9a}
.warn{border-color:#c79a3a}.scroll{overflow-x:auto}</style></head><body><main>
<a href="/">← Přehled všech botů</a><h1>🎲 MAX-efekt long/short</h1>
<p>Pouze simulované PAPER obchody · žádné příkazy na burzu</p>
<div class="card warn"><b>Výzkumná hypotéza R12 – v backtestu neprošla.</b> Běží jen kvůli sběru dat, není to ověřená zisková strategie.
3 longy + 3 shorty z 8 coinů, každá noha 10 % kapitálu, rebalance jednou za 28 dní (pondělí 00:00 UTC).</div>
<div id="health" class="card">Načítám stav…</div>
<div class="grid"><div class="card">Equity<br><strong id="equity">—</strong></div>
<div class="card">Realizovaný P/L<br><strong id="pnl">—</strong></div>
<div class="card">Neuzavřený P/L<br><strong id="upnl">—</strong></div>
<div class="card">Otevřené pozice<br><strong id="open">—</strong></div>
<div class="card">Uzavřené obchody<br><strong id="count">—</strong></div>
<div class="card">Příští rebalance<br><strong id="next">—</strong></div></div>
<div class="card"><h2>Otevřené pozice</h2><div class="scroll"><table id="positions"></table></div></div>
<div class="card"><h2>Historie simulovaných obchodů</h2><div class="scroll"><table id="trades"></table></div></div>
<small>Ceny a funding: veřejná data OKX (USDT swapy). Poplatek 0,095 % + skluz 0,02 % na stranu. Stav je uložen v PostgreSQL.</small>
<script>
const $=id=>document.getElementById(id),n=(v,d=2)=>v==null?'—':Number(v).toFixed(d);
const col=v=>'<td class="'+(Number(v)>=0?'g':'r')+'">'+n(v)+'</td>';
const day=ms=>ms==null?'—':new Date(ms).toISOString().slice(0,10);
function px(v){v=Number(v);return v>=100?v.toFixed(2):v>=1?v.toFixed(4):v.toFixed(5)}
async function refresh(){
try{
const r=await fetch('/max-effect/status',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);
const d=await r.json(),p=d.paper_portfolio||{};
$('health').textContent='Stav: '+d.status+' · poslední sken: '+(d.generated_at_utc||'zatím žádný')+
 ((d.warnings||[]).length?' · upozornění: '+d.warnings.join(', '):'');
$('equity').textContent=p.equity==null?'—':n(p.equity)+' USDT';
$('pnl').textContent=p.realized_pnl==null?'—':n(p.realized_pnl)+' USDT';
$('upnl').textContent=p.unrealized_pnl==null?'—':n(p.unrealized_pnl)+' USDT';
$('open').textContent=p.open_count??'—';$('count').textContent=p.trade_count??'—';
$('next').textContent=day(p.next_rebalance_day);
const pos=Object.entries(p.positions||{});
$('positions').innerHTML=pos.length?'<tr><th>Coin</th><th>Směr</th><th>Vstup</th><th>Cena</th><th>Funding</th><th>P/L</th></tr>'+
 pos.map(([s,x])=>'<tr><td>'+s.replace('USDT','')+'</td><td>'+(x.side>0?'LONG':'SHORT')+'</td><td>'+px(x.entry)+'</td><td>'+px(x.last_price)+'</td>'+col(x.funding)+col(x.unrealized_pnl)+'</tr>').join('')
 :'<tr><td>Žádná otevřená pozice – první vstup proběhne '+day(p.next_rebalance_day)+'.</td></tr>';
const tr=(p.trades||[]).slice(-30).reverse();
$('trades').innerHTML=tr.length?'<tr><th>Coin</th><th>Směr</th><th>Výstup</th><th>Důvod</th><th>P/L</th></tr>'+
 tr.map(t=>'<tr><td>'+t.symbol.replace('USDT','')+'</td><td>'+t.side+'</td><td>'+String(t.exit_at).slice(0,10)+'</td><td>'+t.reason+'</td>'+col(t.net_pnl)+'</tr>').join('')
 :'<tr><td>Zatím žádný uzavřený obchod.</td></tr>';
}catch(e){$('health').textContent='Chyba načtení: '+e.message;}
}refresh();setInterval(refresh,15000);
</script></main></body></html>"""


def status_payload(reader=read):
    base = {"strategy": STRATEGY, "mode": "PAPER_ONLY", "execution_enabled": False,
            "holding_days": H_DAYS, "lookback_days": L_DAYS}
    try:
        state = reader()
    except Exception as exc:
        return 503, dict(base, status="DATABASE_UNAVAILABLE", error=type(exc).__name__,
                         persistence="postgres")
    base.update(state.get("snapshot") or {})
    base.update({key: value for key, value in state.items() if key != "snapshot"})
    return 200, base


def install(app):
    """Zaregistruje stránku, stav a spustí monitor ve vlastním vlákně."""
    from starlette.concurrency import run_in_threadpool
    from starlette.responses import HTMLResponse, JSONResponse

    async def max_effect_status():
        code, body = await run_in_threadpool(status_payload)
        return JSONResponse(body, status_code=code, headers={"Cache-Control": "no-store"})

    async def max_effect_dashboard():
        return HTMLResponse(PAGE)

    app.add_api_route("/max-effect/status", max_effect_status, methods=["GET"])
    app.add_api_route("/max-effect", max_effect_dashboard, methods=["GET"],
                      include_in_schema=False)

    @app.on_event("startup")
    async def _start_max_effect_paper_monitor():
        if os.getenv("MAX_EFFECT_PAPER_ENABLED", "1") != "1":
            return
        threading.Thread(target=run_forever, name="max-effect-paper",
                         daemon=True).start()


if __name__ == "__main__":
    run_forever()
