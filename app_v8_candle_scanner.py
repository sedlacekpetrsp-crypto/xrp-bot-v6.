from market_data import install_data_health
import asyncio
import copy
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

import app_v8_candle as fixed
import v8_candle_scanner_engine as scanner

BUILD = "winrate-stats-v8-cache3"
app = FastAPI(title="V8 Candle Combined")
install_data_health(app)
log = logging.getLogger(__name__)
fixed_task = None
scanner_task = None
database_task = None
started_at = datetime.now(timezone.utc)
results = {}
workers = {
    "fixed": {"last_success": None, "error": None, "loaded": False},
    "scanner": {"last_success": None, "error": None, "loaded": False},
}
database = {"ok": False, "checked_at": None, "error": "Čekám na ověření databáze"}


def utcnow():
    return datetime.now(timezone.utc)


def check_database():
    # Run on the event loop: no cycle can mutate state between capture and comparison.
    # Connection/statement timeouts bound this infrequent read-only check.
    if not fixed.DATABASE_URL or fixed.DATABASE_URL != scanner.DATABASE_URL:
        raise RuntimeError("Databáze obou botů není nakonfigurována shodně")
    with scanner.psycopg.connect(scanner.DATABASE_URL, connect_timeout=5,
                                options="-c statement_timeout=5000") as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        f = conn.execute("SELECT state FROM candle_v8_fixed_state WHERE id=1").fetchone()
        s = conn.execute("SELECT state FROM candle_v8_scanner_state WHERE id=1").fetchone()
        rows = conn.execute(
            "SELECT entry_time, exit_time, net_pnl FROM candle_v8_fixed_trades ORDER BY id DESC LIMIT 100"
        ).fetchall()
    if not f or not s:
        raise RuntimeError("V databázi chybí uložený stav bota")
    for name, state, module in (("Fixed", f[0], fixed), ("Scanner", s[0], scanner)):
        if state.get("paper_balance") != module.paper_balance or state.get("paper_position") != module.paper_position:
            raise RuntimeError(name + ": uložený stav neodpovídá běžícímu botu")
        if state.get("last_entry_candle") != module.last_entry_candle:
            raise RuntimeError(name + ": poslední vstup není potvrzen v databázi")
    if s[0].get("history", []) != scanner.history:
        raise RuntimeError("Scanner: historie není shodná s databází")
    saved_fixed = [(r[0].isoformat() if r[0] else None,
                    r[1].isoformat() if r[1] else None, r[2]) for r in rows]
    memory_fixed = [(t["entry_time"], t["exit_time"], t["net_pnl"]) for t in fixed.trade_history[:100]]
    if saved_fixed != memory_fixed:
        raise RuntimeError("Fixed: historie není shodná s databází")
    return {"ok": True, "checked_at": utcnow().isoformat(), "error": None,
            "fixed_history_count": len(rows), "scanner_history_count": len(scanner.history)}


async def database_loop():
    while True:
        try:
            if all(w["loaded"] for w in workers.values()):
                database.update(check_database())
        except Exception:
            log.exception("DATABASE VERIFICATION FAILED")
            database.update(ok=False, checked_at=utcnow().isoformat(),
                            error="Ověření uloženého stavu selhalo; zkontrolujte databázi")
        await asyncio.sleep(60)


async def worker(name, initialize, cycle, interval):
    state = workers[name]
    while True:
        try:
            if not state["loaded"]:
                initialize()
                state["loaded"] = True
            data = await cycle()
            # Scanner returns net P&L at its latest quote. Invert its own fee/slippage
            # formula to expose that same mark without requesting another market quote.
            p = data.get("position")
            if name == "scanner" and p and p.get("qty", 0) > 0:
                data["price"] = scanner.target_for_net(
                    p["side"], p["entry_price"], data["unrealized_pnl"] / p["qty"])
            results[name] = copy.deepcopy(data)
            state.update(last_success=utcnow().isoformat(), error=None)
        except Exception:
            log.exception("%s BACKGROUND CYCLE FAILED", name)
            state["error"] = "Chyba běhu bota; probíhá další pokus"
        await asyncio.sleep(interval)


def initialize_fixed():
    if not fixed.DATABASE_URL:
        raise RuntimeError("Fixed: DATABASE_URL chybí")
    fixed.init_db()
    fixed.load_state()


