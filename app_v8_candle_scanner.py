from market_data import install_data_health
import asyncio
import copy
import logging
import math
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

import app_v8_candle as fixed
import v8_candle_scanner_engine as scanner
import app_v8_fly_engine as fly
from v8_fly_layer import install as install_fly

install_fly(fly)
FLY_ENABLED = os.getenv("FLY_INTEGRATED_ENABLED", "false").lower() == "true"

BUILD = "combined-v8-account-stats-adaptive-risk-1"
app = FastAPI(title="V8 Candle Combined")
install_data_health(app)
log = logging.getLogger(__name__)
fixed_task = None
scanner_task = None
database_task = None
fly_task = None
fly_error = None
started_at = datetime.now(timezone.utc)
results = {}
workers = {
    "fixed": {"last_success": None, "error": None, "loaded": False},
    "scanner": {"last_success": None, "error": None, "loaded": False},
}
database = {"ok": False, "checked_at": None, "error": "Čekám na ověření databáze"}

_BASE_SCANNER_RISK = float(scanner.RISK_PER_TRADE)
_ORIGINAL_OPEN_POSITION = scanner.open_position


def _pf(rows):
    wins = sum(max(float(t.get("net_pnl", 0) or 0), 0.0) for t in rows)
    losses = abs(sum(min(float(t.get("net_pnl", 0) or 0), 0.0) for t in rows))
    if losses <= 1e-12:
        return math.inf if wins > 0 else 0.0
    return wins / losses


def _risk_guard(signal):
    version = getattr(scanner, "STRATEGY_VERSION", None)
    current = [
        t for t in scanner.history
        if (not version or t.get("strategy_version") == version)
        and isinstance(t.get("net_pnl"), (int, float))
    ]
    side_rows = [t for t in current if t.get("side") == signal.get("side")][:24]
    symbol_rows = [t for t in current if t.get("symbol") == signal.get("symbol")][:12]

    mult = 1.0
    reasons = []
    side_pf = _pf(side_rows)
    symbol_pf = _pf(symbol_rows)

    if len(side_rows) >= 12:
        if side_pf < 0.75:
            mult = min(mult, 0.50)
            reasons.append(f"side PF {side_pf:.2f}")
        elif side_pf < 1.00:
            mult = min(mult, 0.75)
            reasons.append(f"side PF {side_pf:.2f}")

    if len(symbol_rows) >= 5:
        if symbol_pf < 0.50:
            mult = min(mult, 0.50)
            reasons.append(f"coin PF {symbol_pf:.2f}")
        elif symbol_pf < 0.90:
            mult = min(mult, 0.75)
            reasons.append(f"coin PF {symbol_pf:.2f}")

    return {
        "multiplier": mult,
        "side_trades": len(side_rows),
        "side_profit_factor": None if math.isinf(side_pf) else side_pf,
        "symbol_trades": len(symbol_rows),
        "symbol_profit_factor": None if math.isinf(symbol_pf) else symbol_pf,
        "reason": ", ".join(reasons) if reasons else "normal risk",
    }


def adaptive_open_position(signal, market):
    guard = _risk_guard(signal)
    signal["adaptive_risk"] = guard
    scanner.RISK_PER_TRADE = _BASE_SCANNER_RISK * float(guard["multiplier"])
    try:
        return _ORIGINAL_OPEN_POSITION(signal, market)
    finally:
        scanner.RISK_PER_TRADE = _BASE_SCANNER_RISK


scanner.open_position = adaptive_open_position


def utcnow():
    return datetime.now(timezone.utc)


