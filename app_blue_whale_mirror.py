"""
Blue Whale Fibonacci 0.618–0.786 + VWAP reversion — PAPER ONLY.
Public market data; persistent simulated positions. No live orders.
"""
from __future__ import annotations
import news_signal
import asyncio, html, os, re, math, hashlib, time
import psycopg
from psycopg.types.json import Jsonb
from datetime import datetime, timezone
from typing import Optional
import httpx
from market_data import market_get, market
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

APP_NAME="Blue Whale Fibonacci + VWAP — PAPER"
SYMBOL="BTCUSDT"
TELEGRAM_URL="https://t.me/s/BlueWhaleCryptoTrading"
BINANCE_PRICE_URL="https://data-api.binance.vision/api/v3/ticker/price"
START_BALANCE=float(os.getenv("START_BALANCE","10000"))
RISK_PER_TRADE=min(0.002, float(os.getenv("WHALE_RISK_PER_TRADE","0.002")))
RR=float(os.getenv("RR","2.0"))
FEE_RATE=float(os.getenv("FEE_RATE","0.00095"))
SLIPPAGE_RATE=float(os.getenv("SLIPPAGE_RATE","0.0002"))
MAX_HOLD_HOURS=float(os.getenv("MAX_HOLD_HOURS","48"))
SCAN_SECONDS=10
ENTRY_SCAN_SECONDS=60
SYMBOLS=("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT")
MAX_SIGNAL_AGE_MINUTES=float(os.getenv("MAX_SIGNAL_AGE_MINUTES","15"))
MAX_OPEN_POSITIONS=2
MAX_TOTAL_RISK_RATE=0.004
SAME_SIDE_COOLDOWN_MINUTES=float(os.getenv("SAME_SIDE_COOLDOWN_MINUTES","30"))
DATABASE_URL=os.getenv("DATABASE_URL")
WHALE_TECH_CONFIRM=os.getenv("WHALE_TECH_CONFIRM","1")=="1"
WHALE_CONFIRM_MIN_SCORE=int(os.getenv("WHALE_CONFIRM_MIN_SCORE","4"))
WHALE_MIN_STOP_RATE=0.001
WHALE_MAX_STOP_RATE=float(os.getenv("WHALE_MAX_STOP_RATE","0.04"))
WHALE_BREAKEVEN_R=float(os.getenv("WHALE_BREAKEVEN_R","1.0"))
WHALE_PROFIT_LOCK_R=float(os.getenv("WHALE_PROFIT_LOCK_R","1.5"))
KLINES_URL="https://data-api.binance.vision/api/v3/klines"

SIGNAL_POLICY_VERSION="fib-618-786-vwap-v2-trend-pullback"
WHALE_ENTRY_TOLERANCE=float(os.getenv("WHALE_ENTRY_TOLERANCE","0.002"))
WHALE_MIN_NET_RR=float(os.getenv("WHALE_MIN_NET_RR","1.5"))
WHALE_TREND_EFFICIENCY=float(os.getenv("WHALE_TREND_EFFICIENCY","0.45"))
WHALE_TREND_VWAP_BARS=int(os.getenv("WHALE_TREND_VWAP_BARS","15"))

app=FastAPI(title=APP_NAME)
state={"balance":START_BALANCE,"equity":START_BALANCE,"open_positions":[],"open_position":None,"trades":[],"seen_signal_ids":[],"last_scan":None,"last_signal":None,"status":"starting","error":None,"persistence":"memory","persistence_error":None}

state.update({"mode":"PAPER","build":SIGNAL_POLICY_VERSION,"signal_policy":SIGNAL_POLICY_VERSION,"strategies":["FIB_618_786","VWAP_REVERSION","VWAP_TREND_PULLBACK"],"entry_status":"Čekám na kontrolu signálů","signal_checks":[],"last_source_scan":None})

def utcnow(): return datetime.now(timezone.utc)

def _sync_legacy_open_position():
    positions=state.get("open_positions") or []
    state["open_position"]=positions[0] if positions else None

