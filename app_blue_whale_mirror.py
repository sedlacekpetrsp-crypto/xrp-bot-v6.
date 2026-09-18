"""
Blue Whale Public Signal Mirror — PAPER ONLY.
Public Telegram captions + public Binance market data. No live orders.
"""
from __future__ import annotations
import asyncio, html, os, re
from datetime import datetime, timezone
from typing import Optional
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

APP_NAME="Blue Whale Public Mirror — PAPER"
SYMBOL="BTCUSDT"
TELEGRAM_URL="https://t.me/s/BlueWhaleCryptoTrading"
BINANCE_PRICE_URL="https://data-api.binance.vision/api/v3/ticker/price"
START_BALANCE=float(os.getenv("START_BALANCE","10000"))
RISK_PER_TRADE=float(os.getenv("RISK_PER_TRADE","0.003"))
RR=float(os.getenv("RR","2.0"))
FEE_RATE=float(os.getenv("FEE_RATE","0.0005"))
SLIPPAGE_RATE=float(os.getenv("SLIPPAGE_RATE","0.0002"))
MAX_HOLD_HOURS=float(os.getenv("MAX_HOLD_HOURS","48"))
SCAN_SECONDS=int(os.getenv("SCAN_SECONDS","60"))
MAX_SIGNAL_AGE_MINUTES=float(os.getenv("MAX_SIGNAL_AGE_MINUTES","15"))

app=FastAPI(title=APP_NAME)
state={"balance":START_BALANCE,"equity":START_BALANCE,"open_position":None,"trades":[],"seen_signal_ids":[],"last_scan":None,"last_signal":None,"status":"starting","error":None}

def utcnow(): return datetime.now(timezone.utc)

def clean_text(raw):
    raw=re.sub(r"<br\s*/?>","\n",raw,flags=re.I)
    raw=re.sub(r"<[^>]+>"," ",raw)
    raw=html.unescape(raw)
    raw=re.sub(r"[ \t\r\f\v]+"," ",raw)
    return raw.strip()

def parse_stop(text):
    u=text.upper()
    m=re.search(r"\bSL\s*[:=]?\s*([0-9]{2,3}(?:,[0-9]{1,3})?(?:X{1,3})?)",u)
    if not m: return None
    shown=m.group(1); raw=shown.replace(",","")
    if "X" not in raw:
        try:
            v=float(raw)
            if v<10000:return None
            return {"raw":shown,"low":v,"high":v,"masked":False}
        except ValueError:return None
    n=raw.count("X"); prefix=raw[:-n]
    if not prefix.isdigit():return None
    low=float(int(prefix)*(10**n))
    return {"raw":shown,"low":low,"high":low+(10**n)-1,"masked":True}

def explicit_side(text)->Optional[str]:
    u=text.upper()
    lg=bool(re.search(r"\bLONG\b",u)); sh=bool(re.search(r"\bSHORT\b",u))
    if lg and not sh:return "LONG"
    if sh and not lg:return "SHORT"
    return None

def infer_side(text,stop,price):
    s=explicit_side(text)
    if s:return s
    if stop["high"]<price*0.995:return "LONG"
    if stop["low"]>price*1.005:return "SHORT"
    return None

def effective_stop(side,stop):
    if side=="LONG":return stop["high"] if stop["masked"] else stop["low"]
    return stop["low"] if stop["masked"] else stop["high"]

async def btc_price(client):
    r=await client.get(BINANCE_PRICE_URL,params={"symbol":SYMBOL},timeout=15)
    r.raise_for_status()
    return float(r.json()["price"])

async def latest_signal(client):
    r=await client.get(TELEGRAM_URL,headers={"User-Agent":"Mozilla/5.0 BlueWhalePaperMirror/1.0"},timeout=20)
    r.raise_for_status()
    chunks=re.split(r'(?=<div class="tgme_widget_message_wrap)',r.text)
    candidates=[]
    for ch in chunks:
        mid=re.search(r'data-post="BlueWhaleCryptoTrading/(\d+)"',ch)
        if not mid:continue
        tm=re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>',ch,flags=re.S)
        dtm=re.search(r'<time[^>]+datetime="([^"]+)"',ch)
        text=clean_text(tm.group(1)) if tm else ""
        if "BTC" not in text.upper():continue
        stop=parse_stop(text)
        if stop:
            posted_at=None
            if dtm:
                try: posted_at=datetime.fromisoformat(dtm.group(1).replace("Z","+00:00"))
                except Exception: posted_at=None
            candidates.append({"id":int(mid.group(1)),"text":text,"stop":stop,"posted_at":posted_at.isoformat() if posted_at else None})
    return max(candidates,key=lambda x:x["id"]) if candidates else None

def mark_to_market(price):
    p=state["open_position"]
    if not p:
        state["equity"]=state["balance"]; return
    gross=(price-p["entry"])*p["qty"] if p["side"]=="LONG" else (p["entry"]-price)*p["qty"]
    state["equity"]=state["balance"]+gross-price*p["qty"]*FEE_RATE