def normalize_scanner_snapshot(data):
    data = copy.deepcopy(data)
    positions = list(data.get("positions") or [])
    balance = float(data.get("balance") or 0.0)

    if not positions:
        data["positions"] = []
        data["position"] = None
        data["price"] = None
        data["unrealized_pnl"] = 0.0
        data["total_unrealized_pnl"] = 0.0
        data["open_positions"] = 0
        data["equity"] = balance
    else:
        total_upnl = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
        data["positions"] = positions
        data["position"] = positions[0]
        data["price"] = float(positions[0].get("current_price") or 0.0)
        data["unrealized_pnl"] = float(positions[0].get("unrealized_pnl") or 0.0)
        data["total_unrealized_pnl"] = total_upnl
        data["open_positions"] = len(positions)
        data["equity"] = balance + total_upnl

    expected = balance + float(data.get("total_unrealized_pnl") or 0.0)
    data["account_consistent"] = abs(float(data.get("equity") or 0.0) - expected) < 1e-8
    data["realized_pnl"] = balance - float(getattr(scanner, "STARTING_BALANCE", 10000.0))
    data["adaptive_risk_enabled"] = True
    data["base_risk_per_trade"] = _BASE_SCANNER_RISK
    return data


def check_database():
    if not fixed.DATABASE_URL or fixed.DATABASE_URL != scanner.DATABASE_URL:
        raise RuntimeError("Databáze obou botů není nakonfigurována shodně")
    with scanner.psycopg.connect(
        scanner.DATABASE_URL,
        connect_timeout=5,
        options="-c statement_timeout=5000",
    ) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        f = conn.execute("SELECT state FROM candle_v8_fixed_state WHERE id=1").fetchone()
        s = conn.execute("SELECT state FROM candle_v8_scanner_state WHERE id=1").fetchone()
        rows = conn.execute(
            "SELECT entry_time, exit_time, net_pnl FROM candle_v8_fixed_trades ORDER BY id DESC LIMIT 100"
        ).fetchall()
    if not f or not s:
        raise RuntimeError("V databázi chybí uložený stav bota")

    for name, state, module in (("Fixed", f[0], fixed), ("Scanner", s[0], scanner)):
        if state.get("paper_balance") != module.paper_balance:
            raise RuntimeError(name + ": uložený balance neodpovídá běžícímu botu")
        if state.get("last_entry_candle") != module.last_entry_candle:
            raise RuntimeError(name + ": poslední vstup není potvrzen v databázi")

    saved_positions = s[0].get("paper_positions")
    if isinstance(saved_positions, dict) and saved_positions != scanner.paper_positions:
        raise RuntimeError("Scanner: otevřené pozice nejsou shodné s databází")
    if s[0].get("history", []) != scanner.history:
        raise RuntimeError("Scanner: historie není shodná s databází")

    saved_fixed = [
        (r[0].isoformat() if r[0] else None, r[1].isoformat() if r[1] else None, r[2])
        for r in rows
    ]
    memory_fixed = [
        (t["entry_time"], t["exit_time"], t["net_pnl"])
        for t in fixed.trade_history[:100]
    ]
    if saved_fixed != memory_fixed:
        raise RuntimeError("Fixed: historie není shodná s databází")

    return {
        "ok": True,
        "checked_at": utcnow().isoformat(),
        "error": None,
        "fixed_history_count": len(rows),
        "scanner_history_count": len(scanner.history),
        "scanner_open_positions": len(scanner.paper_positions),
    }


async def database_loop():
    while True:
        try:
            if all(w["loaded"] for w in workers.values()):
                database.update(check_database())
        except Exception:
            log.exception("DATABASE VERIFICATION FAILED")
            database.update(
                ok=False,
                checked_at=utcnow().isoformat(),
                error="Ověření uloženého stavu selhalo; zkontrolujte databázi",
            )
        await asyncio.sleep(60)


async def worker(name, initialize, cycle, interval):
    state = workers[name]
    while True:
        try:
            if not state["loaded"]:
                initialize()
                state["loaded"] = True
            data = await cycle()
            if name == "scanner":
                data = normalize_scanner_snapshot(data)
            results[name] = copy.deepcopy(data)
            state.update(last_success=utcnow().isoformat(), error=None)
        except Exception:
            log.exception("%s BACKGROUND CYCLE FAILED", name)
            state["error"] = "Chyba běhu bota; probíhá další pokus"
        await asyncio.sleep(interval)


