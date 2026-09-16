import asyncio, math, statistics, time
from datetime import datetime
from fib_strategy import fib_pullback

BUILD="v8-fly-antifakeout-20260916-1"
Z_ARMED=0.40; Z_STRONG=0.80; Z_DANGER=0.55; ARMED_MAX_DISTANCE_ATR=0.18
MAX_REAL_SPREAD_PCT=0.0008; DANGER_EXIT_SCORE=2; DANGER_MAX_MR=0.45
BREAKEVEN_TRIGGER_R=0.75; PROFIT_MODE_R=0.90; PROFIT_GIVEBACK_R=0.35; PROFIT_MIN_LOCK_R=0.20; MONITOR_REFRESH_SECONDS=30.0
ANTI_STRONG_VOL=1.20; ANTI_BOOK_MARGIN=0.03; RETEST_TOL_ATR=0.08; RETEST_MAX_SECONDS=120.0
m=None; _monitor_cache={}; _breakout_watch={}

def z_momentum(closes,minutes=5,vol_window=30):
    if len(closes)<max(vol_window+2,minutes+2):return 0.0
    logs=[]
    for i in range(max(1,len(closes)-vol_window-1),len(closes)):
        if closes[i]>0 and closes[i-1]>0:logs.append(math.log(closes[i]/closes[i-1]))
    if len(logs)<2:return 0.0
    sigma=statistics.pstdev(logs[-vol_window:])
    return 0.0 if sigma<=1e-12 else math.log(closes[-1]/closes[-1-minutes])/(sigma*math.sqrt(minutes))

async def book(symbol):
    d=await m.binance_get('/api/v3/depth',{'symbol':symbol,'limit':m.ORDER_BOOK_LEVELS}); bids=d.get('bids',[]); asks=d.get('asks',[])
    if not bids or not asks:return {'imbalance':.5,'spread_pct':1.,'best_bid':None,'best_ask':None}
    b=sum(float(p)*float(q) for p,q in bids); a=sum(float(p)*float(q) for p,q in asks); bid=float(bids[0][0]); ask=float(asks[0][0]); mid=(bid+ask)/2
    return {'imbalance':b/(a+b) if a+b else .5,'spread_pct':(ask-bid)/mid if mid else 1.,'best_bid':bid,'best_ask':ask}