def open_paper(signal,side,market_price):
    entry=market_price*(1+SLIPPAGE_RATE if side=="LONG" else 1-SLIPPAGE_RATE)
    stop=effective_stop(side,signal["stop"])
    stop_rate=(entry-stop)/entry if side=="LONG" else (stop-entry)/entry
    if stop_rate<=0 or stop_rate>0.10:return False
    risk=state["balance"]*RISK_PER_TRADE
    eff=stop_rate+2*(FEE_RATE+SLIPPAGE_RATE)
    notional=risk/eff; qty=notional/entry
    move=RR*eff
    tp=entry*(1+move) if side=="LONG" else entry*(1-move)
    entry_fee=entry*qty*FEE_RATE
    state["balance"]-=entry_fee
    state["open_position"]={"signal_id":signal["id"],"signal_text":signal["text"],"side":side,"entry":entry,"stop":stop,"tp":tp,"qty":qty,"notional":notional,"risk_dollars":risk,"opened_at":utcnow().isoformat(),"entry_fee":entry_fee}
    state["last_signal"]={"id":signal["id"],"side":side,"stop_raw":signal["stop"]["raw"],"accepted_at":utcnow().isoformat()}
    return True

def close_paper(price,reason):
    p=state["open_position"]
    if not p:return
    exit_price=price*(1-SLIPPAGE_RATE if p["side"]=="LONG" else 1+SLIPPAGE_RATE)
    gross=(exit_price-p["entry"])*p["qty"] if p["side"]=="LONG" else (p["entry"]-exit_price)*p["qty"]
    exit_fee=exit_price*p["qty"]*FEE_RATE
    net_after_exit=gross-exit_fee
    state["balance"]+=net_after_exit
    trade={**p,"exit":exit_price,"exit_fee":exit_fee,"net_pnl":net_after_exit-p["entry_fee"],"closed_at":utcnow().isoformat(),"reason":reason}
    state["trades"].append(trade); state["trades"]=state["trades"][-100:]
    state["open_position"]=None; state["equity"]=state["balance"]

def age_hours():
    p=state["open_position"]
    if not p:return 0
    return (utcnow()-datetime.fromisoformat(p["opened_at"])).total_seconds()/3600

async def bot_loop():
    await asyncio.sleep(2)
    async with httpx.AsyncClient() as client:
        while True:
            try:
                price=await btc_price(client)
                state["last_scan"]=utcnow().isoformat(); state["status"]="running"; state["error"]=None
                p=state["open_position"]
                if p:
                    mark_to_market(price)
                    if (price<=p["stop"] if p["side"]=="LONG" else price>=p["stop"]):close_paper(p["stop"],"SL")
                    elif (price>=p["tp"] if p["side"]=="LONG" else price<=p["tp"]):close_paper(p["tp"],"TP")
                    elif age_hours()>=MAX_HOLD_HOURS:close_paper(price,"TIME")
                else:
                    s=await latest_signal(client)
                    if s and s["id"] not in state["seen_signal_ids"]:
                        state["seen_signal_ids"].append(s["id"]); state["seen_signal_ids"]=state["seen_signal_ids"][-200:]
                        posted=datetime.fromisoformat(s["posted_at"]) if s.get("posted_at") else None
                        age_min=((utcnow()-posted).total_seconds()/60.0) if posted else None
                        if age_min is None or age_min>MAX_SIGNAL_AGE_MINUTES:
                            state["last_signal"]={"id":s["id"],"side":None,"stop_raw":s["stop"]["raw"],"rejected":"stale public signal","age_minutes":age_min,"seen_at":utcnow().isoformat()}
                            print("REJECT stale signal id={} age_min={}".format(s["id"],age_min),flush=True)
                        else:
                            side=infer_side(s["text"],s["stop"],price)
                            if side:
                                ok=open_paper(s,side,price)
                                print("OPEN paper id={} side={} ok={} price={}".format(s["id"],side,ok,price),flush=True)
                            else:
                                state["last_signal"]={"id":s["id"],"side":None,"stop_raw":s["stop"]["raw"],"rejected":"direction unclear","age_minutes":age_min,"seen_at":utcnow().isoformat()}
                                print("REJECT unclear direction id={}".format(s["id"]),flush=True)
            except Exception as e:
                state["status"]="error"; state["error"]=repr(e)
            await asyncio.sleep(SCAN_SECONDS)

@app.on_event("startup")
async def startup(): asyncio.create_task(bot_loop())

@app.get("/health")
async def health(): return {"ok":True,"mode":"PAPER","status":state["status"],"error":state["error"]}

@app.get("/status")
async def status(): return JSONResponse(state)

@app.get("/",response_class=HTMLResponse)
async def dashboard():
    p=state["open_position"]; trades=state["trades"]; wins=sum(1 for t in trades if t["net_pnl"]>0); wr=100*wins/len(trades) if trades else 0
    pos="Žádná otevřená pozice." if not p else f"{p['side']} BTC | entry {p['entry']:.2f} | SL {p['stop']:.2f} | TP {p['tp']:.2f}"
    rows="".join(f"<tr><td>{t['signal_id']}</td><td>{t['side']}</td><td>{t['entry']:.2f}</td><td>{t['exit']:.2f}</td><td>{t['reason']}</td><td>{t['net_pnl']:.2f}</td></tr>" for t in reversed(trades[-20:]))
    return f"""<html><body style='font-family:Arial;max-width:980px;margin:32px auto'>
    <h1>{APP_NAME}</h1><p><b>PAPER ONLY</b></p>
    <p>Balance: <b>{state['balance']:.2f} USD</b> | Equity: <b>{state['equity']:.2f} USD</b> | Trades: {len(trades)} | Winrate: {wr:.1f}%</p>
    <h2>Open position</h2><p>{pos}</p>
    <h2>Last signal</h2><pre>{state['last_signal']}</pre>
    <h2>Recent trades</h2><table border='1' cellpadding='6'><tr><th>Signal</th><th>Side</th><th>Entry</th><th>Exit</th><th>Reason</th><th>Net PnL</th></tr>{rows}</table>
    <p>Public-signal mirror. Hidden VIP entry/TP are not guessed. No live orders.</p></body></html>"""
