import asyncio,json,math,os,time
from datetime import datetime,timezone,timedelta
import httpx,psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse,JSONResponse
from market_data import market_get
import app_v8_fly_engine as ind

app=FastAPI(title='V11 Evidence XRP')
BUILD='v11-evidence-xrp-20260917-2'; SYMBOL='XRPUSDC'; BTC='BTCUSDC'; API='https://data-api.binance.vision'; DB=os.getenv('DATABASE_URL')
BAL=10000.0; POS=None; HIST=[]; WATCH=None; LAST=None; CD=None; LAST_CYCLE=None; ERR=None; DECISION='STARTING'; CLIENT=None; bot_task=None
FEE=.0005; SLIP=.0002; COST=2*(FEE+SLIP); BASE_RISK=.0015; MAX_NOTIONAL=.30
PARTIAL_R=.80; PARTIAL_FRAC=.60; RUNNER_R=2.20; MAX_MIN=60

def now(): return datetime.now(timezone.utb)
def db(): return psycopg.connect(DB) if DB else None

def init_db():
    if not DB:return
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS v11_evidence_state(id int primary key,state jsonb not null)')
        c.execute('''CREATE TABLE IF NOT EXISTS v11_evidence_trades(id serial primary key,version text,symbol text,side text,entry float8,exit float8,qty float8,pnl float8,risk float8,meta jsonb,reason text,opened timestamptz,closed timestamptz default now())''');c.commit()

def load():
    global BAL,POS,HIST,LAST,CD
    if not DB:return
    with db() as c:
        r=c.execute('select state from v11_evidence_state where id=1').fetchone()
        if r:
            s=r[0] or {};BAL=float(s.get('bal',BAL));POS=s.get('pos');LAST=s.get('last');x=s.get('cd');CD=datetime.fromisoformat(x) if x else None
        rows=c.execute('select version,symbol,side,entry,exit,qty,pnl,risk,meta,reason,opened,closed from v11_evidence_trades order by id desc limit 300').fetchall()
    HIST=[{'version':r[0],'symbol':r[1],'side':r[2],'entry':r[3],'exit':r[4],'qty':r[5],'pnl':r[6],'risk':r[7],'meta':r[8] or {},'reason':r[9],'opened':r[10].isoformat() if r[10] else None,'closed':r[11].isoformat() if r[11] else None} for r in rows]

def save_state():
    if not DB:return
    s={'bal':BAL,'pos':POS,'last':LAST,'cd':CD.isoformat() if CD else None}
    with db() as c:c.execute("insert into v11_evidence_state values(1,%s::jsonb) on conflict(id) do update set state=excluded.state",(json.dumps(s),));c.commit()

def save_trade(t):
    if not DB:return
    with db() as c:c.execute('insert into v11_evidence_trades(version,symbol,side,entry,exit,qty,pnl,risk,meta,reason,opened,closed) values(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)',(t['version'],t['symbol'],t['side'],t['entry'],t['exit'],t['qty'],t['pnl'],t['risk'],json.dumps(t['meta']),t['reason'],t['opened'],t['closed']));c.commit()

async def get(path,p):
    r=await market_get(CLIENT,API+path,params=p,timeout=12);r.raise_for_status();return r.json()
async def kl(s,i,n=220):return await get('/api/v3/klines',{'symbol':s,'interval':i,'limit':n})
async def price():return float((await get('/api/v3/ticker/price',{'symbol':SYMBOL}))['price'])
async def book():return await get('/api/v3/depth',{'symbol':SYMBOL,'limit':20})
def oc(k):
    x=k[:-1];return [float(r[2]) for r in x],[float(r[3]) for r in x],[float(r[4]) for r in x],[float(r[5]) for r in x],int(x[-1][0])
def vr(v,n=20):
    a=sum(v[-n-1:-1])/n;return v[-1]/a if a else 0

def snap(d):
    b,a=d['bids'],d['asks'];bv=sum(float(p)*float(q) for p,q in b[:5]);av=sum(float(p)*float(q) for p,q in a[:5]);bp,bq=float(b[0][0]),float(b[0][1]);ap,aq=float(a[0][0]),float(a[0][1]);m=(bp+ap)/2
    return {'bp':bp,'bq':bq,'ap':ap,'aq':aq,'imb':bv/(bv+av),'spr':(ap-bp)/m}
def ofi(a,b):
    e=(b['bq'] if b['bp']>=a['bp'] else 0)-(a['bq'] if b['bp']<=a['bp'] else 0)-(b['aq'] if b['ap']<=a['ap'] else 0)+(a['aq'] if b['ap']>=a['ap'] else 0)
    return e/max((a['bq']+a['aq']+b['bq']+b['aq'])/4,1e-12)
async def micro():
    s=[]
    for i in range(3):
        s.append(snap(await book()))
        if i<2:await asyncio.sleep(.4)
    o=[ofi(s[0],s[1]),ofi(s[1],s[2])]
    return {'imb':sum(x['imc'] for x in s)/3,'spr':max(x['spr'] for x in s),'ofi':sum(o)/2,'same':(o[0]>0 and o[1]>0) or (o[0]<0 and o[1]<0)}