async def fly_worker():
    global fly_error
    while True:
        try:
            if not fly.DATABASE_URL:
                raise RuntimeError("Fly database is missing")
            with fly.get_db() as conn:
                row = conn.execute("SELECT state FROM v8fixed_state WHERE id=1").fetchone()
                if not row:
                    raise RuntimeError("Existing Fly state is missing")
            await fly.startup()
            saved = row[0]
            if fly.PAPER_BALANCE != float(saved["paper_balance"]) or fly.paper_position != saved.get("paper_position"):
                raise RuntimeError("Fly state did not restore correctly")
            fly_error = None
            log.warning("INTEGRATED_FLY_STARTED history=%s", len(fly.trade_history))
            await fly.bot_task
        except asyncio.CancelledError:
            raise
        except Exception:
            fly_error = "Fly se nepodařilo spustit; další pokus za 30 sekund"
            log.exception("INTEGRATED_FLY_FAILED")
        finally:
            await fly.shutdown()
            if fly.bot_task:
                await asyncio.gather(fly.bot_task, return_exceptions=True)
            fly.bot_loop_started = False
        await asyncio.sleep(30)


def fly_status():
    age = (
        (utcnow() - datetime.fromisoformat(fly.last_cycle_at)).total_seconds()
        if fly.last_cycle_at else None
    )
    running = bool(fly_task and not fly_task.done() and fly.bot_task and not fly.bot_task.done())
    return {
        "enabled": FLY_ENABLED,
        "running": running,
        "ok": bool(FLY_ENABLED and running and age is not None and age < 120 and not fly_error),
        "age_seconds": round(age, 1) if age is not None else None,
        "last_cycle_at": fly.last_cycle_at,
        "error": fly_error,
        "history_count": len(fly.trade_history),
        "dashboard": "/fly/",
    }


def initialize_fixed():
    if not fixed.DATABASE_URL:
        raise RuntimeError("Fixed: DATABASE_URL chybí")
    fixed.init_db()
    fixed.load_state()


@app.on_event("startup")
async def startup():
    global fixed_task, scanner_task, database_task, fly_task, started_at
    started_at = utcnow()
    fixed_task = asyncio.create_task(worker("fixed", initialize_fixed, fixed.analyze_once, 15))
    scanner_task = asyncio.create_task(worker("scanner", scanner.load_state, scanner.cycle, scanner.SCAN_SECONDS))
    database_task = asyncio.create_task(database_loop())
    if FLY_ENABLED:
        fly_task = asyncio.create_task(fly_worker())


