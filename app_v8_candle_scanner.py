import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

import app_v8_candle as fixed
import v8_candle_scanner_engine as scanner

BUILD = "history-cards-v4"
app = FastAPI(title="V8 Candle Combined")

fixed_task = None
scanner_task = None


@app.on_event("startup")
async def startup():
    global fixed_task, scanner_task
    try:
        fixed.init_db()
        fixed.load_state()
    except Exception as e:
        print("FIXED DB STARTUP ERROR", repr(e))
    fixed_task = asyncio.create_task(fixed.bot_loop())
    scanner_task = asyncio.create_task(scanner.loop())


@app.on_event("shutdown")
async def shutdown():
    for task in (fixed_task, scanner_task):
        if task:
            task.cancel()
    for task in (fixed_task, scanner_task):
        if task:
            try:
                await task
            except asyncio.CancelledError:
                pass


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "V8 Candle Combined",
        "build": BUILD,
        "fixed": {
            "running": bool(fixed_task and not fixed_task.done()),
            "strategy": "XRP breakout/momentum + 15m trend + volume",
            "rr": fixed.RISK_REWARD,
        },
        "scanner": {
            "running": bool(scanner_task and not scanner_task.done()),
            "symbols": len(scanner.SYMBOLS),
            "strategy": "market strength + breakout/momentum + 15m trend + volume",
            "rr": scanner.RISK_REWARD,
        },
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/fixed/analyze")
async def fixed_analyze():
    try:
        return JSONResponse(await fixed.analyze_once())
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/scanner/analyze")
async def scanner_analyze():
    try:
        return JSONResponse(await scanner.cycle())
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/analyze")
async def analyze():
    fixed_data, scanner_data = await asyncio.gather(
        fixed.analyze_once(), scanner.cycle(), return_exceptions=True
    )
    return JSONResponse({
        "fixed": fixed_data if not isinstance(fixed_data, Exception) else {"ok": False, "error": str(fixed_data)},
        "scanner": scanner_data if not isinstance(scanner_data, Exception) else {"ok": False, "error": str(scanner_data)},
        "time": datetime.now(timezone.utc).isoformat(),
    })


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
</style></head>
<body><div class="w">
<div class="clockbar"><div><div class="muted">AKTUÁLNÍ ČAS</div><div id="clock" class="clock">--:--:--</div></div><div id="refresh" class="refresh">Data se načítají…</div></div>
<h1>V8 Candle Combined</h1><div class="muted">Fixed + Scanner · PAPER · Průraz / momentum · bez engulfingu · bez pauzy po ztrátě (v3)</div>
<div class="grid"><div class="card"><h2>V8 Candle Fixed</h2><div id="fixed">Načítám…</div><p id="fixedReason" class="wait"></p></div><div class="card"><h2>V8 Candle Scanner</h2><div id="scanner">Načítám…</div><p id="scannerReason" class="wait"></p></div></div>
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
function historyTime(value){
 const d=new Date(value);return value&&!isNaN(d)?d.toLocaleString('cs-CZ',{day:'numeric',month:'numeric',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'}):'—';
}
function renderHistory(target, rows){
 target.replaceChildren();
 if(!rows.length){target.appendChild(historyNode('div','trade-empty','Zatím žádné uzavřené obchody'));return;}
 const setups={MOMENTUM_BREAKOUT:'Průraz',MOMENTUM:'Momentum',BULLISH_ENGULFING:'Býčí engulfing (starší strategie)',BEARISH_ENGULFING:'Medvědí engulfing (starší strategie)'};
 const reasons={STOP_LOSS:'Stop-loss',TAKE_PROFIT:'Dosažený cíl',TIME_EXIT:'Časový limit',BREAK_EVEN:'Výstup na nule'};
 for(const t of rows.slice(0,20)){
  const item=historyNode('article','trade-card');
  const head=historyNode('div','trade-head');
  const identity=historyNode('div','trade-identity');
  identity.append(historyNode('span','trade-coin',(t.symbol||'XRPUSDT').replace(/USDT$/,' / USDT')),historyNode('span','trade-badge '+(t.side==='LONG'?'long':'short'),t.side||'—'));
  const result=historyNode('div','trade-result');const net=Number(t.net_pnl);
  result.append(historyNode('span','trade-label','Čistý výsledek'),historyNode('strong',net>0?'ok':net<0?'red':'muted',(net>0?'+':'')+historyNumber(t.net_pnl,2)+' USDT'));
  head.append(identity,result);item.appendChild(head);
  const prices=historyNode('div','trade-prices');
  for(const [label,value] of [['Vstupní cena',t.entry_price],['Výstupní cena',t.exit_price]]){
   const cell=historyNode('div','trade-price');cell.append(historyNode('span','trade-label',label),historyNode('span','',historyNumber(value,5)));prices.appendChild(cell);
  }
  item.appendChild(prices);const footer=historyNode('div','trade-footer');
  for(const [label,value] of [['Strategie',setups[t.setup]||t.setup||'—'],['Ukončení',reasons[t.reason]||t.reason||'—'],['Otevřeno',historyTime(t.entry_time)],['Uzavřeno',historyTime(t.exit_time)]]){
   const detail=historyNode('div','trade-detail');detail.append(historyNode('span','',label),historyNode('span','',value));footer.appendChild(detail);
  }
  item.appendChild(footer);target.appendChild(item);
 }
}
async function go(){
 try{
  const d=await (await fetch('/analyze',{cache:'no-store'})).json();
  const f=d.fixed||{}, s=d.scanner||{};
  fixed.innerHTML=f.error?`<span class="red">ERROR: ${f.error}</span>`:`<div class="big">${f.position?f.position.side:'WAIT'}</div><div>Balance: ${(f.balance||0).toFixed(2)} USDT</div><div>Equity: ${(f.equity||0).toFixed(2)} USDT</div><div class="muted">${f.position?'Pozice otevřená':'Bez otevřené pozice'}</div>`;
  scanner.innerHTML=s.error?`<span class="red">ERROR: ${s.error}</span>`:`<div class="big">${s.position?s.position.side:'WAIT'}</div><div>Balance: ${(s.balance||0).toFixed(2)} USDT</div><div>Equity: ${(s.equity||0).toFixed(2)} USDT</div><div class="muted">${s.position?s.position.symbol+' '+s.position.side:'Bez otevřené pozice'}</div>`;
  fixedReason.textContent=f.position?'Pozice otevřená':f.cooldown_until&&new Date(f.cooldown_until)>new Date()?'Pauza po ztrátě':(f.signal?.reasons||[]).join(' · ');
  scannerReason.textContent=s.position?'Pozice otevřená':s.cooldown_until&&new Date(s.cooldown_until)>new Date()?'Pauza po ztrátě':s.signal?.reason||'Čekám na splnění vstupních podmínek';
  renderHistory(scannerHistory,s.history||[]);
  renderHistory(fixedHistory,f.history||[]);
  const rows=s.scan||[];
  scan.innerHTML='<table><tr><th>Coin</th><th>1h</th><th>4h</th><th>Strength</th><th>Směr</th></tr>'+rows.map(x=>`<tr><td>${x.symbol}</td><td>${x.m1h.toFixed(2)}%</td><td>${x.m4h.toFixed(2)}%</td><td>${x.strength.toFixed(2)}</td><td class="${x.bucket==='LONG'?'ok':x.bucket==='SHORT'?'red':'muted'}"><b>${x.bucket}</b></td></tr>`).join('')+'</table>';
  const t=d.time?new Date(d.time):new Date();
  refresh.className='refresh oktxt';
  refresh.textContent='Data aktualizována: '+t.toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
 }catch(e){
  refresh.className='refresh errtxt';
  refresh.textContent='Chyba aktualizace dat';
 }
}
tick();setInterval(tick,1000);go();setInterval(go,15000);
</script></body></html>'''