async def strategy(symbol):
    k1,k5,bk=await asyncio.gather(m.get_klines(symbol,'1m'),m.get_klines(symbol,'5m'),book(symbol)); a1,a5=k1[:-1],k5[:-1]
    h=[float(x[2]) for x in a1]; l=[float(x[3]) for x in a1]; c=[float(x[4]) for x in a1]; v=[float(x[5]) for x in a1]
    h5=[float(x[2]) for x in a5]; l5=[float(x[3]) for x in a5]; c5=[float(x[4]) for x in a5]; ct=int(a1[-1][0]); hi,lo,cl=h[-1],l[-1],c[-1]
    e9,e21=m.ema(c,9),m.ema(c,21); e20,e50=m.ema(c5,20),m.ema(c5,50); rv=m.rsi_wilder(c); av=m.atr_wilder(h,l,c); ad=m.adx_wilder(h5,l5,c5); mh,mhp=m.macd_hist(c); vw=m.vwap(h,l,c,v)
    pv=v[-21:-1]; vr=v[-1]/(sum(pv)/len(pv)) if pv and sum(pv)>0 else 0; imb=float(bk['imbalance']); spread=float(bk['spread_pct']); z=z_momentum(c); sep=abs(e20-e50)/cl if cl and e20 is not None and e50 is not None else 0
    if ad is not None and ad>=m.TREND_ADX_MIN and sep>=m.EMA_SEP_MIN:regime='TREND_LONG' if c5[-1]>e20>e50 else 'TREND_SHORT' if c5[-1]<e20<e50 else 'TRANSITION'
    elif ad is not None and ad<=m.RANGE_ADX_MAX:regime='RANGE'
    else:regime='TRANSITION'
    rng=max(hi-lo,1e-12); bull=(cl-lo)/rng; bear=(hi-cl)/rng; bh=max(h[-m.BREAKOUT_LOOKBACK-1:-1]); bl=min(l[-m.BREAKOUT_LOOKBACK-1:-1]); mac_up=mh is not None and (mh>0 or (mhp is not None and mh>mhp)); mac_dn=mh is not None and (mh<0 or (mhp is not None and mh<mhp)); spread_ok=spread<=MAX_REAL_SPREAD_PCT
    ls=sum([e9>e21,cl>e9,40<=rv<=70,mac_up,bull>=.55,vr>=m.MIN_TREND_VOLUME,spread_ok and imb>=m.BOOK_LONG_MIN,vw is not None and cl>=vw]); ss=sum([e9<e21,cl<e9,30<=rv<=60,mac_dn,bear>=.55,vr>=m.MIN_TREND_VOLUME,spread_ok and imb<=m.BOOK_SHORT_MAX,vw is not None and cl<=vw])
    raw='WAIT'; setup=None; score=0; fib=fib_pullback(h,l,c,v,lookback=30,min_impulse_pct=.0045,min_volume_ratio=.85)
    if regime=='TREND_LONG' and cl>bh and vr>=m.MIN_BREAKOUT_VOLUME and ls>=m.MIN_SCORE:raw,setup,score='LONG','BREAKOUT',ls
    elif regime=='TREND_SHORT' and cl<bl and vr>=m.MIN_BREAKOUT_VOLUME and ss>=m.MIN_SCORE:raw,setup,score='SHORT','BREAKOUT',ss
    elif fib and fib['signal']=='LONG' and regime=='TREND_LONG' and ls>=max(5,m.MIN_SCORE-1):raw,setup,score='LONG','FIB_0618_0786',ls
    elif fib and fib['signal']=='SHORT' and regime=='TREND_SHORT' and ss>=max(5,m.MIN_SCORE-1):raw,setup,score='SHORT','FIB_0618_0786',ss
    signal=raw; reject=None; edge=0.0
    if raw in ('LONG','SHORT'):
        p=m.SETUP_PARAMS.get(setup,m.SETUP_PARAMS['BREAKOUT']); edge=(av*p['atr_mult']*p['rr'])/cl if av and cl else 0
        if edge<m.ROUND_TRIP_COST*m.MIN_EDGE_MULTIPLE:signal,reject='WAIT','EDGE_TOO_SMALL'
        elif not spread_ok:signal,reject='WAIT',f'REAL_SPREAD_{spread*100:.3f}%'
        elif raw=='LONG' and z<0.15:signal,reject='WAIT',f'Z_TOO_WEAK_{z:.2f}'
        elif raw=='SHORT' and z>-0.15:signal,reject='WAIT',f'Z_TOO_WEAK_{z:.2f}'
    armed_side=armed_trigger=armed_dist=None
    if av and av>0 and spread_ok and raw=='WAIT':
        ld=(bh-cl)/av; sd=(cl-bl)/av
        if regime=='TREND_LONG' and 0<=ld<=ARMED_MAX_DISTANCE_ATR and ls>=max(5,m.MIN_SCORE-1) and vr>=m.MIN_TREND_VOLUME and z>=Z_ARMED and imb>=m.BOOK_LONG_MIN:armed_side,armed_trigger,armed_dist='LONG',bh,ld
        elif regime=='TREND_SHORT' and 0<=sd<=ARMED_MAX_DISTANCE_ATR and ss>=max(5,m.MIN_SCORE-1) and vr>=m.MIN_TREND_VOLUME and z<=-Z_ARMED and imb<=m.BOOK_SHORT_MAX:armed_side,armed_trigger,armed_dist='SHORT',bl,sd
    zclass='STRONG_LONG' if z>=Z_STRONG else 'ARMED_LONG' if z>=Z_ARMED else 'STRONG_SHORT' if z<=-Z_STRONG else 'ARMED_SHORT' if z<=-Z_ARMED else 'IGNORE'; reason=f'{symbol} {regime} raw={raw} setup={setup} L/S={ls}/{ss} book={imb:.3f} spread={spread*100:.3f}% vol={vr:.2f}x z={z:.2f} edge={edge*100:.3f}%'
    if armed_side:reason+=f' ARMED={armed_side}@{armed_trigger:.8f}'
    if reject:reason+=f' REJECT={reject}'
    out={'symbol':symbol,'price':float(k1[-1][4]),'signal':signal,'raw_signal':raw,'setup':setup,'score':score,'candle_time':ct,'regime':regime,'rsi':rv,'atr':av,'adx5':ad,'volume_ratio':vr,'book_imbalance':imb,'real_spread_pct':spread,'z_momentum':z,'z_class':zclass,'armed_side':armed_side,'armed_trigger':armed_trigger,'armed_distance_atr':armed_dist,'reason':reason}
    if fib:out.update({k:fib[k] for k in ('fib_0618','fib_0786','swing_high','swing_low')})
    return out