@app.on_event("shutdown")
async def shutdown():
    tasks = [t for t in (fixed_task, scanner_task, database_task, fly_task) if t]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def runtime_status():
    now = utcnow()
    status = {}
    for name, task, limit in (
        ("fixed", fixed_task, 90),
        ("scanner", scanner_task, max(180, scanner.SCAN_SECONDS * 3)),
    ):
        state = workers[name]
        age = (
            (now - datetime.fromisoformat(state["last_success"])).total_seconds()
            if state["last_success"] else None
        )
        running = bool(task and not task.done())
        status[name] = {
            **state,
            "running": running,
            "ok": running and age is not None and age <= limit and not state["error"],
            "age_seconds": round(age, 1) if age is not None else None,
        }
    db = dict(database)
    db_age = (
        (now - datetime.fromisoformat(db["checked_at"])).total_seconds()
        if db["checked_at"] else None
    )
    db["ok"] = bool(db["ok"] and db_age is not None and db_age <= 150)
    healthy = all(s["ok"] for s in status.values()) and db["ok"]
    fs = fly_status()
    healthy = healthy and (not FLY_ENABLED or fs["ok"])
    return {
        "status": "ok" if healthy else "degraded",
        "service": "V8 Candle Combined",
        "build": BUILD,
        **status,
        "database": db,
        "fly": fs,
        "started_at": started_at.isoformat(),
        "time": now.isoformat(),
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    status = runtime_status()
    return JSONResponse(
        status,
        status_code=200 if status["status"] == "ok" else 503,
        headers={"Cache-Control": "no-store"},
    )


def snapshot(name):
    data = copy.deepcopy(results.get(name, {}))
    state = runtime_status()[name]
    data["background"] = state
    if not state["ok"]:
        data["error"] = state["error"] or "Čekám na aktuální výsledek běhu na pozadí"
    return data


@app.get("/fixed/analyze")
async def fixed_analyze():
    return JSONResponse(snapshot("fixed"), headers={"Cache-Control": "no-store"})


@app.get("/scanner/analyze")
async def scanner_analyze():
    return JSONResponse(snapshot("scanner"), headers={"Cache-Control": "no-store"})


@app.get("/analyze")
async def analyze():
    return JSONResponse(
        {
            "fixed": snapshot("fixed"),
            "scanner": snapshot("scanner"),
            "monitoring": runtime_status(),
            "time": utcnow().isoformat(),
        },
        headers={"Cache-Control": "no-store"},
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return r'''<!doctype html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V8 Candle Combined</title>
<style>
body{margin:0;background:#07111f;color:#f4f7fb;font-family:system-ui}.w{max-width:1000px;margin:auto;padding:18px}.card{background:#0f1b2d;border:1px solid #243650;border-radius:18px;padding:18px;margin:12px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.cell{background:#091526;border-radius:11px;padding:11px}.label,.muted{color:#8ea1b8}.value{font-size:21px;font-weight:800}.ok{color:#21d19f}.red{color:#ff647c}.wait{color:#f8c55c}.big{font-size:30px;font-weight:850}.pill{display:inline-block;border-radius:999px;padding:5px 9px;font-size:12px;font-weight:800;background:#10372f;color:#21d19f}.pos,.trade{border-top:1px solid #243650;padding:12px 0}.row{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.coin{font-size:18px;font-weight:800}table{width:100%;border-collapse:collapse}td,th{padding:7px;border-bottom:1px solid #243650;text-align:left;font-size:12px}.clock{font-size:28px;font-weight:850}@media(max-width:720px){.grid,.stats{grid-template-columns:1fr 1fr}.w{padding:12px}}@media(max-width:430px){.grid,.stats{grid-template-columns:1fr}.value{font-size:19px}}
</style></head><body><div class="w">
<div class="card row"><div><div class="muted">AKTUÁLNÍ ČAS</div><div id="clock" class="clock">--:--:--</div></div><div><div class="muted">STAV</div><div id="runtime">Načítám…</div></div></div>
<h1>V8 Candle Combined</h1><div class="muted">Scanner + Fixed + Fly · PAPER · 1m vstupy · adaptivní risk · poplatky a slippage zahrnuté v čistém P/L</div>
<div class="card"><b>Fly bot ve stejné službě</b><p id="flyState" class="muted">Ověřuji…</p><a href="/fly/" style="color:#21d19f">Otevřít Fly →</a></div>
<div class="grid"><div class="card"><div class="row"><h2>V8 Candle Scanner</h2><span id="scanCount" class="pill">—</span></div><div id="scanner"></div><p id="scannerReason" class="wait"></p></div><div class="card"><div class="row"><h2>V8 Candle Fixed</h2><span id="fixedCount" class="pill">—</span></div><div id="fixed"></div><p id="fixedReason" class="wait"></p></div></div>
<div class="card"><h2>Výsledky aktuální strategie Scanneru</h2><div id="stats"></div></div>
<div class="card"><h2>LONG vs SHORT</h2><div id="sideStats"></div></div>
<div class="card"><h2>Výsledky podle coinů</h2><div id="coinStats"></div></div>
<div class="card"><h2>Otevřené pozice Scanneru</h2><div id="positions"></div></div>
<div class="card"><h2>Poslední obchody Scanneru</h2><div id="history"></div></div>
<div class="card"><h2>Scanner trhu</h2><div id="market"></div></div>
</div><script>
const nf=(v,d=2)=>Number.isFinite(Number(v))?Number(v).toLocaleString('cs-CZ',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
const cls=v=>Number(v)>=0?'ok':'red';
function tick(){clock.textContent=new Date().toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit',second:'2-digit'})}
function pf(rows){const gp=rows.filter(x=>+x.net_pnl>0).reduce((a,x)=>a+(+x.net_pnl),0),gl=Math.abs(rows.filter(x=>+x.net_pnl<0).reduce((a,x)=>a+(+x.net_pnl),0));return gl?gp/gl:(gp>0?Infinity:0)}
function metrics(rows){const wins=rows.filter(x=>+x.net_pnl>0),loss=rows.filter(x=>+x.net_pnl<0),net=rows.reduce((a,x)=>a+(+x.net_pnl||0),0),p=pf(rows),wr=rows.length?wins.length/rows.length*100:0,avg=rows.length?net/rows.length:0;let eq=0,peak=0,maxdd=0;for(const t of [...rows].reverse()){eq+=+t.net_pnl||0;peak=Math.max(peak,eq);maxdd=Math.max(maxdd,peak-eq)}return{n:rows.length,w:wins.length,l:loss.length,net,p,wr,avg,maxdd}}
function statsHtml(m){return `<div class="stats"><div class="cell"><div class="value ${m.wr>=45?'ok':'red'}">${nf(m.wr,1)} %</div><div class="label">Winrate</div></div><div class="cell"><div class="value ${m.p>=1?'ok':'red'}">${Number.isFinite(m.p)?nf(m.p,2):'∞'}</div><div class="label">Profit factor</div></div><div class="cell"><div class="value ${cls(m.net)}">${m.net>=0?'+':''}${nf(m.net)} USDT</div><div class="label">Čistý P/L</div></div><div class="cell"><div class="value red">${nf(m.maxdd)} USDT</div><div class="label">Max drawdown</div></div><div class="cell"><div class="value">${m.w} / ${m.l}</div><div class="label">Wins / Losses</div></div><div class="cell"><div class="value ${cls(m.avg)}">${nf(m.avg)} USDT</div><div class="label">Průměr / obchod</div></div><div class="cell"><div class="value">${m.n}</div><div class="label">Obchodů strategie</div></div><div class="cell"><div class="value">1:2</div><div class="label">Základní R:R</div></div></div>`}
function sideTable(rows){return ['LONG','SHORT'].map(s=>{const m=metrics(rows.filter(x=>x.side===s));return `<tr><td class="${s==='LONG'?'ok':'red'}"><b>${s}</b></td><td>${m.n}</td><td>${nf(m.wr,1)} %</td><td>${Number.isFinite(m.p)?nf(m.p,2):'∞'}</td><td class="${cls(m.net)}">${m.net>=0?'+':''}${nf(m.net)}</td></tr>`}).join('')}
function coins(rows){const map={};for(const t of rows){(map[t.symbol]??=[]).push(t)}return Object.entries(map).map(([s,r])=>[s,metrics(r)]).sort((a,b)=>b[1].net-a[1].net).map(([s,m])=>`<tr><td><b>${s.replace('USDT','')}</b></td><td>${m.n}</td><td>${nf(m.wr,1)} %</td><td>${Number.isFinite(m.p)?nf(m.p,2):'∞'}</td><td class="${cls(m.net)}">${m.net>=0?'+':''}${nf(m.net)}</td></tr>`).join('')}
function positionsHtml(d){const ps=d.positions||[];if(!ps.length)return '<div class="muted">Bez otevřené pozice — Balance a Equity jsou nyní stejné.</div>';return ps.map(p=>`<div class="pos"><div class="row"><div><span class="coin">${p.symbol}</span> <b class="${p.side==='LONG'?'ok':'red'}">${p.side}</b> · ${String(p.setup||'').replaceAll('_',' ')}</div><div class="${cls(p.unrealized_pnl)}"><b>${+p.unrealized_pnl>=0?'+':''}${nf(p.unrealized_pnl)} USDT</b></div></div><div class="muted">Entry ${nf(p.entry_price,6)} · Now ${nf(p.current_price,6)} · SL ${nf(p.stop_loss,6)} · TP ${nf(p.take_profit,6)} · risk guard ×${nf(p.adaptive_risk?.multiplier??1,2)}</div></div>`).join('')}
function historyHtml(rows){return rows.slice(0,20).map(t=>`<div class="trade"><div class="row"><div><b>${t.symbol}</b> <span class="${t.side==='LONG'?'ok':'red'}">${t.side}</span> · ${String(t.setup||'').replaceAll('_',' ')}</div><div class="${cls(t.net_pnl)}"><b>${+t.net_pnl>=0?'+':''}${nf(t.net_pnl)} USDT</b></div></div><div class="muted">${String(t.reason||'').replaceAll('_',' ')} · risk guard ×${nf(t.adaptive_risk?.multiplier??1,2)} · ${new Date(t.exit_time).toLocaleString('cs-CZ')}</div></div>`).join('')||'<div class="muted">Zatím bez historie.</div>'}
function card(d,el,reason){const side=d.position?.side||d.signal?.side||'WAIT';el.innerHTML=`<div class="big ${side==='LONG'?'ok':side==='SHORT'?'red':''}">${side}</div><div>Balance: <b>${nf(d.balance)} USDT</b></div><div>Equity: <b>${nf(d.equity)} USDT</b></div><div class="muted">Otevřeno: ${d.open_positions||0} · nerealizovaný P/L ${nf(d.total_unrealized_pnl||0)} USDT</div>`;reason.textContent=d.error||d.signal?.reason||''}
async function load(){try{const r=await fetch('/analyze',{cache:'no-store'}),j=await r.json(),s=j.scanner||{},f=j.fixed||{},mon=j.monitoring||{};runtime.textContent=mon.status==='ok'?'Běží správně':'Kontrola hlásí problém';runtime.className=mon.status==='ok'?'ok':'red';flyState.textContent=mon.fly?.ok?`Fly běží · historie ${mon.fly.history_count}`:(mon.fly?.enabled?'Fly čeká / chyba':'Fly není aktivní');flyState.className=mon.fly?.ok?'ok':'wait';card(s,scanner,scannerReason);card(f,fixed,fixedReason);scanCount.textContent=`${(s.history||[]).length} uzavřených`;fixedCount.textContent=`${(f.history||[]).length} uzavřených`;const all=s.history||[],cur=all.filter(t=>!s.strategy_version||t.strategy_version===s.strategy_version);stats.innerHTML=statsHtml(metrics(cur));sideStats.innerHTML=`<table><tr><th>Směr</th><th>Obchody</th><th>Winrate</th><th>PF</th><th>P/L USDT</th></tr>${sideTable(cur)}</table><p class="muted">Adaptivní risk sníží nové riziko na 75 % nebo 50 %, pokud má směr dost obchodů a slabý profit factor. Nikdy nezvyšuje riziko nad základ.</p>`;coinStats.innerHTML=`<table><tr><th>Coin</th><th>Obchody</th><th>Winrate</th><th>PF</th><th>P/L USDT</th></tr>${coins(cur)}</table>`;positions.innerHTML=positionsHtml(s);history.innerHTML=historyHtml(all);market.innerHTML=(s.scan||[]).slice(0,20).map(x=>`${x.symbol} · ${x.bucket} · ${nf(x.strength,2)}`).join('<br>')||'—';if(s.account_consistent===false){runtime.textContent='CHYBA ÚČTU: Balance/Equity nejsou konzistentní';runtime.className='red'}}catch(e){runtime.textContent='Aktualizace se nezdařila';runtime.className='red'}}
setInterval(tick,1000);tick();setInterval(load,15000);load();
</script></body></html>'''


@fly.app.middleware("http")
async def fly_availability(request, call_next):
    if not FLY_ENABLED:
        if request.url.path.rstrip("/") == "/fly":
            return HTMLResponse(
                '<html lang="cs"><meta name="viewport" content="width=device-width,initial-scale=1"><body><h1>Fly není aktivní</h1><p>Integrovaný Fly worker je vypnutý.</p><a href="/">Zpět na scanner</a></body></html>',
                status_code=503,
            )
        return JSONResponse({"status": "disabled"}, status_code=503)
    return await call_next(request)


app.mount("/fly", fly.app)