def net(side,e,m):
    x=m*(1-SLIP if side=='LONG' else 1+SLIP);g=x-e if side=='LONG' else e-x;return g-(e+x)*FEE
def target(side,e,n):
    if side=='LONG':return ((n+e*(1+FEE))/(1-FEE))/(1-SLIP)
    return ((e*(1-FEE)-n)/(1+FEE))/(1+SLIP)

def vol_mult(c):
    def sd(n):
        x=[math.log(b/a) for a,b in zip(c[-n-1:-1],c[-n:]) if a>0 and b>0];m=sum(x)/len(x);return math.sqrt(sum((z-m)**2 for z in x)/len(x)) if x else 0
    f,s=sd(12),sd(72);r=f/s if s else 1
    return .5 if r>=1.6 else .75 if r>=1.3 else 1

async def analyze():
    k1,k5,k15,kb=await asyncio.gather(kl(SYMBOL,'1m'),kl(SYMBOL,'5m'),kl(SYMBOL,'15m'),kl(BTC,'5m',60));h1,l1,c1,v1,_=oc(k1);h5,l5,c5,v5,t=oc(k5);h15,l15,c15,v15,_=oc(k15);_,_,bc,_,_=oc(kb)
    px=float(k1[-1][4]);a1=ind.atr_wilder(h1,l1,c1);a5=ind.atr_wilder(h5,l5,c5);adx=ind.adx_wilder(h15,l15,c15);e20,e50=ind.ema(c15,20),ind.ema(c15,50);f20,f50=ind.ema(c5,20),ind.ema(c5,50);vw=ind.vwap(h5,l5,c5,v5)
    bh=max(h5[-21:-1]);bl=min(l5[-21:-1]);buf=(a5 or 0)*.04;sep=abs(e20-e50)/px if e20 is not None and e50 is not None else 0;atr=(a5 or 0)/px;btc=bc[-1]/bc[-2]-1
    common=adx is not None and adx>=18 and sep>=.0008 and vr(v5)>=1.2 and vr(v1)>=1.05 and .0025<=atr<=.015
    lc=common and e20>e50 and c15[-1]>e20 and f20>f50 and c5[-1]>f20 and c5[-1]>=vw and btc>-.005
    sc=common and e20<e50 and c15[-1]<e20 and f20<f50 and c5[-1]<f20 and c5[-1]<=vw and btc<.005
    stop=max((a5 or 0)*.9/px,.0045);edge=stop*PARTIAL_R/COST
    return {'px':px,'atr1':a1,'atr5':a5,'t':t,'bh':bh,'bl':bl,'lc':lc,'sc':sc,'lb':c5[-1]>bh+buf,'sb':c5[-1]<bl-buf,'edge':edge,'ok':edge>=2.5 and stop<=.009,'vm':vol_mult(c5),'btc':btc,'adx':adx,'vr5':vr(v5)}

def openpos(a,side,px,tr,m):
    global POS,LAST,DECISION
    e=px*(1+SLIP if side=='LONG' else 1-SLIP);d=max(float(a['atr5'] or 0)*.9,px*.0045);sl=e-d if side=='LONG' else e+d;r=-net(side,e,sl)
    if r<=0 or d/px>.009:return
    risk=BAL*BASE_RISK*a['vm'];q=min(risk/r,BAL*MAX_NOTIONAL/e);POS={'side':side,'entry':e,'qty':q,'iq':q,'sl':sl,'tp':target(side,e,r*RUNNER_R),'rpu':r,'risk':q*r,'partial':False,'pnl_part':0.0,'opened':now().isoformat(),'meta':{'ofi':m['ofi'],'imb':m['imc'],'spr':m['spr'],'edge':a['edge'],'vm':a['vm'],'btc':a['btc'],'adx':a['adx'],'vr5':a['vr5']}};LAST=a['t'];DECISION='ENTER_'+side;save_state()

def partial(px):
    global BAL,DECISION
    p=POS;q=p['qty']*PARTIAL_FRAC;x=px*(1-SLIP if p['side']=='LONG' else 1+SLIP);n=((x-p['entry']) if p['side']=='LONG' else (p['entry']-x))*q-(p['entry']+x)*q*FEE;BAL+=n;p['qty']-=q;p['pnl_part']=n;p['partial']=True;p['sl']=target(p['side'],p['entry'],0);DECISION='PARTIAL_60';save_state()