@app.on_event("startup")
async def startup():
    global fixed_task, scanner_task, database_task, started_at
    started_at = utcnow()
    fixed_task = asyncio.create_task(worker("fixed", initialize_fixed, fixed.analyze_once, 15))
    scanner_task = asyncio.create_task(worker("scanner", scanner.load_state, scanner.cycle, scanner.SCAN_SECONDS))
    database_task = asyncio.create_task(database_loop())


@app.on_event("shutdown")
async def shutdown():
    tasks = [t for t in (fixed_task, scanner_task, database_task) if t]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def runtime_status():
    now = utcnow()
    status = {}
    for name, task, limit in (("fixed", fixed_task, 90),
                              ("scanner", scanner_task, max(180, scanner.SCAN_SECONDS * 3))):
        state = workers[name]
        age = (now - datetime.fromisoformat(state["last_success"])).total_seconds() if state["last_success"] else None
        running = bool(task and not task.done())
        status[name] = {**state, "running": running,
                        "ok": running and age is not None and age <= limit and not state["error"],
                        "age_seconds": round(age, 1) if age is not None else None}
    db = dict(database)
    db_age = (now - datetime.fromisoformat(db["checked_at"])).total_seconds() if db["checked_at"] else None
    db["ok"] = bool(db["ok"] and db_age is not None and db_age <= 150)
    healthy = all(s["ok"] for s in status.values()) and db["ok"]
    return {"status": "ok" if healthy else "degraded", "service": "V8 Candle Combined",
            "build": BUILD, **status, "database": db,
            "started_at": started_at.isoformat(), "time": now.isoformat()}


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    status = runtime_status()
    return JSONResponse(status, status_code=200 if status["status"] == "ok" else 503,
                        headers={"Cache-Control": "no-store"})


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
    return JSONResponse({"fixed": snapshot("fixed"), "scanner": snapshot("scanner"),
                         "monitoring": runtime_status(), "time": utcnow().isoformat()},
                        headers={"Cache-Control": "no-store"})


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return '''<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V8 Candle Combined</title>
<style>
body{margin:0;background:#07111f;color:#f4f7fb;font-family:system-ui}.w{max-width:980px;margin:auto;padding:18px}.card{background:#0f1b2d;border:1px solid #243650;border-radius:18px;padding:18px;margin:12px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.muted{color:#8ea1b8}.ok{color:#21d19f}.wait{color:#f8c55c}.red{color:#ff647c}.big{font-size:28px;font-weight:800}.clockbar{display:flex;align-items:center;justify-content:space-between;gap:12px;background:#0f1b2d;border:1px solid #243650;border-radius:16px;padding:12px 16px;margin-bottom:16px}.clock{font-size:30px;font-weight:800;letter-spacing:1px}.refresh{font-size:14px;color:#8ea1b8;text-align:right}.refresh.oktxt{color:#21d19f}.refresh.errtxt{color:#ff647c}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #243650;text-align:left;font-size:13px}@media(max-width:700px){.grid{grid-template-columns:1fr}.clockbar{align-items:flex-start;flex-direction:column}.refresh{text-align:left}.clock{font-size:28px}}

.history-title{font-size:22px;margin:0 0 4px}.history-note{font-size:13px;color:#8ea1b8;margin:0 0 18px}
.trade-card{background:#0a1525;border:1px solid #26374d;border-radius:14px;padding:16px;margin-top:12px}
.trade-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}.trade-identity{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.trade-coin{font-size:21px;font-weight:750}.trade-badge{font-size:12px;font-weight:800;letter-spacing:.5px;padding:5px 9px;border-radius:7px}.trade-badge.long{color:#21d19f;background:#10372f}.trade-badge.short{color:#ff647c;background:#391d2b}.trade-result{text-align:right;margin-left:auto}.trade-result strong{display:block;font-size:23px;font-variant-numeric:tabular-nums;white-space:nowrap}.trade-label{color:#8ea1b8;font-size:12px;font-weight:400;display:block;margin-bottom:4px}.trade-prices{display:grid;grid-template-columns:1fr 1fr;gap:14px;border-top:1px solid #243650;margin-top:15px;padding-top:14px}.trade-price{font-size:17px;font-weight:600;font-variant-numeric:tabular-nums}.trade-footer{border-top:1px solid #243650;margin-top:14px;padding-top:12px;display:grid;gap:8px;font-size:13px}.trade-detail{display:flex;justify-content:space-between;gap:14px}.trade-detail span:first-child{color:#8ea1b8;flex-shrink:0}.trade-detail span:last-child{text-align:right;overflow-wrap:anywhere}.trade-empty{color:#8ea1b8;padding:16px 0}
@media(max-width:380px){.trade-card{padding:12px}.trade-result strong{font-size:20px}.trade-coin{font-size:19px}}
.position-summary{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.position-pnl{font-size:30px;font-weight:800;font-variant-numeric:tabular-nums;margin:16px 0 4px}.position-sub{font-size:13px;color:#8ea1b8}.position-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:18px 0}.position-cell{background:#091526;border-radius:10px;padding:12px;min-width:0}.position-value{font-size:18px;font-weight:700;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.position-track{height:12px;background:linear-gradient(90deg,#96354e,#bd9743 45%,#178971);position:relative;border-radius:8px;margin:26px 8px 12px}.position-marker{position:absolute;top:-5px;width:6px;height:22px;background:#fff;transform:translateX(-50%);border:1px solid #07111f;border-radius:4px}.position-entry{position:absolute;top:-3px;width:2px;height:18px;background:#0a1525;transform:translateX(-50%)}.position-scale{display:flex;justify-content:space-between;font-size:12px;gap:10px}.position-note{font-size:12px;color:#8ea1b8;margin-top:12px;line-height:1.5}.position-account{border-top:1px solid #243650;margin-top:16px;padding-top:12px;font-size:14px;color:#8ea1b8}
.stats-box{border-top:1px solid #243650;margin-top:16px;padding-top:14px}.stats-title{font-size:12px;color:#8ea1b8;margin-bottom:8px}.stats-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.stats-cell{background:#091526;border-radius:10px;padding:10px}.stats-value{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums}.stats-label{font-size:11px;color:#8ea1b8;margin-top:2px}.stats-note{font-size:11px;color:#8ea1b8;margin-top:8px;line-height:1.4}
</style></head>
<body><div class="w">
<div class="clockbar"><div><div class="muted">AKTUÁLNÍ ČAS</div><div id="clock" class="clock">--:--:--</div></div><div id="refresh" class="refresh">Data se načítají…</div></div>
<div class="card"><b>Kontrola provozu</b><div id="runtimeState" class="muted">Ověřuji běh na pozadí a uloženou historii…</div></div>\n<h1>V8 Candle Combined</h1><div class="muted">Fixed + Scanner · PAPER · Vstup 1m · trend 15m · aktuální realizační cena · max. odchylka 0,15 % (v7)</div>
<div class="grid"><div class="card"><h2>V8 Candle Fixed</h2><div id="fixed">Načítám…</div><p id="fixedReason" class="wait"></p><div id="fixedStats"></div></div><div class="card"><h2>V8 Candle Scanner</h2><div id="scanner">Načítám…</div><p id="scannerReason" class="wait"></p><div id="scannerStats"></div></div></div>
<div class="card"><h2 class="history-title">Historie Scanneru</h2><p class="history-note">Posledních 20 uzavřených obchodů</p><div id="scannerHistory">Načítám…</div></div><div class="card"><h2 class="history-title">Historie Fixed</h2><p class="history-note">Posledních 20 uzavřených obchodů</p><div id="fixedHistory">Načítám…</div></div><div class="card"><h2>Scanner trhu</h2><div id="scan">Načítám…</div></div></div>
<script>
function tick(){
 const n=new Date();
 clock.textContent=n.toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
function historyNode(tag,cls,text){
 const node=document.createElement(tag);node.className=cls;if(text!==undefined)node.textContent=text;return node;
}
function historyNumber(value,digits){
 if(value===null||value===undefined||!Number.isFinite(Number(value)))return '—';
 return Number(value).toLocaleString('cs-CZ',{minimumFractionDigits:digits,maximumFractionDigits:digits});
}
function renderStats(data,el){
 const h=Array.isArray(data?.history)?data.history:[];
 const closed=h.filter(t=>Number.isFinite(Number(t?.net_pnl)));
 const wins=closed.filter(t=>Number(t.net_pnl)>0);
 const losses=closed.filter(t=>Number(t.net_pnl)<0);
 const decisive=wins.length+losses.length;
 const winrate=decisive?wins.length/decisive*100:0;
 const grossProfit=wins.reduce((a,t)=>a+Number(t.net_pnl),0);
 const grossLoss=Math.abs(losses.reduce((a,t)=>a+Number(t.net_pnl),0));
 const profitFactor=grossLoss?grossProfit/grossLoss:(grossProfit>0?Infinity:0);
 const net=closed.reduce((a,t)=>a+Number(t.net_pnl),0);
 el.innerHTML=`<div class="stats-box"><div class="stats-title">VYHODNOCENÍ UZAVŘENÝCH OBCHODŮ</div><div class="stats-grid"><div class="stats-cell"><div class="stats-value ${winrate>=50?'ok':'red'}">${historyNumber(winrate,1)} %</div><div class="stats-label">Winrate</div></div><div class="stats-cell"><div class="stats-value">${wins.length} / ${losses.length}</div><div class="stats-label">Wins / Losses</div></div><div class="stats-cell"><div class="stats-value ${profitFactor>=1?'ok':'red'}">${Number.isFinite(profitFactor)?historyNumber(profitFactor,2):'∞'}</div><div class="stats-label">Profit factor</div></div><div class="stats-cell"><div class="stats-value ${net>=0?'ok':'red'}">${historyNumber(net,2)} USDT</div><div class="stats-label">Čistý P/L</div></div></div><div class="stats-note">Počet uzavřených obchodů: ${closed.length} · Winrate počítá výhry proti výhrám + ztrátám. Uložená historie má nejvýše 100 obchodů.</div></div>`;
}
function setupName(v){return String(v||'—').replaceAll('_',' ')}
function formatDate(v){
 if(!v)return '—';
 const d=new Date(v);if(Number.isNaN(d.getTime()))return String(v);
 return d.toLocaleString('cs-CZ',{dateStyle:'short',timeStyle:'medium'});
}
function historyRows(data,container){
 container.replaceChildren();
 const h=Array.isArray(data?.history)?data.history.slice(0,20):[];
 if(!h.length){container.append(historyNode('div','trade-empty','Zatím nejsou žádné uzavřené obchody.'));return;}
 for(const t of h){
  const side=String(t.side||'—').toUpperCase();
  const pnl=Number(t.net_pnl);
  const card=historyNode('div','trade-card');
  const head=historyNode('div','trade-head');
  const identity=historyNode('div','trade-identity');
  identity.append(historyNode('div','trade-coin',t.symbol?String(t.symbol).replace('USDT',' / USDT'):'XRP / USDT'));
  identity.append(historyNode('div','trade-badge '+(side==='LONG'?'long':'short'),side));
  const result=historyNode('div','trade-result');
  result.append(historyNode('span','trade-label','Čistý výsledek'));
  result.append(historyNode('strong',Number.isFinite(pnl)?(pnl>=0?'ok':'red'):'',Number.isFinite(pnl)?`${pnl>=0?'+':''}${historyNumber(pnl,2)} USDT`:'—'));
  head.append(identity,result);card.append(head);
  const prices=historyNode('div','trade-prices');
  const ep=historyNode('div','');ep.append(historyNode('span','trade-label','Vstup'),historyNode('div','trade-price',historyNumber(t.entry_price,6)));
  const xp=historyNode('div','');xp.append(historyNode('span','trade-label','Výstup'),historyNode('div','trade-price',historyNumber(t.exit_price,6)));
  prices.append(ep,xp);card.append(prices);
  const footer=historyNode('div','trade-footer');
  for(const [k,v] of [['Setup',setupName(t.setup)],['Ukončení',setupName(t.reason)],['Množství',Number.isFinite(Number(t.qty))?historyNumber(t.qty,3):'—'],['Otevřen',formatDate(t.entry_time)],['Uzavřen',formatDate(t.exit_time)]]){
   const row=historyNode('div','trade-detail');row.append(historyNode('span','',k),historyNode('span','',v));footer.append(row);
  }
  card.append(footer);container.append(card);
 }
}
function positionProgress(p,price){
 if(!p||!Number.isFinite(Number(price)))return 50;
 const sl=Number(p.stop_loss),tp=Number(p.take_profit),px=Number(price);
 if(![sl,tp,px].every(Number.isFinite)||sl===tp)return 50;
 const lo=Math.min(sl,tp),hi=Math.max(sl,tp);return Math.max(0,Math.min(100,(px-lo)/(hi-lo)*100));
}
function renderPosition(data){
 const p=data.position;if(!p)return '<span class="muted">Bez otevřené pozice</span>';
 const px=Number(data.price),pnl=Number(data.unrealized_pnl)||0,progress=positionProgress(p,px);
 const sideClass=String(p.side).toUpperCase()==='LONG'?'ok':'red';
 return `<div class="position-summary"><div><b class="${sideClass}">${p.side}</b> · ${p.symbol||'XRPUSDT'} · ${setupName(p.setup)}</div><div class="position-sub">otevřeno ${formatDate(p.entry_time)}</div></div><div class="position-pnl ${pnl>=0?'ok':'red'}">${pnl>=0?'+':''}${historyNumber(pnl,2)} USDT</div><div class="position-sub">Nerealizovaný čistý P/L včetně poplatků a slippage</div><div class="position-grid"><div class="position-cell"><span class="trade-label">Vstup</span><div class="position-value">${historyNumber(p.entry_price,6)}</div></div><div class="position-cell"><span class="trade-label">Aktuální cena</span><div class="position-value">${historyNumber(px,6)}</div></div><div class="position-cell"><span class="trade-label">Stop loss</span><div class="position-value red">${historyNumber(p.stop_loss,6)}</div></div><div class="position-cell"><span class="trade-label">Take profit</span><div class="position-value ok">${historyNumber(p.take_profit,6)}</div></div><div class="position-cell"><span class="trade-label">Množství</span><div class="position-value">${historyNumber(p.qty,3)}</div></div><div class="position-cell"><span class="trade-label">Risk při vstupu</span><div class="position-value">${historyNumber(p.risk_usdt,2)} USDT</div></div></div><div class="position-track"><div class="position-entry" style="left:${positionProgress(p,p.entry_price)}%"></div><div class="position-marker" style="left:${progress}%"></div></div><div class="position-scale"><span class="red">SL ${historyNumber(p.stop_loss,5)}</span><span>${historyNumber(px,5)}</span><span class="ok">TP ${historyNumber(p.take_profit,5)}</span></div><div class="position-note">Bílá značka ukazuje aktuální cenu mezi SL a TP. Tmavá čára označuje vstup. Průběh se aktualizuje společně s botem.</div>`;
}
function card(d,el,reason,stats){const side=d.position?d.position.side:(d.signal?.side||'WAIT');el.innerHTML='<div class="big '+(side==='WAIT'?'':'ok')+'">'+side+'</div><div>Balance: '+historyNumber(d.balance,2)+' USDT</div><div>Equity: '+historyNumber(d.equity,2)+' USDT</div><div>'+renderPosition(d)+'</div>';reason.textContent=d.error||d.signal?.reason||(d.signal?.reasons||[]).join(' · ')||'';renderStats(d,stats)}
async function load(){try{const r=await fetch('/analyze',{cache:'no-store'});const j=await r.json();const bad=!r.ok||j.monitoring?.status!=='ok';refresh.textContent=bad?'Poslední kontrola hlásí problém':'Aktualizováno '+new Date().toLocaleTimeString('cs-CZ');refresh.className='refresh '+(bad?'errtxt':'oktxt');runtimeState.textContent=bad?'Některý běh nebo databáze není aktuální.':'Fixed i Scanner běží na pozadí a uložený stav je ověřen.';runtimeState.className=bad?'red':'ok';card(j.fixed,fixed,fixedReason,fixedStats);card(j.scanner,scanner,scannerReason,scannerStats);historyRows(j.scanner,scannerHistory);historyRows(j.fixed,fixedHistory);scan.innerHTML=(j.scanner.scan||[]).map(x=>x.symbol+' · '+x.bucket+' · '+Number(x.strength).toFixed(2)).join('<br>')||'—'}catch(e){refresh.textContent='Aktualizace se nezdařila';refresh.className='refresh errtxt';runtimeState.textContent='Nelze ověřit aktuální běh.';runtimeState.className='red'}}
setInterval(tick,1000);tick();setInterval(load,15000);load();
</script></body></html>'''