def open_trade(a,price):
    if m.paper_position or not a.get('atr'):return
    setup=a.get('setup') or 'BREAKOUT'; p=m.SETUP_PARAMS.get(setup,m.SETUP_PARAMS['BREAKOUT']); dist=max(float(a['atr'])*p['atr_mult'],price*m.MIN_STOP_RATE)
    if dist/price>m.MAX_STOP_RATE:return
    side=a['signal']; entry=price*(1+m.SLIPPAGE_RATE if side=='LONG' else 1-m.SLIPPAGE_RATE); sl=entry-dist if side=='LONG' else entry+dist; nloss=-m.estimated_net_per_unit(side,entry,sl)
    if nloss<=0:return
    risk=m.PAPER_BALANCE*m.RISK_PER_TRADE; tp=m.target_market_for_net_profit(side,entry,nloss*m.NET_RISK_REWARD); qty=min(risk/nloss,m.PAPER_BALANCE*m.MAX_NOTIONAL_SHARE/entry)
    m.paper_position={'symbol':a['symbol'],'side':side,'setup':setup,'regime':a['regime'],'score':a.get('score',0),'entry_price':entry,'qty':qty,'stop_loss':sl,'take_profit':tp,'risk_distance':dist,'initial_risk_usdc':qty*nloss,'net_rr':m.NET_RISK_REWARD,'mae_r':0.,'mfe_r':0.,'breakeven_moved':False,'profit_mode':False,'z_entry':float(a.get('z_momentum') or 0),'entry_trigger':float(a.get('entry_trigger') or a.get('armed_trigger') or price),'entry_spread_pct':float(a.get('real_spread_pct') or 0),'entry_book_imbalance':float(a.get('book_imbalance') or .5),'entry_volume_ratio':float(a.get('volume_ratio') or 0),'entry_kind':a.get('entry_kind','CLOSED_CANDLE'),'last_danger_score':0,'opened_at':m.utcnow().isoformat()}; m.last_entry_candle[a['symbol']]=a['candle_time']; m.save_state(); m.log_signal(a,'ENTER',f'{setup} {m.paper_position["entry_kind"]} z={m.paper_position["z_entry"]:.2f}')

def close_trade(price,reason):
    if not m.paper_position:return
    p=m.paper_position;e=float(p['entry_price']);q=float(p['qty']);x=price*(1-m.SLIPPAGE_RATE if p['side']=='LONG' else 1+m.SLIPPAGE_RATE);gross=(x-e)*q if p['side']=='LONG' else (e-x)*q;fees=(e*q+x*q)*m.FEE_RATE;net=gross-fees;risk=max(float(p.get('initial_risk_usdc') or 0),1e-12);rr=net/risk;mfe=float(p.get('mfe_r',0));mae=float(p.get('mae_r',0));cap=(rr/mfe*100) if mfe>0 and rr>0 else 0;age=(m.utcnow()-datetime.fromisoformat(p['opened_at'])).total_seconds()/60;detail=f'{reason} | R={rr:.2f} MFE={mfe:.2f} MAE={mae:.2f} CAP={cap:.0f}% DUR={age:.1f}m Z={float(p.get("z_entry",0)):.2f}';m.PAPER_BALANCE+=net;now=m.utcnow();t={**p,'exit_price':x,'gross_pnl':gross,'fees':fees,'pnl':net,'reason':detail,'closed_at':now.isoformat()};m.save_trade(t);m.trade_history.insert(0,t);m.trade_history=m.trade_history[:500];m.cooldown_until=now+m.timedelta(minutes=2 if net<0 else 0);m.paper_position=None;m.save_state()

async def manage_position():
    if not m.paper_position:return
    p=m.paper_position;price=await m.get_live_price(p['symbol'],max_age=1.);e=float(p['entry_price']);d=float(p['risk_distance']);mr=(price-e)/d if p['side']=='LONG' else (e-price)/d;p['mfe_r']=max(float(p.get('mfe_r',0)),mr);p['mae_r']=min(float(p.get('mae_r',0)),mr)
    if not p.get('breakeven_moved') and mr>=BREAKEVEN_TRIGGER_R:p['stop_loss']=e*(1+m.ROUND_TRIP_COST) if p['side']=='LONG' else e*(1-m.ROUND_TRIP_COST);p['breakeven_moved']=True;m.save_state()
    if p['side']=='LONG' and price<=float(p['stop_loss']) or p['side']=='SHORT' and price>=float(p['stop_loss']):close_trade(price,'STOP/BREAKEVEN');return
    if p['side']=='LONG' and price>=float(p['take_profit']) or p['side']=='SHORT' and price<=float(p['take_profit']):close_trade(price,'TAKE PROFIT');return
    age=(m.utcnow()-datetime.fromisoformat(p['opened_at'])).total_seconds()/60
    if age>=m.MAX_TRADE_MINUTES:close_trade(price,'TIME EXIT')