def close(px,why):
    global BAL,POS,HIST,CD,DECISION
    p=POS;x=px*(1-SLIP if p['side']=='LONG' else 1+SLIP);n=((x-p['entry']) if p['side']=='LONG' else (p['entry']-x))*p['qty']-(p['entry']+x)*p['qty']*FEE
    n+=p.get('pnl_part',0);BAL+=n-p.get('pnl_part',0);t={'version':BUILD,'symbol':SYMBOL,'side':p['side'],'entry':p['entry'],'exit':x,'qty':p['iq'],'pnl':n,'risk':p['risk'],'meta':p['meta'],'reason':why,'opened':p['opened'],'closed':now().isoformat()};save_trade(t);HIST.insert(0,t);HIST=HIST[:300];CD=now()+timedelta(minutes=15 if n<0 else 5);POS=None;DECISION='CLOSE_'+why;save_state()

async def manage():
    if not POS:return
    p=POS;px=await price();r=net(p['side'],p['entry'],px)*p['iq']/max(p['risk'],1e-12)
    if not p['partial'] and r>=PARTIAL_R:partial(px);p=POS
    if (p['side']=='LONG' and px<=p['sl']) or (p['side']=='SHORT' and px>=p['sl']):close(px,'STOP');return
    if (p['side']=='LONG' and px>=p['tp']) or (p['side']=='SHORT' and px<=p['tp']):close(px,'RUNNER');return
    if (now()-datetime.fromisoformat(p['opened'])).total_seconds()/60>=MAX_MIN:close(px,'TIME')

async def cycle():
    global WATCH,LAST_CYCLE,ERR,DECISION
    try:
        await manage()
        if POS:return
        if CD and now()<CD:DECISION='COOLDOWN';return
        a=await analyze()
        if not a['ok']:DECISION='WAIT_COST';WATCH=None;return
        side='LONG' if a['lc'] and a['lb'] else 'SHORT' if a['sc'] and a['sb'] else None
        if not side:DECISION='WAIT';WATCH=None;return
        tr=a['bh'] if side=='LONG' else a['bl'];px=await price();tol=max(float(a['atr1'] or 0),1e-12)*.12
        if not WATCH or WATCH.get('t')!=a['t'] or WATCH.get('side')!=side:WATCH={'t':a['t'],'side':side,'tr':tr,'at':time.time(),'rt':False};DECISION='ARM_'+side;return
        if time.time()-WATCH['at']>240:WATCH=None;DECISION='TIMEOUT';return
        if not WATCH['rt']:
            if tr-tol<=px<=tr+tol:WATCH['rt']=True;DECISION='RETEST'
            return
        if not ((side=='LONG' and px>=tr+tol*.4) or (side=='SHORT' and px<=tr-tol*.4)):return
        m=await micro();good=m['same'] and m['spr']<=.0004 and ((side=='LONG' and m['imb']>=.54 and m['ofi']>=.05) or (side=='SHORT' and m['imb']<=.46 and m['ofi']<=-.05))
        if not good:DECISION='REJECT_MICRO';return
        if a['t']==LAST:return
        openpos(a,side,px,tr,m);WATCH=None;ERR=None
    except Exception as e:ERR=repr(e);DECISION='ERROR';raise
    finally:LAST_CYCLE=now().isoformat()

async def loop():
    while True:
        try:await cycle()
        except Exception as e:print('V11 LOOP',repr(e),flush=True)
        await asyncio.sleep(5)

async def startup():
    global CLIENT,bot_task
    init_db();load();CLIENT=CLIENT or httpx.AsyncClient();bot_task=bot_task if bot_task and not bot_task.done() else asyncio.create_task(loop())
async def shutdown():
    global CLIENT,bot_task
    if bot_task:bot_task.cancel();await asyncio.gather(bot_task,return_exceptions=True);bot_task=None
    if CLIENT:await CLIENT.aclose();CLIENT=None

def snapshot():
    r=[x for x in HIST if x['version']==BUILD];w=[x for x in r if x['pnl']>0];gp=sum(x['pnl'] for x in w);gl=abs(sum(x['pnl'] for x in r if x['pnl']<0));pf=gp/gl if gl else (999 if gp else 0);exp=sum(x['pnl']/max(x['risk'],1e-12) for x in r)/len(r) if r else 0
    return {'build':BUILD,'balance':BAL,'position':POS,'trades':len(r),'wins':len(w),'win_rate':len(w)/len(r)*100 if r else 0,'pnl':sum(x['pnl'] for x in r),'profit_factor':pf,'expectancy_r':exp,'validation':'COLLECTING_SAMPLE' if len(r)<30 else 'PROMISING' if pf>=1.2 and exp>0 else 'REVISE','history':r[:50],'last_cycle_at':LAST_CYCLE,'last_error':ERR,'last_decision':DECISION}
@app.get('/analyze')
async def ar():return JSONResponse(snapshot(),headers={'Cache-Control':'no-store'})
@app.get('/',response_class=HTMLResponse)
async def dash():return HTMLResponse('<html><body style="background:#08121f;color:white;font-family:system-ui"><h1>V11 Evidence XRP</h1><p>PAPER · XRPUSDC · breakout + retest + OFI + volatility risk scaling</p><pre id="x"></pre><script>setInterval(async()=>x.textContent=JSON.stringify(await(await fetch("analyze")).json(),null,2),5000)</script></body></html>')
