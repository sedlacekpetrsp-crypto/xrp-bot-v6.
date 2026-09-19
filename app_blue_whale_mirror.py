"""
Blue Whale Public Signal Mirror — PAPER ONLY.
Public Telegram captions + public Binance market data. No live orders.
"""
from __future__ import annotations
import asyncio, html, os, re
import psycopg
from psycopg.types.json import Jsonb
from datetime import datetime, timezone
from typing import Optional
import httpx
from market_data import market_get, market
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
DATABASE_URL=os.getenv("DATABASE_URL")

app=FastAPI(title=APP_NAME)
state={"balance":START_BALANCE,"equity":START_BALANCE,"open_position":None,"trades":[],"seen_signal_ids":[],"last_scan":None,"last_signal":None,"status":"starting","error":None,"persistence":"memory","persistence_error":None}

def utcnow(): return datetime.now(timezone.utc)

def _persistent_payload():
    return {
        "balance":state["balance"],
        "equity":state["equity"],
        "open_position":state["open_position"],
        "trades":state["trades"][-100:],
        "seen_signal_ids":state["seen_signal_ids"][-200:],
        "last_scan":state["last_scan"],
        "last_signal":state["last_signal"],
    }

def init_persistence():
    if not DATABASE_URL:
        state["persistence"]="memory"
        state["persistence_error"]="DATABASE_URL is not configured"
        return
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS blue_whale_state (
                id integer PRIMARY KEY,
                state jsonb NOT NULL,
                updated_at timestamptz NOT NULL DEFAULT now()
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS blue_whale_trades (
                signal_id bigint PRIMARY KEY,
                side text NOT NULL,
                entry double precision NOT NULL,
                exit double precision NOT NULL,
                qty double precision NOT NULL,
                net_pnl double precision NOT NULL,
                reason text,
                opened_at timestamptz,
                closed_at timestamptz
            )""")
            row=conn.execute("SELECT state FROM blue_whale_state WHERE id=1").fetchone()
            if row and isinstance(row[0],dict):
                saved=row[0]
                for key in ("balance","equity","open_position","trades","seen_signal_ids","last_scan","last_signal"):
                    if key in saved:
                        state[key]=saved[key]
            else:
                conn.execute(
                    "INSERT INTO blue_whale_state (id,state,updated_at) VALUES (1,%s,now()) ON CONFLICT (id) DO NOTHING",
                    (Jsonb(_persistent_payload()),),
                )
        state["persistence"]="postgres"
        state["persistence_error"]=None
    except Exception as e:
        state["persistence"]="memory"
        state["persistence_error"]=repr(e)
        print("PERSISTENCE INIT ERROR {}".format(repr(e)),flush=True)

def save_state():
    if not DATABASE_URL:
        return
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
            conn.execute(
                """INSERT INTO blue_whale_state (id,state,updated_at) VALUES (1,%s,now())
                   ON CONFLICT (id) DO UPDATE SET state=EXCLUDED.state, updated_at=now()""",
                (Jsonb(_persistent_payload()),),
            )
        state["persistence"]="postgres"
        state["persistence_error"]=None
    except Exception as e:
        state["persistence_error"]=repr(e)
        print("PERSISTENCE SAVE ERROR {}".format(repr(e)),flush=True)

def save_trade(trade):
    if not DATABASE_URL:
        return
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
            conn.execute(
                """INSERT INTO blue_whale_trades
                   (signal_id,side,entry,exit,qty,net_pnl,reason,opened_at,closed_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (signal_id) DO UPDATE SET
                     side=EXCLUDED.side, entry=EXCLUDED.entry, exit=EXCLUDED.exit,
                     qty=EXCLUDED.qty, net_pnl=EXCLUDED.net_pnl, reason=EXCLUDED.reason,
                     opened_at=EXCLUDED.opened_at, closed_at=EXCLUDED.closed_at""",
                (trade["signal_id"],trade["side"],trade["entry"],trade["exit"],trade["qty"],trade["net_pnl"],trade.get("reason"),trade.get("opened_at"),trade.get("closed_at")),
            )
    except Exception as e:
        state["persistence_error"]=repr(e)
        print("PERSISTENCE TRADE ERROR {}".format(repr(e)),flush=True)

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
    r=await market_get(client,BINANCE_PRICE_URL,params={"symbol":SYMBOL},timeout=15)
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
    save_state()
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
    save_trade(trade)
    save_state()

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
                save_state()
            except Exception as e:
                state["status"]="error"; state["error"]=repr(e)
            await asyncio.sleep(SCAN_SECONDS)

@app.on_event("startup")
async def startup():
    init_persistence()
    asyncio.create_task(bot_loop())

@app.get("/health")
async def health(): return {"ok":True,"mode":"PAPER","status":state["status"],"error":state["error"],"persistence":state["persistence"],"persistence_error":state["persistence_error"]}

@app.get("/status")
async def status(): return JSONResponse(state)

@app.get("/",response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse("""
<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blue Whale Public Mirror</title>
<style>
body{margin:0;background:#0b1118;color:#edf3f8;font-family:Arial,sans-serif}
.wrap{max-width:1050px;margin:auto;padding:14px}
.card{background:#151c24;border:1px solid #26313d;border-radius:16px;padding:16px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
.coin{background:#10171f;border-radius:12px;padding:12px}
.row{display:flex;justify-content:space-between;gap:12px;margin:7px 0}
.green{color:#5ce68b}.red{color:#ff6b6b}.yellow{color:#ffd166}.muted{opacity:.65}
.trade{display:grid;grid-template-columns:.8fr .7fr 1fr 1fr .8fr;gap:8px;padding:9px 0;border-bottom:1px solid #29343e;font-size:13px}
h1{font-size:24px;margin:0 0 8px}h2{font-size:18px;margin:0 0 12px}
.badge{display:inline-block;padding:5px 9px;border-radius:999px;background:#10271c;color:#5ce68b;font-size:12px;font-weight:700}
@media(max-width:620px){.wrap{padding:10px}.card{padding:13px;border-radius:14px}.trade{grid-template-columns:1fr 1fr;font-size:12px}.trade span:nth-child(5){grid-column:1/-1}}
</style>
</head>
<body><div class="wrap">

<div class="card">
  <h1>🐋 BLUE WHALE PUBLIC MIRROR</h1>
  <div class="muted">PAPER • BTCUSDT • veřejné signály • risk 0,3 % • TP 2R • poplatky + slippage</div>
</div>

<div class="card"><div id="stats" class="grid"></div></div>

<div class="card">
  <h2>📡 Stav bota</h2>
  <div id="statusbox" class="coin">Načítám…</div>
</div>

<div class="card">
  <h2>📈 Otevřená pozice</h2>
  <div id="position" class="coin muted">Načítám…</div>
</div>

<div class="card">
  <h2>🎯 Poslední signál</h2>
  <div id="signal" class="coin muted">Načítám…</div>
</div>

<div class="card">
  <h2>🧾 Poslední obchody</h2>
  <div id="trades"></div>
</div>

<div class="card muted" id="health">Načítám…</div>
</div>

<script>
const f=(n,d=2)=>Number(n||0).toFixed(d);
const cls=n=>Number(n)>=0?'green':'red';

function kv(label,value){
  return '<div class="coin"><div class="muted">'+label+'</div><b>'+value+'</b></div>';
}
function row(label,value,klass=''){
  return '<div class="row"><span>'+label+'</span><b class="'+klass+'">'+value+'</b></div>';
}

async function refresh(){
  try{
    const r=await fetch('/status',{cache:'no-store'});
    const d=await r.json();
    const trades=d.trades||[];
    const wins=trades.filter(x=>Number(x.net_pnl)>0).length;
    const wr=trades.length?100*wins/trades.length:0;
    const total=trades.reduce((a,x)=>a+Number(x.net_pnl||0),0);

    document.getElementById('stats').innerHTML=
      kv('Balance',f(d.balance,2)+' USD')+
      kv('Equity',f(d.equity,2)+' USD')+
      kv('Obchody',trades.length)+
      kv('Win rate',f(wr,1)+' %')+
      kv('Net PnL','<span class="'+cls(total)+'">'+(total>=0?'+':'')+f(total,2)+' USD</span>');

    document.getElementById('statusbox').innerHTML=
      row('Režim','PAPER','green')+
      row('Status',d.status||'—',d.status==='running'?'green':'yellow')+
      row('Obchodní stav',d.open_position?'OBCHOD OTEVŘEN':'⏳ ČEKÁM NA OBCHOD',d.open_position?'green':'yellow')+
      row('Poslední scan',d.last_scan||'—')+
      row('Ukládání',d.persistence||'memory',d.persistence==='postgres'?'green':'yellow')+
      row('Chyba',d.error||d.persistence_error||'žádná',(d.error||d.persistence_error)?'red':'green');

    if(d.open_position){
      const p=d.open_position;
      document.getElementById('position').className='coin';
      document.getElementById('position').innerHTML=
        row('Směr',p.side,p.side==='LONG'?'green':'red')+
        row('Entry',f(p.entry,2)+' USD')+
        row('SL',f(p.stop,2)+' USD','red')+
        row('TP',f(p.tp,2)+' USD','green')+
        row('Risk',f(p.risk_dollars,2)+' USD')+
        row('Notional',f(p.notional,2)+' USD')+
        '<div class="muted">Signal ID: '+p.signal_id+'</div>';
    }else{
      document.getElementById('position').className='coin muted';
      document.getElementById('position').innerHTML='<b class="yellow">⏳ ČEKÁM NA OBCHOD</b><div style="margin-top:6px">Žádná otevřená pozice.</div>';
    }

    if(d.last_signal){
      const s=d.last_signal;
      const side=s.side||'WAIT';
      document.getElementById('signal').className='coin';
      document.getElementById('signal').innerHTML=
        row('Signal ID',s.id||'—')+
        row('Směr',side,side==='LONG'?'green':side==='SHORT'?'red':'yellow')+
        row('SL',s.stop_raw||'—')+
        (s.rejected?row('Výsledek',s.rejected,'yellow'):'')+
        (s.age_minutes!=null?row('Stáří',f(s.age_minutes,1)+' min'):'');
    }else{
      document.getElementById('signal').className='coin muted';
      document.getElementById('signal').innerHTML='Čekám na nový veřejný BTC signál.';
    }

    document.getElementById('trades').innerHTML=trades.slice().reverse().slice(0,30).map(t=>
      '<div class="trade">'+
      '<span>#'+t.signal_id+'</span>'+
      '<span class="'+(t.side==='LONG'?'green':'red')+'">'+t.side+'</span>'+
      '<span>'+f(t.entry,2)+' → '+f(t.exit,2)+'</span>'+
      '<span>'+t.reason+'</span>'+
      '<span class="'+cls(t.net_pnl)+'">'+(Number(t.net_pnl)>=0?'+':'')+f(t.net_pnl,2)+' USD</span>'+
      '</div>'
    ).join('') || '<div class="coin muted">Zatím žádné uzavřené obchody.</div>';

    document.getElementById('health').textContent=
      'Blue Whale Public Mirror • PAPER ONLY • kontrola nového signálu každých 60 s';
  }catch(e){
    document.getElementById('health').textContent='Dashboard error: '+e;
  }
}
refresh();
setInterval(refresh,5000);
</script>
</body></html>
""", headers={"Cache-Control":"no-store, no-cache, must-revalidate"})