def _persistent_payload():
    return {
        "balance":state["balance"],
        "equity":state["equity"],
        "open_positions":state["open_positions"],
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
                for key in ("balance","equity","trades","seen_signal_ids","last_scan","last_signal"):
                    if key in saved:
                        state[key]=saved[key]
                if isinstance(saved.get("open_positions"),list):
                    state["open_positions"]=saved["open_positions"]
                elif saved.get("open_position"):
                    state["open_positions"]=[saved["open_position"]]
                else:
                    state["open_positions"]=[]
                _sync_legacy_open_position()
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

def parse_level(text, label):
    # Match a complete numeric token, never a prefix of 819xx or 81900.
    m=re.search(r"\b(?:"+label+r")\s*[:=]?\s*([0-9][0-9,.X]*)(?![\w.])",text.upper())
    if not m:return None
    raw=m.group(1)
    if "X" in raw:return None
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?",raw):return None
    value=float(raw.replace(",",""))
    return value if 1000 <= value <= 10000000 else None

def parse_stop(text):
    value=parse_level(text,r"SL|STOP LOSS|STOP-LOSS")
    return {"raw":str(value),"low":value,"high":value,"masked":False} if value else None

def explicit_side(text)->Optional[str]:
    u=text.upper()
    lg=bool(re.search(r"\bLONG\b",u)); sh=bool(re.search(r"\bSHORT\b",u))
    if lg and not sh:return "LONG"
    if sh and not lg:return "SHORT"
    return None

def infer_side(text,stop,price):
    # Direction must be in the source; a stop above market is not a sell signal.
    return explicit_side(text)

def effective_stop(side,stop):
    if side=="LONG":return stop["high"] if stop["masked"] else stop["low"]
    return stop["low"] if stop["masked"] else stop["high"]

async def btc_price(client):
    r=await market_get(client,BINANCE_PRICE_URL,params={"symbol":SYMBOL},timeout=15)
    return float(r.json()["price"])

def _ema(values, period):
    if not values: return 0.0
    a=2.0/(period+1.0); out=float(values[0])
    for v in values[1:]: out=a*float(v)+(1-a)*out
    return out

def _rsi(values, period=14):
    if len(values)<period+1:return 50.0
    gains=[]; losses=[]
    for a,b in zip(values[-period-1:-1],values[-period:]):
        d=float(b)-float(a); gains.append(max(d,0.0)); losses.append(max(-d,0.0))
    ag=sum(gains)/period; al=sum(losses)/period
    if al<=1e-12:return 100.0
    rs=ag/al
    return 100.0-(100.0/(1.0+rs))

async def technical_confirmation(client, side):
    """Confirm public Whale direction with closed-candle trend/momentum/volume."""
    news = await news_signal.get_news(SYMBOL)
    if news_signal.blocks_entry(SYMBOL, side):
        return False, {"score": 0, "reason": "BTC_NEWS_CONFLICT", "news": news}
    if not WHALE_TECH_CONFIRM:
        return True, {"score":99,"reason":"disabled"}
    score=0; details={}
    for interval,limit in (("5m",120),("15m",120),("1h",120)):
        r=await market_get(client,KLINES_URL,params={"symbol":SYMBOL,"interval":interval,"limit":limit},timeout=15)
        rows=r.json()
        # Ignore the live candle; trade only from completed information.
        closed=rows[:-1] if len(rows)>2 else rows
        closes=[float(x[4]) for x in closed]
        vols=[float(x[5]) for x in closed]
        if len(closes)<55:
            return False, {"score":0,"reason":"insufficient candles"}
        e20=_ema(closes[-60:],20); e50=_ema(closes[-90:],50)
        rsi=_rsi(closes,14)
        ret3=closes[-1]/closes[-4]-1.0
        avgvol=sum(vols[-21:-1])/20.0 if len(vols)>=21 else sum(vols[:-1])/max(1,len(vols)-1)
        vr=(vols[-1]/avgvol) if avgvol>0 else 1.0
        bull=closes[-1]>e20>e50
        bear=closes[-1]<e20<e50
        details[interval]={"close":closes[-1],"ema20":e20,"ema50":e50,"rsi":rsi,"ret3":ret3,"volume_ratio":vr}
        if side=="LONG":
            if bull: score+=1
            if rsi>=52 and rsi<=74: score+=1
            if ret3>0: score+=1
        else:
            if bear: score+=1
            if rsi<=48 and rsi>=26: score+=1
            if ret3<0: score+=1
        # Volume confirmation only once on the execution timeframe.
        if interval=="5m" and vr>=1.05: score+=1
    # Hard veto: never fade the 1h structure.
    h1=details.get("1h",{})
    hard_veto=(side=="SHORT" and h1.get("close",0)>h1.get("ema20",0)>h1.get("ema50",0)) or (side=="LONG" and h1.get("close",0)<h1.get("ema20",0)<h1.get("ema50",0))
    ok=(score>=WHALE_CONFIRM_MIN_SCORE and not hard_veto)
    return ok, {"score":score,"min_score":WHALE_CONFIRM_MIN_SCORE,"hard_veto":hard_veto,"details":details,"news":news}

async def latest_signals(client):
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
        # Include incomplete posts in diagnostics, but never trade them.
        if not re.search(r"\b(?:SL|LONG|SHORT|ENTRY)\b",text.upper()):continue
        posted_at=None
        if dtm:
            try: posted_at=datetime.fromisoformat(dtm.group(1).replace("Z","+00:00"))
            except ValueError: pass
        candidates.append({"id":int(mid.group(1)),"text":text,"stop":parse_stop(text),
                           "entry":parse_level(text,r"ENTRY|ENTRY PRICE"),
                           "tp":parse_level(text,r"TP1|TP 1|TP|TAKE PROFIT"),
                           "posted_at":posted_at.isoformat() if posted_at else None})
    state["last_source_scan"]=utcnow().isoformat()
    return sorted(candidates,key=lambda x:x["id"])

def signal_problem(signal, price):
    stop=signal.get("stop")
    side=explicit_side(signal["text"])
    if not side or not stop or stop.get("masked") or not signal.get("entry") or not signal.get("tp"):
        return "Neúplný signál: potřebuji směr, přesný vstup, SL a TP", True
    entry=signal["entry"]; sl=stop["low"]; tp=signal["tp"]
    if not (sl < entry < tp if side=="LONG" else tp < entry < sl):
        return "Nesprávné pořadí vstupu, SL a TP", True
    if (price<=sl or price>=tp) if side=="LONG" else (price>=sl or price<=tp):
        return "Cena už překročila SL nebo TP signálu", True
    if abs(price-entry)/entry>WHALE_ENTRY_TOLERANCE:
        return "Čekám na cenu v blízkosti vstupu signálu", False
    return None, False

def remember_signal(signal_id):
    if signal_id not in state["seen_signal_ids"]:
        state["seen_signal_ids"].append(signal_id)
        state["seen_signal_ids"]=state["seen_signal_ids"][-200:]

def mark_to_market(price=None):
    marks=state.get("market_prices",{})
    net=0.0
    for p in state.get("open_positions") or []:
        px=marks.get(p.get("symbol",SYMBOL))
        if px is None:
            state["equity"]=None
            _sync_legacy_open_position()
            return
        fill=px*(1-SLIPPAGE_RATE if p["side"]=="LONG" else 1+SLIPPAGE_RATE)
        net+=((fill-p["entry"]) if p["side"]=="LONG" else (p["entry"]-fill))*p["qty"]-fill*p["qty"]*FEE_RATE
    state["equity"]=state["balance"]+net
    _sync_legacy_open_position()

def _same_side_too_soon(side):
    now=utcnow()
    for p in state.get("open_positions") or []:
        if p.get("side")!=side:
            continue
        try:
            age_min=(now-datetime.fromisoformat(p["opened_at"])).total_seconds()/60.0
        except Exception:
            age_min=0.0
        if age_min<SAME_SIDE_COOLDOWN_MINUTES:
            return True
    return False

def open_paper(signal,side,market_price):
    reason,_=signal_problem(signal,market_price)
    if reason or side!=explicit_side(signal["text"]):
        state["last_signal"]={"id":signal["id"],"rejected":reason or "Směr neodpovídá signálu"}
        return False
    positions=state.get("open_positions") or []
    if len(positions)>=MAX_OPEN_POSITIONS:
        state["last_signal"]={"id":signal["id"],"rejected":"Limit dvou otevřených pozic"}
        return False
    if any(p.get("symbol",SYMBOL)==signal.get("symbol",SYMBOL) for p in positions):
        state["last_signal"]={"id":signal["id"],"rejected":"Na tomto trhu už je pozice"}
        return False
    if _same_side_too_soon(side):
        state["last_signal"]={"id":signal["id"],"side":side,"stop_raw":signal["stop"]["raw"],"rejected":"same-side cooldown","seen_at":utcnow().isoformat()}
        return False
    entry=market_price*(1+SLIPPAGE_RATE if side=="LONG" else 1-SLIPPAGE_RATE)
    stop=effective_stop(side,signal["stop"])
    stop_rate=(entry-stop)/entry if side=="LONG" else (stop-entry)/entry
    if stop_rate<=0 or stop_rate>WHALE_MAX_STOP_RATE or stop_rate<WHALE_MIN_STOP_RATE:
        state["last_signal"]={"id":signal["id"],"side":side,"stop_raw":signal["stop"]["raw"],"rejected":"stop distance outside quality band","stop_rate":stop_rate,"seen_at":utcnow().isoformat()}
        return False
    account_basis=state["balance"]+sum(float(p.get("entry_fee",0.0)) for p in positions)
    risk=account_basis*RISK_PER_TRADE
    open_risk=sum(float(p.get("risk_dollars",0.0)) for p in positions)
    if open_risk+risk > account_basis*MAX_TOTAL_RISK_RATE+1e-9:
        state["last_signal"]={"id":signal["id"],"side":side,"stop_raw":signal["stop"]["raw"],"rejected":"max total risk","seen_at":utcnow().isoformat()}
        return False
    eff=stop_rate+2*(FEE_RATE+SLIPPAGE_RATE)
    notional=min(risk/eff, max(0.0, account_basis-sum(float(p.get("notional",0)) for p in positions)), account_basis*0.5)
    if notional<=0:return False
    risk=notional*eff
    qty=notional/entry
    tp=float(signal["tp"])
    reward_rate=((tp-entry) if side=="LONG" else (entry-tp))/entry-2*(FEE_RATE+SLIPPAGE_RATE)
    if reward_rate < WHALE_MIN_NET_RR*eff:
        state["last_signal"]={"id":signal["id"],"rejected":"Nedostatečný poměr zisku k riziku po poplatcích"}
        return False
    entry_fee=entry*qty*FEE_RATE
    state["balance"]-=entry_fee
    position={"symbol":signal.get("symbol",SYMBOL),"strategy":signal.get("strategy","LEGACY_TELEGRAM"),"signal_policy":SIGNAL_POLICY_VERSION,"confirmation":signal.get("confirmation"),"source_entry":signal["entry"],"signal_id":signal["id"],"signal_text":signal["text"],"side":side,"entry":entry,"stop":stop,"initial_stop":stop,"tp":tp,"qty":qty,"notional":notional,"risk_dollars":risk,"opened_at":utcnow().isoformat(),"entry_fee":entry_fee,"breakeven":False,"profit_lock":False}
    state["open_positions"].append(position)
    _sync_legacy_open_position()
    state["last_signal"]={"symbol":signal.get("symbol",SYMBOL),"strategy":signal.get("strategy"),"id":signal["id"],"side":side,"stop_raw":signal["stop"]["raw"],"accepted_at":utcnow().isoformat()}
    remember_signal(signal["id"])
    mark_to_market(market_price)
    save_state()
    return True

def close_paper(p,price,reason,mark_price=None):
    positions=state.get("open_positions") or []
    if p not in positions:return
    exit_price=price*(1-SLIPPAGE_RATE if p["side"]=="LONG" else 1+SLIPPAGE_RATE)
    gross=(exit_price-p["entry"])*p["qty"] if p["side"]=="LONG" else (p["entry"]-exit_price)*p["qty"]
    exit_fee=exit_price*p["qty"]*FEE_RATE
    net_after_exit=gross-exit_fee
    state["balance"]+=net_after_exit
    trade={**p,"exit":exit_price,"exit_fee":exit_fee,"net_pnl":net_after_exit-p["entry_fee"],"closed_at":utcnow().isoformat(),"reason":reason}
    state["trades"].append(trade); state["trades"]=state["trades"][-100:]
    state["open_positions"].remove(p)
    _sync_legacy_open_position()
    mark_to_market(mark_price if mark_price is not None else price)
    save_trade(trade)
    save_state()

def age_hours(p):
    if not p:return 0
    return (utcnow()-datetime.fromisoformat(p["opened_at"])).total_seconds()/3600

def closed_candles(rows, now_ms, minutes):
    closed=[r for r in rows if int(r[6]) < now_ms]
    if len(closed)<60 or now_ms-int(closed[-1][6]) > (minutes*60+45)*1000:
        raise ValueError("Chybí aktuální uzavřené svíčky")
    if any(int(b[0])-int(a[0]) != minutes*60000 for a,b in zip(closed,closed[1:])):
        raise ValueError("Mezera v historii svíček")
    for r in closed:
        if not all(math.isfinite(float(r[i])) and float(r[i])>0 for i in (1,2,3,4)) or not math.isfinite(float(r[5])) or float(r[5])<0:
            raise ValueError("Neplatná cena nebo objem")
    return closed

def atr_value(rows):
    tr=[max(float(b[2])-float(b[3]),abs(float(b[2])-float(a[4])),abs(float(b[3])-float(a[4]))) for a,b in zip(rows,rows[1:])]
    return sum(tr[-14:])/14

def fib_candidate(rows):
    """Confirmed 5m pivots, two right-hand bars; no live candle or future data."""
    pivots=[]
    # Reserve the final candle for entry confirmation, not pivot discovery.
    for i in range(2,len(rows)-3):
        window=rows[i-2:i]+rows[i+1:i+3]
        if float(rows[i][2])>max(float(r[2]) for r in window):pivots.append((i,"H",float(rows[i][2])))
        if float(rows[i][3])<min(float(r[3]) for r in window):pivots.append((i,"L",float(rows[i][3])))
    diag={"strategy":"FIB_618_786","reason":"Čekám na potvrzený swing"}
    if len(pivots)<2:return None,diag
    end=pivots[-1]
    start=next((p for p in reversed(pivots[:-1]) if p[1]!=end[1] and p[0]<end[0]),None)
    if not start or len(rows)-1-end[0]>36:return None,diag
    side="LONG" if end[1]=="H" else "SHORT"
    lo=start[2] if side=="LONG" else end[2]
    hi=end[2] if side=="LONG" else start[2]
    span=hi-lo; atr=atr_value(rows)
    if span<3*atr:return None,{**diag,"reason":"Swing je příliš malý"}
    f618=hi-.618*span if side=="LONG" else lo+.618*span
    f786=hi-.786*span if side=="LONG" else lo+.786*span
    lower,upper=sorted((f618,f786))
    diag.update(side=side,fib_618=f618,fib_786=f786,swing_low=lo,swing_high=hi,
                reason="Čekám na dotyk pásma a potvrzený odraz")
    tail=rows[end[0]+1:]
    if (min(float(r[3]) for r in tail)<=lo if side=="LONG" else max(float(r[2]) for r in tail)>=hi):
        return None,{**diag,"reason":"Swing byl porušen; čekám na nový"}
    prev,last=rows[-2:]
    touched=any(float(r[3])<=upper and float(r[2])>=lower for r in (prev,last))
    c,o=float(last[4]),float(last[1])
    confirmed=(c>o and c>float(prev[4]) and c>=lower and c<=upper+.3*atr) if side=="LONG" else (c<o and c<float(prev[4]) and c<=upper and c>=lower-.3*atr)
    if not touched or not confirmed:return None,diag
    stop=lo-.25*atr if side=="LONG" else hi+.25*atr
    target=hi if side=="LONG" else lo
    # One entry for a swing, even if price revisits the zone later.
    key=f"fib:{rows[start[0]][0]}:{rows[end[0]][0]}:{side}"
    return dict(side=side,entry=c,stop=stop,tp=target,key=key,strategy="FIB_618_786",confirmation=diag),diag

def vwap_candidate(rows):
    # Slow 60-minute VWAP for mean reversion. In a strongly one-sided market
    # switch to a faster same-direction VWAP pullback instead of fading trend.
    sample=rows[-61:-1]
    vol=sum(float(r[5]) for r in sample)
    diag={"strategy":"VWAP_REVERSION","reason":"Čekám na návrat z odchylky k VWAP"}
    if vol<=0:return None,{**diag,"reason":"Chybí objem pro VWAP"}
    mean=sum((float(r[2])+float(r[3])+float(r[4]))/3*float(r[5]) for r in sample)/vol
    variance=sum((((float(r[2])+float(r[3])+float(r[4]))/3-mean)**2)*float(r[5]) for r in sample)/vol
    sigma=math.sqrt(variance); atr=atr_value(rows)
    diag.update(vwap=mean,slow_vwap=mean,band_low=mean-1.8*sigma,band_high=mean+1.8*sigma)
    if sigma<=0 or atr<=0:return None,diag

    closes=[float(r[4]) for r in rows[-21:]]
    path=sum(abs(b-a) for a,b in zip(closes,closes[1:]))
    efficiency=abs(closes[-1]-closes[0])/path if path else 0
    diag["trend_efficiency"]=efficiency

    if efficiency>WHALE_TREND_EFFICIENCY:
        side="LONG" if closes[-1]>closes[0] else "SHORT"
        n=max(5,min(WHALE_TREND_VWAP_BARS,len(rows)-2))
        trend_sample=rows[-(n+1):-1]
        tvol=sum(float(r[5]) for r in trend_sample)
        if tvol<=0:
            return None,{**diag,"strategy":"VWAP_TREND_PULLBACK","reason":"Chybí objem pro trendový VWAP"}
        trend_vwap=sum((float(r[2])+float(r[3])+float(r[4]))/3*float(r[5]) for r in trend_sample)/tvol
        touch_tolerance=max(.35*atr,trend_vwap*.00015)
        recent=rows[-3:]
        touched=(min(float(r[3]) for r in recent)<=trend_vwap+touch_tolerance and
                 max(float(r[2]) for r in recent)>=trend_vwap-touch_tolerance)
        prev,last=rows[-2:]
        a,b=float(prev[4]),float(last[4]); o=float(last[1])

        diag.update(strategy="VWAP_TREND_PULLBACK",trend_side=side,trend_vwap=trend_vwap,
                    vwap=trend_vwap,touch_tolerance=touch_tolerance)
        if side=="LONG":
            confirmed=(touched and b>o and b>a and b>trend_vwap and
                       b-trend_vwap<=1.25*atr)
            stop=min(float(r[3]) for r in rows[-5:])-.35*atr
            risk=max(b-stop,0.0)
        else:
            confirmed=(touched and b<o and b<a and b<trend_vwap and
                       trend_vwap-b<=1.25*atr)
            stop=max(float(r[2]) for r in rows[-5:])+.35*atr
            risk=max(stop-b,0.0)

        if not confirmed:
            direction="LONG" if side=="LONG" else "SHORT"
            return None,{**diag,"reason":f"Silný trend {direction}; čekám na pullback k trendovému VWAP a potvrzení"}

        stop_rate=risk/b if b>0 else 0.0
        round_trip=2*(FEE_RATE+SLIPPAGE_RATE)
        minimum_target_rate=WHALE_MIN_NET_RR*(stop_rate+round_trip)+round_trip
        target_distance=max(2.0*risk,b*minimum_target_rate*1.05,1.5*atr)
        target=b+target_distance if side=="LONG" else b-target_distance
        diag["reason"]="Trendový VWAP pullback potvrzen"
        key=f"vwap-trend:{last[0]}:{side}"
        return dict(side=side,entry=b,stop=stop,tp=target,key=key,
                    strategy="VWAP_TREND_PULLBACK",confirmation=diag),diag

    prev,last=rows[-2:]; a,b=float(prev[4]),float(last[4])
    side=None
    if a<mean-1.8*sigma<=b<mean and b>float(last[1]):side="LONG"
    elif a>mean+1.8*sigma>=b>mean and b<float(last[1]):side="SHORT"
    if not side:return None,diag
    stop=min(float(r[3]) for r in rows[-5:])-.5*atr if side=="LONG" else max(float(r[2]) for r in rows[-5:])+.5*atr
    return dict(side=side,entry=b,stop=stop,tp=mean,key=f"vwap:{last[0]}:{side}",strategy="VWAP_REVERSION",confirmation=diag),diag

async def scan_entries(client, price=None):
    diagnostics=[]
    for symbol in SYMBOLS:
        try:
            now_ms=int(time.time()*1000)
            frames={}
            for interval,minutes in (("1m",1),("5m",5)):
                r=await market_get(client,KLINES_URL,params={"symbol":symbol,"interval":interval,"limit":120},timeout=15)
                frames[interval]=closed_candles(r.json(),now_ms,minutes)
            candidates=[]
            for fn,interval in ((fib_candidate,"5m"),(vwap_candidate,"1m")):
                candidate,diag=fn(frames[interval]); diag["symbol"]=symbol
                diagnostics.append(diag)
                if candidate:candidates.append((candidate,diag))
            # Fresh execution mark after candle requests; do not chase a closed-bar signal.
            r=await market_get(client,BINANCE_PRICE_URL,params={"symbol":symbol},timeout=15)
            px=float(r.json()["price"])
            state.setdefault("market_prices",{})[symbol]=px
            for candidate,diag in candidates:
                sid=int.from_bytes(hashlib.sha256((symbol+candidate["key"]).encode()).digest()[:8],"big") & ((1<<63)-1)
                if sid in state["seen_signal_ids"]:
                    diag["reason"]="Tento setup již byl zobchodován";continue
                if any(p.get("symbol",SYMBOL)==symbol for p in state["open_positions"]):
                    diag["reason"]="Na tomto trhu už je otevřená pozice";continue
                if state.get("persistence")!="postgres" or state.get("persistence_error"):
                    diag["reason"]="Nový vstup čeká na funkční ukládání";continue
                candidate.update(id=sid,text=candidate["side"],symbol=symbol,
                                 stop={"raw":str(candidate["stop"]),"low":candidate["stop"],"high":candidate["stop"],"masked":False})
                if open_paper(candidate,candidate["side"],px):
                    remember_signal(sid)
                    diag["reason"]="Obchod otevřen: "+candidate["strategy"]
                else:
                    diag["reason"]=(state.get("last_signal") or {}).get("rejected","Limit pozic nebo rizika")
        except Exception as exc:
            diagnostics.append({"symbol":symbol,"strategy":"DATA","reason":str(exc),"error":True})
    state["signal_checks"]=diagnostics
    state["entry_status"]=" | ".join(d["symbol"]+" "+d["strategy"]+": "+d["reason"] for d in diagnostics)
    state["last_source_scan"]=utcnow().isoformat()
    print("WHALE "+SIGNAL_POLICY_VERSION+" balance="+str(state["balance"])+" trades="+str(len(state["trades"]))+" persistence="+str(state["persistence"])+" "+state["entry_status"],flush=True)

async def bot_loop():
    await asyncio.sleep(2)
    last_entries=0.0
    async with httpx.AsyncClient() as client:
        while True:
            errors=[]
            try:
                # Exit management is independent of signal/news availability.
                for symbol in set(SYMBOLS)|{p.get("symbol",SYMBOL) for p in state["open_positions"]}:
                    try:
                        r=await market_get(client,BINANCE_PRICE_URL,params={"symbol":symbol},timeout=15)
                        price=float(r.json()["price"])
                        if not math.isfinite(price) or price<=0:raise ValueError("Neplatná cena")
                        state.setdefault("market_prices",{})[symbol]=price
                        if symbol==SYMBOL:state["market_price"]=price
                        for p in list(state["open_positions"]):
                            if p.get("symbol",SYMBOL)!=symbol:continue
                            # Use observed price for a stop gap, not an unavailable ideal fill.
                            if (price<=p["stop"] if p["side"]=="LONG" else price>=p["stop"]):
                                close_paper(p,price,"SL",price);continue
                            if (price>=p["tp"] if p["side"]=="LONG" else price<=p["tp"]):
                                close_paper(p,p["tp"],"TP",price);continue
                            if age_hours(p)>=MAX_HOLD_HOURS:
                                close_paper(p,price,"TIME",price);continue
                            one_r=abs(p["entry"]-p.get("initial_stop",p["stop"]))
                            favorable=(price-p["entry"]) if p["side"]=="LONG" else (p["entry"]-price)
                            if one_r>0 and favorable>=WHALE_BREAKEVEN_R*one_r:
                                # Cost-covered breakeven, only tighten after the market passes it.
                                be=p["entry"]*(1+FEE_RATE)/((1-FEE_RATE)*(1-SLIPPAGE_RATE)) if p["side"]=="LONG" else p["entry"]*(1-FEE_RATE)/((1+FEE_RATE)*(1+SLIPPAGE_RATE))
                                if (price>be if p["side"]=="LONG" else price<be):
                                    p["stop"]=max(p["stop"],be) if p["side"]=="LONG" else min(p["stop"],be)
                                    p["breakeven"]=True
                    except Exception as exc:
                        state.setdefault("market_prices",{}).pop(symbol,None)
                        errors.append(symbol+": "+str(exc))
                mark_to_market()
                if time.monotonic()-last_entries>=ENTRY_SCAN_SECONDS:
                    await scan_entries(client)
                    last_entries=time.monotonic()
                errors.extend(d["symbol"]+": "+d["reason"] for d in state.get("signal_checks",[]) if d.get("error"))
                state["last_scan"]=utcnow().isoformat()
                state["status"]="error" if errors else "running"
                state["error"]="; ".join(errors) if errors else None
                mark_to_market()
                save_state()
            except Exception as exc:
                state["status"]="error";state["error"]=repr(exc)
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
<title>Blue Whale Fibonacci + VWAP</title>
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
  <h1>🐋 BLUE WHALE FIB + VWAP</h1>
  <div class="muted">PAPER • BTC / ETH / SOL / XRP • FIB 0,618–0,786 + VWAP • risk max. 0,2 %</div>
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
      document.getElementById('position').innerHTML='Žádná otevřená pozice.';
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
      document.getElementById('signal').innerHTML='Čekám na odraz FIB 0,618–0,786 nebo návrat k VWAP.';
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
      'Blue Whale Fibonacci + VWAP • PAPER ONLY • kontrola nového signálu každých 60 s';
  }catch(e){
    document.getElementById('health').textContent='Dashboard error: '+e;
  }
}
refresh();
setInterval(refresh,5000);
</script>
</body></html>
""", headers={"Cache-Control":"no-store, no-cache, must-revalidate"})