def choose_best(rows):
    confirmed=[r for r in rows if r.get('signal') in ('LONG','SHORT') and m.last_entry_candle.get(r['symbol'])!=r.get('candle_time')]
    if confirmed:return sorted(confirmed,key=lambda r:(int(r.get('score',0)),abs(float(r.get('z_momentum') or 0))),reverse=True)[0]
    armed=[r for r in rows if r.get('armed_side') in ('LONG','SHORT') and m.last_entry_candle.get(r['symbol'])!=r.get('candle_time')]
    return sorted(armed,key=lambda r:(abs(float(r.get('z_momentum') or 0)),-float(r.get('armed_distance_atr') or 999)),reverse=True)[0] if armed else None

def strong_breakout(a,side):
    z=float(a.get('z_momentum') or 0); vr=float(a.get('volume_ratio') or 0); imb=float(a.get('book_imbalance') or .5)
    if vr<ANTI_STRONG_VOL:return False
    if side=='LONG':return z>=Z_STRONG and imb>=min(.95,m.BOOK_LONG_MIN+ANTI_BOOK_MARGIN)
    return z<=-Z_STRONG and imb<=max(.05,m.BOOK_SHORT_MAX-ANTI_BOOK_MARGIN)

async def cycle():
    try:
        await manage_position()
        if m.paper_position:return
        if m.cooldown_until and m.utcnow()<m.cooldown_until:return
        rows=await m.analyze_all();best=choose_best(rows)
        if not best:return
        price=await m.get_live_price(best['symbol'],max_age=1.)
        if best.get('signal') in ('LONG','SHORT'):
            open_trade(best,price);return
        side=best.get('armed_side'); trigger=best.get('armed_trigger'); symbol=best['symbol']
        if side not in ('LONG','SHORT') or trigger is None:return
        trigger=float(trigger); atr=max(float(best.get('atr') or 0),1e-12); crossed=(side=='LONG' and price>=trigger) or (side=='SHORT' and price<=trigger); now=time.time(); watch=_breakout_watch.get(symbol)
        if crossed and strong_breakout(best,side):
            early=dict(best); early['signal']=side; early['raw_signal']=side; early['setup']='BREAKOUT'; early['entry_kind']='ANTI_STRONG_BREAKOUT'; early['entry_trigger']=trigger; _breakout_watch.pop(symbol,None); open_trade(early,price);return
        if crossed:
            if not watch or watch.get('side')!=side or abs(float(watch.get('trigger',0))-trigger)>atr*.02:_breakout_watch[symbol]={'side':side,'trigger':trigger,'crossed_at':now,'retested':False}
            return
        if not watch:return
        if now-float(watch.get('crossed_at',now))>RETEST_MAX_SECONDS:_breakout_watch.pop(symbol,None);return
        if watch.get('side')!=side:return
        tol=atr*RETEST_TOL_ATR
        touched=(side=='LONG' and trigger-tol<=price<=trigger+tol) or (side=='SHORT' and trigger-tol<=price<=trigger+tol)
        if touched:watch['retested']=True;return
        held=(side=='LONG' and watch.get('retested') and price>trigger+tol*.25) or (side=='SHORT' and watch.get('retested') and price<trigger-tol*.25)
        if held:
            ret=dict(best); ret['signal']=side; ret['raw_signal']=side; ret['setup']='BREAKOUT'; ret['entry_kind']='ANTI_RETEST_BREAKOUT'; ret['entry_trigger']=trigger; _breakout_watch.pop(symbol,None); open_trade(ret,price)
    finally:m.last_cycle_at=m.utcnow().isoformat()

def install(module):
    global m;m=module
    m.SETUP_PARAMS['FIB_0618_0786']={'atr_mult':1.0,'rr':1.70};m.ENABLED_SETUPS={'BREAKOUT','FIB_0618_0786'}
    m.strategy_analysis=strategy;m.open_trade=open_trade;m.manage_position=manage_position;m.cycle=cycle;m.FLY_LAYER_BUILD=BUILD
