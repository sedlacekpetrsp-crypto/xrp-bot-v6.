import asyncio, json, math, os, statistics, time
from datetime import datetime, timezone, timedelta
import httpx, psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from market_data import market_get
import app_v8_fly_engine as ind

app = FastAPI(title='V11 Evidence XRP')
BUILD = STRATEGY_VERSION = 'v11-evidence-xrp-20260917-1'
SYMBOL, BTC_SYMBOL = 'XRPUSDC', 'BTCUSDC'
BINANCE_API = 'https://data-api.binance.vision'
DATABASE_URL = os.getenv('DATABASE_URL')
STARTING_BALANCE = 10000.0
TRADING_MODE = 'PAPER'

BASE_RISK_PER_TRADE = 0.0015
MAX_NOTIONAL_SHARE = 0.30
FEE_RATE, SLIPPAGE_RATE = 0.0005, 0.0002
ROUND_TRIP_COST = 2 * (FEE_RATE + SLIPPAGE_RATE)
BREAKOUT_LOOKBACK_5M = 20
RETEST_SECONDS, RETEST_TOL_ATR1 = 240, 0.12
BREAKOUT_BUFFER_ATR5 = 0.04
MIN_VOLUME_RATIO_5M, MIN_VOLUME_RATIO_1M = 1.20, 1.05
MAX_SPREAD_PCT = 0.00040
BOOK_LONG_MIN, BOOK_SHORT_MAX = 0.54, 0.46
MIN_ADX_15M, MIN_EMA_SEP_15M = 18.0, 0.0008
MIN_ATR5_RATE, MAX_ATR5_RATE = 0.0025, 0.0150
BTC_SHOCK_5M = 0.0050
MIN_STOP_RATE, MAX_STOP_RATE, ATR5_STOP_MULT = 0.0045, 0.0090, 0.90
MIN_EDGE_TO_COST = 2.50
PARTIAL_TAKE_R, PARTIAL_FRACTION = 0.80, 0.60
RUNNER_CAP_R = 2.20
TRAIL_START_R, TRAIL_LOCK_1_R = 1.20, 0.35
TRAIL_LOCK_2_TRIGGER_R, TRAIL_LOCK_2_R = 1.65, 0.85
MAX_TRADE_MINUTES = 60
MAX_TRADES_PER_UTC_DAY, DAILY_LOSS_LIMIT_R = 4, 1.50
MAX_CONSECUTIVE_LOSSES, LOSS_STREAK_COOLDOWN_MIN = 2, 60
NORMAL_COOLDOWN_MIN = 5
OFI_SNAPSHOTS, OFI_DELAY_SECONDS = 3, 0.40
MIN_OFI_NORM, MIN_OFI_SIGN_CONSISTENCY = 0.05, 1.0

paper_balance = STARTING_BALANCE
paper_position = None
trade_history, watch = [], None
last_entry_candle = cooldown_until = None
last_cycle_at = last_error = last_analysis = None
last_decision = 'STARTING'
http_client = bot_task = None

def utcnow(): return datetime.now(timezone.utc)
def get_db(): return psycopg.connect(DATABASE_URL) if DATABASE_URL else None

