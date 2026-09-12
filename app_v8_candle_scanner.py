import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

import app_v8_candle as fixed
import v8_candle_scanner_engine as scanner

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
        "fixed": {
            "running": bool(fixed_task and not fixed_task.done()),
            "strategy": "XRP engulfing + 15m trend + volume",
            "rr": fixed.RISK_REWARD,
        },
        "scanner": {
            "running": bool(scanner_task and not scanner_task.done()),
            "symbols": len(scanner.SYMBOLS),
            "strategy": "market strength + engulfing + 15m trend + volume",
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
body{margin:0;background:#07111f;color:#f4f7fb;font-family:system-ui}.w{max-width:980px;margin:auto;padding:18px}.card{background:#0f1b2d;border:1px solid #243650;border-radius:18px;padding:18px;margin:12px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.muted{color:#8ea1b8}.ok{color:#21d19f}.wait{color:#f8c55c}.red{color:#ff647c}.big{font-size:28px;font-weight:800}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #243650;text-align:left;font-size:13px}@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style></head>
<body><div class="w"><h1>V8 Candle Combined</h1><div class="muted">Jeden Render proces · Fixed + Scanner · PAPER</div>
<div class="grid"><div class="card"><h2>V8 Candle Fixed</h2><div id="fixed">Načítám…</div></div><div class="card"><h2>V8 Candle Scanner</h2><div id="scanner">Načítám…</div></div></div>
<div class="card"><h2>Scanner trhu</h2><div id="scan">Načítám…</div></div></div>
<script>
async function go(){
 const d=await (await fetch('/analyze')).json();
 const f=d.fixed||{}, s=d.scanner||{};
 fixed.innerHTML=f.error?`<span class="red">ERROR: ${f.error}</span>`:`<div class="big">${(f.signal&&f.signal.side)||'WAIT'}</div><div>Balance: ${(f.balance||0).toFixed(2)} USDT</div><div>Equity: ${(f.equity||0).toFixed(2)} USDT</div><div class="muted">${f.position?'Pozice otevřená':'Bez otevřené pozice'}</div>`;
 scanner.innerHTML=s.error?`<span class="red">ERROR: ${s.error}</span>`:`<div class="big">${(s.signal&&s.signal.side)||'WAIT'}</div><div>Balance: ${(s.balance||0).toFixed(2)} USDT</div><div>Equity: ${(s.equity||0).toFixed(2)} USDT</div><div class="muted">${s.position?s.position.symbol+' '+s.position.side:'Bez otevřené pozice'}</div>`;
 const rows=s.scan||[];
 scan.innerHTML='<table><tr><th>Coin</th><th>1h</th><th>4h</th><th>Strength</th><th>Směr</th></tr>'+rows.map(x=>`<tr><td>${x.symbol}</td><td>${x.m1h.toFixed(2)}%</td><td>${x.m4h.toFixed(2)}%</td><td>${x.strength.toFixed(2)}</td><td>${x.bucket}</td></tr>`).join('')+'</table>';
}
go();setInterval(go,15000);
</script></body></html>'''
