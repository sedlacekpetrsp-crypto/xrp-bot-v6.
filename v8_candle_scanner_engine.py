import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="V8 Candle Scanner")

BINANCE_API = os.getenv("BINANCE_API", "https://data-api.binance.vision")
SYMBOLS = [s.strip().upper() for s in os.getenv(
    "SCANNER_SYMBOLS",
    "XRPUSDT,SOLUSDT,ETHUSDT,DOGEUSDT,ADAUSDT,SUIUSDT,LINKUSDT,AVAXUSDT,HBARUSDT,FETUSDT,DOTUSDT,ATOMUSDT,NEARUSDT,ARBUSDT,RENDERUSDT"
).split(",") if s.strip()]

STARTING_BALANCE = float(os.getenv("STARTING_BALANCE", "10000"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.003"))
RISK_REWARD = float(os.getenv("RISK_REWARD", "2.0"))
FEE_RATE = float(os.getenv("FEE_RATE", "0.0005"))
SLIPPAGE_RATE = float(os.getenv("SLIPPAGE_RATE", "0.0002"))
MAX_NOTIONAL_SHARE = float(os.getenv("MAX_NOTIONAL_SHARE", "0.50"))
MIN_VOLUME_RATIO = float(os.getenv("MIN_VOLUME_RATIO", "1.20"))
MIN_TREND_STRENGTH = float(os.getenv("MIN_TREND_STRENGTH", "0.0012"))
TOP_N = int(os.getenv("TOP_N", "5"))
SCAN_SECONDS = int(os.getenv("SCAN_SECONDS", "60"))
MAX_TRADE_MINUTES = int(os.getenv("MAX_TRADE_MINUTES", "120"))
COOLDOWN_AFTER_LOSS_MIN = int(os.getenv("COOLDOWN_AFTER_LOSS_MIN", "30"))

paper_balance = STARTING_BALANCE
paper_position: Optional[Dict[str, Any]] = None
history: List[Dict[str, Any]] = []
last_scan: List[Dict[str, Any]] = []
last_signal: Dict[str, Any] = {"side": "WAIT"}
cooldown_until: Optional[datetime] = None
bot_task = None


def c(k):
    return {"t": int(k[0]), "o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "v": float(k[5])}

def ema(vals, period):
    if len(vals) < period: return None
    a = 2/(period+1)
    e = sum(vals[:period])/period
    for x in vals[period:]: e = a*x + (1-a)*e
    return e

def bullish(x): return x["c"] > x["o"]
def bearish(x): return x["c"] < x["o"]
def body(x): return abs(x["c"]-x["o"])
def rng(x): return max(x["h"]-x["l"], 1e-12)

def bull_engulf(a,b):
    return bearish(a) and bullish(b) and b["o"] <= a["c"] and b["c"] >= a["o"] and body(b) > body(a)

def bear_engulf(a,b):
    return bullish(a) and bearish(b) and b["o"] >= a["c"] and b["c"] <= a["o"] and body(b) > body(a)

async def klines(client, symbol, interval, limit):
    r = await client.get(f"{BINANCE_API}/api/v3/klines", params={"symbol":symbol,"interval":interval,"limit":limit}, timeout=15)
    r.raise_for_status(); return r.json()

async def price(client, symbol):
    r = await client.get(f"{BINANCE_API}/api/v3/ticker/price", params={"symbol":symbol}, timeout=15)
    r.raise_for_status(); return float(r.json()["price"])

async def strength_for(client, symbol):
    try:
        h1, h4 = await asyncio.gather(klines(client,symbol,"1h",6), klines(client,symbol,"4h",6))
        h1 = [c(x) for x in h1][:-1]; h4 = [c(x) for x in h4][:-1]
        m1 = (h1[-1]["c"]/h1[-5]["o"]-1)*100 if len(h1)>=5 else 0
        m4 = (h4[-1]["c"]/h4[-3]["o"]-1)*100 if len(h4)>=3 else 0
        score = 0.65*m1 + 0.35*m4
        return {"symbol":symbol,"m1h":m1,"m4h":m4,"strength":score}
    except Exception:
        return None

async def build_scan(client):
    rows = [r for r in await asyncio.gather(*(strength_for(client,s) for s in SYMBOLS)) if r]
    rows.sort(key=lambda x:x["strength"], reverse=True)
    longs = {x["symbol"] for x in rows[:TOP_N]}
    shorts = {x["symbol"] for x in rows[-TOP_N:]}
    for x in rows:
        x["bucket"] = "LONG" if x["symbol"] in longs else "SHORT" if x["symbol"] in shorts else "NEUTRAL"
    return rows

async def signal_for(client, row):
    symbol=row["symbol"]
    try:
        raw5, raw15 = await asyncio.gather(klines(client,symbol,"5m",40), klines(client,symbol,"15m",70))
        m=[c(x) for x in raw5][:-1]; s=[c(x) for x in raw15][:-1]
        a,b,conf=m[-3],m[-2],m[-1]
        avg_vol=sum(x["v"] for x in m[-22:-2])/20
        vol=conf["v"]/avg_vol if avg_vol else 0
        closes=[x["c"] for x in s]
        e20,e50=ema(closes,20),ema(closes,50)
        if not e20 or not e50: return None
        trend="LONG" if e20>e50 else "SHORT"
        trend_strength=abs(e20-e50)/conf["c"]
        side=None; setup=None; p_low=None; p_high=None
        if bull_engulf(a,b) and conf["c"]>b["h"]:
            side="LONG"; setup="BULLISH_ENGULFING"; p_low=min(b["l"],conf["l"]); p_high=max(b["h"],conf["h"])
        elif bear_engulf(a,b) and conf["c"]<b["l"]:
            side="SHORT"; setup="BEARISH_ENGULFING"; p_low=min(b["l"],conf["l"]); p_high=max(b["h"],conf["h"])
        if not side: return None
        if side != row["bucket"] or side != trend: return None
        if vol < MIN_VOLUME_RATIO or trend_strength < MIN_TREND_STRENGTH: return None
        return {"symbol":symbol,"side":side,"setup":setup,"entry":conf["c"],"pattern_low":p_low,"pattern_high":p_high,
                "volume_ratio":vol,"trend_strength":trend_strength,"strength":row["strength"],"candle_time":conf["t"]}
    except Exception:
        return None


def est_net_unit(side, entry, exit_market):
    exit_exec=exit_market*(1-SLIPPAGE_RATE if side=="LONG" else 1+SLIPPAGE_RATE)
    gross=(exit_exec-entry) if side=="LONG" else (entry-exit_exec)
    return gross-(entry+exit_exec)*FEE_RATE

def target_for_net(side, entry, target):
    f,s=FEE_RATE,SLIPPAGE_RATE
    if side=="LONG":
        ex=(target+entry*(1+f))/(1-f); return ex/(1-s)
    ex=(entry*(1-f)-target)/(1+f); return ex/(1+s)

def open_position(sig):
    global paper_position
    side=sig["side"]; market=sig["entry"]
    entry=market*(1+SLIPPAGE_RATE if side=="LONG" else 1-SLIPPAGE_RATE)
    buf=market*0.0002
    stop=(sig["pattern_low"]-buf) if side=="LONG" else (sig["pattern_high"]+buf)
    loss=-est_net_unit(side,entry,stop)
    if loss<=0: return False
    qty=min((paper_balance*RISK_PER_TRADE)/loss, (paper_balance*MAX_NOTIONAL_SHARE)/entry)
    if qty<=0: return False
    tp=target_for_net(side,entry,loss*RISK_REWARD)
    paper_position={**sig,"entry_price":entry,"stop_loss":stop,"take_profit":tp,"qty":qty,"risk_usdt":qty*loss,"entry_time":datetime.now(timezone.utc).isoformat()}
    return True

def close_position(market, reason):
    global paper_balance,paper_position,cooldown_until
    if not paper_position: return
    p=paper_position
    ex=market*(1-SLIPPAGE_RATE if p["side"]=="LONG" else 1+SLIPPAGE_RATE)
    gross=(ex-p["entry_price"])*p["qty"] if p["side"]=="LONG" else (p["entry_price"]-ex)*p["qty"]
    fees=(p["entry_price"]*p["qty"]+ex*p["qty"])*FEE_RATE
    net=gross-fees; paper_balance+=net
    history.insert(0,{**p,"exit_price":ex,"net_pnl":net,"reason":reason,"exit_time":datetime.now(timezone.utc).isoformat()})
    del history[30:]
    if net<0: cooldown_until=datetime.now(timezone.utc)+timedelta(minutes=COOLDOWN_AFTER_LOSS_MIN)
    paper_position=None

async def cycle():
    global last_scan,last_signal
    async with httpx.AsyncClient() as client:
        last_scan=await build_scan(client)
        if paper_position:
            px=await price(client,paper_position["symbol"])
            p=paper_position
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(p["entry_time"])).total_seconds()/60
            if p["side"]=="LONG":
                if px<=p["stop_loss"]: close_position(px,"STOP_LOSS")
                elif px>=p["take_profit"]: close_position(px,"TAKE_PROFIT")
            else:
                if px>=p["stop_loss"]: close_position(px,"STOP_LOSS")
                elif px<=p["take_profit"]: close_position(px,"TAKE_PROFIT")
            if paper_position and age>=MAX_TRADE_MINUTES: close_position(px,"TIME_EXIT")
        cd=bool(cooldown_until and datetime.now(timezone.utc)<cooldown_until)
        if not paper_position and not cd:
            watch=[r for r in last_scan if r["bucket"] in ("LONG","SHORT")]
            signals=[s for s in await asyncio.gather(*(signal_for(client,r) for r in watch)) if s]
            if signals:
                signals.sort(key=lambda x:abs(x["strength"]), reverse=True)
                last_signal=signals[0]; open_position(last_signal)
            else:
                last_signal={"side":"WAIT","reason":"No confirmed engulfing setup in top/bottom strength groups"}
        eq=paper_balance
        upnl=0.0
        if paper_position:
            px=await price(client,paper_position["symbol"])
            upnl=est_net_unit(paper_position["side"],paper_position["entry_price"],px)*paper_position["qty"]
            eq+=upnl
        return {"bot":"V8 Candle Scanner","mode":"PAPER","balance":paper_balance,"equity":eq,"unrealized_pnl":upnl,
                "position":paper_position,"signal":last_signal,"scan":last_scan,"history":history,"top_n":TOP_N,
                "risk_per_trade":RISK_PER_TRADE,"risk_reward":RISK_REWARD,"time":datetime.now(timezone.utc).isoformat()}

async def loop():
    while True:
        try: await cycle()
        except Exception as e: print("SCANNER LOOP ERROR",repr(e))
        await asyncio.sleep(SCAN_SECONDS)

@app.on_event("startup")
async def startup():
    global bot_task
    bot_task=asyncio.create_task(loop())

@app.get("/health")
async def health():
    return {"status":"ok","bot":"V8 Candle Scanner","symbols":len(SYMBOLS),"strategy":"market strength + engulfing + 15m trend + volume","rr":"1:2"}

@app.get("/analyze")
async def analyze():
    try: return JSONResponse(await cycle())
    except Exception as e: return JSONResponse({"ok":False,"error":str(e)},status_code=500)

@app.get("/",response_class=HTMLResponse)
async def dashboard():
    return '''<!doctype html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V8 Candle Scanner</title>
<style>body{margin:0;background:#07111f;color:#f4f7fb;font-family:system-ui}.w{max-width:920px;margin:auto;padding:18px}.card{background:#0f1b2d;border:1px solid #243650;border-radius:18px;padding:18px;margin:12px 0}.row{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.big{font-size:34px;font-weight:800}.muted{color:#8ea1b8}.green{color:#21d19f}.red{color:#ff647c}.amber{color:#f8c55c}table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #243650;text-align:left;font-size:13px}@media(max-width:650px){.row{grid-template-columns:1fr}.big{font-size:29px}}</style></head>
<body><div class="w"><h1>V8 Candle Scanner</h1><div class="muted">Market strength + ENGULFING + 15m trend + volume · PAPER</div>
<div class="row"><div class="card"><div class="muted">BALANCE</div><div id="bal" class="big">-</div></div><div class="card"><div class="muted">EQUITY</div><div id="eq" class="big">-</div></div></div>
<div class="card"><h2>Aktuální pozice</h2><div id="pos">Načítám…</div></div><div class="card"><h2>Market scanner</h2><div id="scan">Načítám…</div></div><div class="card"><h2>Poslední obchody</h2><div id="hist">Načítám…</div></div></div>
<script>async function go(){let d=await (await fetch('/analyze')).json();bal.textContent=d.balance.toFixed(2)+' USDT';eq.textContent=d.equity.toFixed(2)+' USDT';pos.innerHTML=d.position?`<b>${d.position.symbol}</b> <span class="${d.position.side==='LONG'?'green':'red'}">${d.position.side}</span><br>Entry ${d.position.entry_price.toFixed(5)} · SL ${d.position.stop_loss.toFixed(5)} · TP ${d.position.take_profit.toFixed(5)}`:'Žádná otevřená pozice';scan.innerHTML='<table><tr><th>Coin</th><th>1h</th><th>4h</th><th>Strength</th><th>Směr</th></tr>'+d.scan.map(x=>`<tr><td>${x.symbol}</td><td>${x.m1h.toFixed(2)}%</td><td>${x.m4h.toFixed(2)}%</td><td>${x.strength.toFixed(2)}</td><td class="${x.bucket==='LONG'?'green':x.bucket==='SHORT'?'red':'muted'}">${x.bucket}</td></tr>`).join('')+'</table>';hist.innerHTML=d.history.length?d.history.map(x=>`<div>${x.symbol} ${x.side} · ${x.reason} · <b>${x.net_pnl.toFixed(2)} USDT</b></div>`).join(''):'Zatím bez uzavřených obchodů'}go();setInterval(go,15000)</script></body></html>'''