def init_db():
    if not DATABASE_URL: return
    with get_db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS v11_evidence_trades(
            id SERIAL PRIMARY KEY,strategy_version TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,
            entry_price DOUBLE PRECISION NOT NULL,exit_price DOUBLE PRECISION NOT NULL,qty DOUBLE PRECISION NOT NULL,
            gross_pnl DOUBLE PRECISION NOT NULL,fees DOUBLE PRECISION NOT NULL,pnl DOUBLE PRECISION NOT NULL,
            initial_risk_usdc DOUBLE PRECISION,risk_multiplier DOUBLE PRECISION,metadata JSONB,reason TEXT,
            opened_at TIMESTAMPTZ,closed_at TIMESTAMPTZ DEFAULT NOW())''')
        c.execute('''CREATE TABLE IF NOT EXISTS v11_evidence_state(id INTEGER PRIMARY KEY,state JSONB NOT NULL)''')
        c.commit()

def load_state():
    global paper_balance,paper_position,last_entry_candle,cooldown_until,trade_history,last_decision
    if not DATABASE_URL: return
    with get_db() as c:
        r=c.execute('SELECT state FROM v11_evidence_state WHERE id=1').fetchone()
        if r:
            s=r[0] or {};paper_balance=float(s.get('paper_balance',STARTING_BALANCE));paper_position=s.get('paper_position')
            last_entry_candle=s.get('last_entry_candle');cd=s.get('cooldown_until');cooldown_until=datetime.fromisoformat(cd) if cd else None
            last_decision=s.get('last_decision','RESTORED')
        rows=c.execute('''SELECT strategy_version,symbol,side,entry_price,exit_price,qty,gross_pnl,fees,pnl,
            initial_risk_usdc,risk_multiplier,metadata,reason,opened_at,closed_at FROM v11_evidence_trades ORDER BY id DESC LIMIT 500''').fetchall()
    trade_history=[{'strategy_version':r[0],'symbol':r[1],'side':r[2],'entry_price':r[3],'exit_price':r[4],'qty':r[5],
        'gross_pnl':r[6],'fees':r[7],'pnl':r[8],'initial_risk_usdc':r[9],'risk_multiplier':r[10],'metadata':r[11] or {},
        'reason':r[12],'opened_at':r[13].isoformat() if r[13] else None,'closed_at':r[14].isoformat() if r[14] else None} for r in rows]

def save_state():
    if not DATABASE_URL:return
    s={'paper_balance':paper_balance,'paper_position':paper_position,'last_entry_candle':last_entry_candle,
       'cooldown_until':cooldown_until.isoformat() if cooldown_until else None,'last_decision':last_decision}
    with get_db() as c:
        c.execute('''INSERT INTO v11_evidence_state(id,state) VALUES(1,%s::jsonb)
            ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state''',(json.dumps(s),));c.commit()

def save_trade(t):
    if not DATABASE_URL:return
    with get_db() as c:
        c.execute('''INSERT INTO v11_evidence_trades(strategy_version,symbol,side,entry_price,exit_price,qty,gross_pnl,fees,pnl,
            initial_risk_usdc,risk_multiplier,metadata,reason,opened_at,closed_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)''',
            (t['strategy_version'],t['symbol'],t['side'],t['entry_price'],t['exit_price'],t['qty'],t['gross_pnl'],t['fees'],t['pnl'],
             t['initial_risk_usdc'],t['risk_multiplier'],json.dumps(t.get('metadata') or {}),t['reason'],t['opened_at'],t['closed_at']));c.commit()

async def fetch(path,params):
    r=await market_get(http_client,BINANCE_API+path,params=params,timeout=12);r.raise_for_status();return r.json()
async def klines(symbol,interval,limit=250): return await fetch('/api/v3/klines',{'symbol':symbol,'interval':interval,'limit':limit})
async def live_price(symbol=SYMBOL): return float((await fetch('/api/v3/ticker/price',{'symbol':symbol}))['price'])
async def depth(symbol=SYMBOL): return await fetch('/api/v3/depth',{'symbol':symbol,'limit':20})

def _ohlcv(rows):
    x=rows[:-1];return [float(r[2]) for r in x],[float(r[3]) for r in x],[float(r[4]) for r in x],[float(r[5]) for r in x],int(x[-1][0])

def _book_snapshot(d):
    bids,asks=d.get('bids') or [],d.get('asks') or []
    if not bids or not asks:return None
    bv=sum(float(p)*float(q) for p,q in bids[:5]);av=sum(float(p)*float(q) for p,q in asks[:5])
    bid,bq=float(bids[0][0]),float(bids[0][1]);ask,aq=float(asks[0][0]),float(asks[0][1]);mid=(bid+ask)/2
    return {'bid':bid,'bid_qty':bq,'ask':ask,'ask_qty':aq,'imbalance':bv/max(bv+av,1e-12),'spread_pct':(ask-bid)/max(mid,1e-12),'depth_top':max((bq+aq)/2,1e-12)}

def _ofi(a,b):
    e=(b['bid_qty'] if b['bid']>=a['bid'] else 0)-(a['bid_qty'] if b['bid']<=a['bid'] else 0)
    e-=(b['ask_qty'] if b['ask']<=a['ask'] else 0);e+=(a['ask_qty'] if b['ask']>=a['ask'] else 0)
    return e/max((a['depth_top']+b['depth_top'])/2,1e-12)

async def microstructure():
    s=[]
    for i in range(OFI_SNAPSHOTS):
        z=_book_snapshot(await depth())
        if not z:return {'ok':False,'reason':'EMPTY_BOOK'}
        s.append(z)
        if i<OFI_SNAPSHOTS-1:await asyncio.sleep(OFI_DELAY_SECONDS)
    o=[_ofi(s[i-1],s[i]) for i in range(1,len(s))]
    return {'ok':True,'imbalance':sum(x['imbalance'] for x in s)/len(s),'spread_pct':max(x['spread_pct'] for x in s),
        'ofi_norm':sum(o)/max(len(o),1),'ofi_values':o,'positive_fraction':sum(x>0 for x in o)/max(len(o),1),'negative_fraction':sum(x<0 for x in o)/max(len(o),1)}

def _stdlog(c,n):
    if len(c)<n+1:return 0.0
    x=[math.log(b/a) for a,b in zip(c[-n-1:-1],c[-n:]) if a>0 and b>0];return statistics.pstdev(x) if len(x)>1 else 0.0

def _risk_multiplier(c5):
    f,s=_stdlog(c5,12),_stdlog(c5,72);r=f/s if s>1e-12 else 1.0
    return (0.50 if r>=1.60 else 0.75 if r>=1.30 else 1.0),f,s,r

def _vr(v,n=20):
    p=v[-n-1:-1];a=sum(p)/len(p) if p else 0;return v[-1]/a if a>0 else 0

def _today_rows():
    d=utcnow().date();return [t for t in trade_history if t.get('closed_at') and datetime.fromisoformat(t['closed_at']).date()==d and t.get('strategy_version')==STRATEGY_VERSION]

def _safety():
    r=_today_rows();ar=sum(float(t.get('initial_risk_usdc') or 0) for t in r)/len(r) if r else 0;p=sum(float(t.get('pnl') or 0) for t in r)
    streak=0
    for t in r:
        if float(t.get('pnl') or 0)<0:streak+=1
        else:break
    return len(r),max(0,-p/max(ar,1e-12)) if r else 0,streak

async def analysis():
    global last_analysis
    k1,k5,k15,kb=await asyncio.gather(klines(SYMBOL,'1m'),klines(SYMBOL,'5m'),klines(SYMBOL,'15m'),klines(BTC_SYMBOL,'5m',60))
    h1,l1,c1,v1,ct1=_ohlcv(k1);h5,l5,c5,v5,ct5=_ohlcv(k5);h1,l15,c15,v15,_=_ohlcv(k15);_,_,btc5,_,_=_ohlcv(kb)
    px=float(k1[-1][4]);atr1=ind.atr_wilder(h1,l1,c1);atr5=ind.atr_wilder(h5,l5,c5);adx15=ind.adx_wilder(h15,l15,c15)
    e20_5,e50_5=ind.ema(c5,20),ind.ema(c5,50);e20_15,e50_15=ind.ema(c15,20),ind.ema(c15,50);vw5=ind.vwap(h5,l5,c5,v95)
    vr5,vr1=_vr(v5),_vr(v1);sep=abs(e20_15-e50_15)/px if e20_15 is not None and e50_15 is not None else 0;atr_rate=(atr5 or 0)/px
    rm,rvf,rvs,vratio=_risk_multiplier(c5);bh=max(h5[-BREAKOUT_LOOKBACK_5M-1:-1]);bl=min(l5[-BREAKOUT_LOOKBACK_5M-1:-1]);buf=(atr5 or 0)*BREAKOUT_BUFFER_ATR5
    long15=e20_15 is not None and e50_15 is not None and e20_15>e50_15 and c15[-1]>e20_15;short15=e20_15 is not None and e50_15 is not None and e20_15<e50_15 and c15[-1]<e20_15
    long5=e20_5 is not None and e50_5 is not None and e20_5>e50_5 and c5[-1]>e20_5;short5=e20_5 is not None and e50_5 is not None and e20_5<e50_5 and c5[-1]<e20_5
    btc=btc5[-1]/btc5[-2]-1 if len(btc5)>1 and btc5[-2] else 0;common=adx15 is not None and adx15>=MIN_ADX_15M and sep>=MIN_EMA_SEP_15M and vr5>=MIN_VOLUME_RATIO_5M and vr1>=MIN_VOLUME_RATIO_1M and MIN_ATR5_RATE<=atr_rate<=MAX_ATR5_RATE
    long_ctx=common and long15 and long5 and vw5 is not None and c5[-1]>=vw5 and btc>-BTC_SHOCK_5M;short_ctx=common and short15 and short5 and vw5 is not None and c5[-1]<=vw5 and btc<BTC_SHOCK_5M
    stop_rate=max((atr5 or 0)*ATR5_STOP_MULT/px,MIN_STOP_RATE);edge=(stop_rate*PARTIAL_TAKE_R)/ROUND_TRIP_COST;edge_ok=edge>=MIN_EDGE_TO_COST and stop_rate<=MAX_STOP_RATE
    last_analysis={'price':px,'candle_time_5m':ct5,'atr1':atr1,'atr5':atr5,'adx15':adx15,'volume_ratio_5m':vr5,'volume_ratio_1m':vr1,
        'breakout_high_5m':bh,'breakout_low_5m':bl,'long_break_close':c5[-1]>bh+buf,'short_break_close':c5[-1]<bl-buf,'long_context':long_ctx,'short_context':short_ctx,
        'btc_return_5m':btc,'risk_multiplier':rm,'vol_ratio':vratio,'atr5_rate':atr_rate,'edge_to_cost':edge,'edge_ok':edge_ok}
    return last_analysis

