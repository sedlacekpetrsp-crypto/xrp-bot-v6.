import asyncio, math, statistics, time
from datetime import datetime
import news_signal

BUILD = "v8-fly-layer-20260921-4"
Z_ARMED = 0.60
Z_STRONG = 0.80
Z_DANGER = 0.55
ARMED_MAX_DISTANCE_ATR = 0.10
MAX_REAL_SPREAD_PCT = 0.0008
DANGER_EXIT_SCORE = 2
DANGER_MAX_MR = 0.45
BREAKEVEN_TRIGGER_R = 0.75
PROFIT_MODE_R = 0.90
PROFIT_GIVEBACK_R = 0.35
PROFIT_MIN_LOCK_R = 0.20
MONITOR_REFRESH_SECONDS = 30.0

STRONG_RISK_RATE = 0.0035
APLUS_RISK_RATE = 0.0050

def quality_risk(a):
    side = a.get('signal')
    score = int(a.get('score') or 0)
    vol = float(a.get('volume_ratio') or 0)
    z = abs(float(a.get('z_momentum') or 0))
    spread = float(a.get('real_spread_pct') or 1)
    edge = float(a.get('expected_move_pct') or 0)
    imb = float(a.get('book_imbalance') or 0.5)
    book_strong = imb >= 0.56 if side == 'LONG' else imb <= 0.44
    book_aplus = imb >= 0.58 if side == 'LONG' else imb <= 0.42

    if (score >= 8 and vol >= 2.20 and z >= 1.30 and book_aplus
            and spread <= 0.0004 and edge >= m.ROUND_TRIP_COST * 4.50):
        return 'A+', APLUS_RISK_RATE
    if (score >= 8 and vol >= 1.80 and z >= 1.00 and book_strong
            and spread <= 0.0005 and edge >= m.ROUND_TRIP_COST * 3.50):
        return 'STRONG', STRONG_RISK_RATE
    return 'STANDARD', m.RISK_PER_TRADE

m = None
_monitor_cache = {}

def z_momentum(closes, minutes=5, vol_window=30):
    if len(closes) < max(vol_window + 2, minutes + 2): return 0.0
    logs=[]
    for i in range(max(1,len(closes)-vol_window-1),len(closes)):
        if closes[i] > 0 and closes[i-1] > 0: logs.append(math.log(closes[i]/closes[i-1]))
    if len(logs) < 2: return 0.0
    sigma = statistics.pstdev(logs[-vol_window:])
    if sigma <= 1e-12: return 0.0
    return math.log(closes[-1]/closes[-1-minutes])/(sigma*math.sqrt(minutes))

async def book(symbol):
    d=await m.binance_get('/api/v3/depth',{'symbol':symbol,'limit':m.ORDER_BOOK_LEVELS})
    bids=d.get('bids',[]); asks=d.get('asks',[])
    if not bids or not asks: return {'imbalance':0.5,'spread_pct':1.0,'best_bid':None,'best_ask':None}
    b=sum(float(p)*float(q) for p,q in bids); a=sum(float(p)*float(q) for p,q in asks)
    bid=float(bids[0][0]); ask=float(asks[0][0]); mid=(bid+ask)/2
    return {'imbalance':b/(a+b) if a+b else .5,'spread_pct':(ask-bid)/mid if mid else 1.0,'best_bid':bid,'best_ask':ask}

async def strategy(symbol):
    if symbol == 'XRPUSDC':
        k1,k5,bk,news=await asyncio.gather(m.get_klines(symbol,'1m'),m.get_klines(symbol,'5m'),book(symbol),news_signal.get_xrp_news())
    else:
        k1,k5,bk=await asyncio.gather(m.get_klines(symbol,'1m'),m.get_klines(symbol,'5m'),book(symbol))
        news={'bullish':False,'bearish':False,'score':0,'headlines':[],'status':'n/a'}
    a1,a5=k1[:-1],k5[:-1]
    h=[float(x[2]) for x in a1]; l=[float(x[3]) for x in a1]; c=[float(x[4]) for x in a1]; v=[float(x[5]) for x in a1]
    h5=[float(x[2]) for x in a5]; l5=[float(x[3]) for x in a5]; c5=[float(x[4]) for x in a5]
    ct=int(a1[-1][0]); hi,lo,cl=h[-1],l[-1],c[-1]
    e9,e21=m.ema(c,9),m.ema(c,21); e20,e50=m.ema(c5,20),m.ema(c5,50)
    rv=m.rsi_wilder(c); av=m.atr_wilder(h,l,c); ad=m.adx_wilder(h5,l5,c5); mh,mhp=m.macd_hist(c); vw=m.vwap(h,l,c,v)
    pv=v[-21:-1]; vr=v[-1]/(sum(pv)/len(pv)) if pv and sum(pv)>0 else 0
    imb=float(bk['imbalance']); spread=float(bk['spread_pct']); z=z_momentum(c)
    sep=abs(e20-e50)/cl if cl and e20 is not None and e50 is not None else 0
    if ad is not None and ad>=m.TREND_ADX_MIN and sep>=m.EMA_SEP_MIN:
        regime='TREND_LONG' if c5[-1]>e20>e50 else 'TREND_SHORT' if c5[-1]<e20<e50 else 'TRANSITION'
    elif ad is not None and ad<=m.RANGE_ADX_MAX: regime='RANGE'
    else: regime='TRANSITION'
    rng=max(hi-lo,1e-12); bull=(cl-lo)/rng; bear=(hi-cl)/rng
    bh=max(h[-m.BREAKOUT_LOOKBACK-1:-1]); bl=min(l[-m.BREAKOUT_LOOKBACK-1:-1])
    mac_up=mh is not None and (mh>0 or (mhp is not None and mh>mhp)); mac_dn=mh is not None and (mh<0 or (mhp is not None and mh<mhp))
    spread_ok=spread<=MAX_REAL_SPREAD_PCT
    ls=sum([e9>e21,cl>e9,40<=rv<=70,mac_up,bull>=.55,vr>=m.MIN_TREND_VOLUME,spread_ok and imb>=m.BOOK_LONG_MIN,vw is not None and cl>=vw])
    ss=sum([e9<e21,cl<e9,30<=rv<=60,mac_dn,bear>=.55,vr>=m.MIN_TREND_VOLUME,spread_ok and imb<=m.BOOK_SHORT_MAX,vw is not None and cl<=vw])
    raw='WAIT'; setup=None; score=0
    if regime=='TREND_LONG' and cl>bh and vr>=max(m.MIN_BREAKOUT_VOLUME,1.50) and ls>=max(m.MIN_SCORE,8):
        raw,setup,score='LONG','BREAKOUT',ls
    elif regime=='TREND_SHORT' and cl<bl and vr>=max(m.MIN_BREAKOUT_VOLUME,1.50) and ss>=max(m.MIN_SCORE,8):
        raw,setup,score='SHORT','BREAKOUT',ss

    # NEWS_LONG: positive XRP/Ripple news is allowed to create an entry only
    # when price/volume/order-book confirm that the market is reacting.
    if symbol=='XRPUSDC' and raw=='WAIT' and news.get('bullish') and not news.get('bearish'):
        news_confirm = (
            cl > e9 > e21
            and cl >= bh * 0.999
            and vr >= 1.80
            and z >= 1.00
            and spread_ok
            and imb >= 0.56
            and ls >= 7
        )
        if news_confirm:
            raw,setup,score='LONG','NEWS_LONG',max(ls,8)
    signal=raw; reject=None; edge=0.0
    if raw in ('LONG','SHORT'):
        p=m.SETUP_PARAMS['BREAKOUT']; edge=(av*p['atr_mult']*p['rr'])/cl if av and cl else 0
        if edge < m.ROUND_TRIP_COST*m.MIN_EDGE_MULTIPLE: signal,reject='WAIT','EDGE_TOO_SMALL'
        elif not spread_ok: signal,reject='WAIT',f'REAL_SPREAD_{spread*100:.3f}%'
        elif raw=='LONG' and news.get('bearish'): signal,reject='WAIT','NEGATIVE_NEWS_BLOCK'
        elif raw=='LONG' and z<Z_ARMED: signal,reject='WAIT',f'Z_TOO_WEAK_{z:.2f}'
        elif raw=='SHORT' and z>-Z_ARMED: signal,reject='WAIT',f'Z_TOO_WEAK_{z:.2f}'
    armed_side=None; armed_trigger=None; armed_dist=None
    if av and av>0 and spread_ok and raw=='WAIT':
        ld=(bh-cl)/av; sd=(cl-bl)/av
        if regime=='TREND_LONG' and 0<=ld<=ARMED_MAX_DISTANCE_ATR and ls>=max(8,m.MIN_SCORE) and vr>=max(m.MIN_BREAKOUT_VOLUME,1.50) and z>=Z_STRONG and imb>=max(m.BOOK_LONG_MIN,0.55):
            armed_side,armed_trigger,armed_dist='LONG',bh,ld
        elif regime=='TREND_SHORT' and 0<=sd<=ARMED_MAX_DISTANCE_ATR and ss>=max(8,m.MIN_SCORE) and vr>=max(m.MIN_BREAKOUT_VOLUME,1.50) and z<=-Z_STRONG and imb<=min(m.BOOK_SHORT_MAX,0.45):
            armed_side,armed_trigger,armed_dist='SHORT',bl,sd
    zclass='STRONG_LONG' if z>=Z_STRONG else 'ARMED_LONG' if z>=Z_ARMED else 'STRONG_SHORT' if z<=-Z_STRONG else 'ARMED_SHORT' if z<=-Z_ARMED else 'IGNORE'
    reason=f'{symbol} {regime} raw={raw} L/S={ls}/{ss} book={imb:.3f} spread={spread*100:.3f}% vol={vr:.2f}x z={z:.2f} edge={edge*100:.3f}% news={int(news.get("score") or 0)}'
    if armed_side: reason+=f' ARMED={armed_side}@{armed_trigger:.6f}'
    if reject: reason+=f' REJECT={reject}'
    return {'symbol':symbol,'price':float(k1[-1][4]),'signal':signal,'raw_signal':raw,'setup':setup,'score':score,'news':news,'candle_time':ct,'regime':regime,'rsi':rv,'atr':av,'adx5':ad,'volume_ratio':vr,'book_imbalance':imb,'book_spread':spread,'real_spread_pct':spread,'best_bid':bk['best_bid'],'best_ask':bk['best_ask'],'long_score':ls,'short_score':ss,'breakout_high':bh,'breakout_low':bl,'expected_move_pct':edge,'z_momentum':z,'z_class':zclass,'armed_side':armed_side,'armed_trigger':armed_trigger,'armed_distance_atr':armed_dist,'reason':reason}

def open_trade(a,price):
    if m.paper_position or not a.get('atr'): return
    p=m.SETUP_PARAMS['BREAKOUT']; dist=max(float(a['atr'])*p['atr_mult'],price*m.MIN_STOP_RATE)
    if dist/price>m.MAX_STOP_RATE: return
    side=a['signal']; entry=price*(1+m.SLIPPAGE_RATE if side=='LONG' else 1-m.SLIPPAGE_RATE); sl=entry-dist if side=='LONG' else entry+dist
    nloss=-m.estimated_net_per_unit(side,entry,sl)
    if nloss<=0:return
    quality,risk_rate=quality_risk(a)
    if a.get('setup')=='NEWS_LONG':
        quality='NEWS+' if quality=='STANDARD' else 'NEWS_'+quality
        risk_rate=min(risk_rate, STRONG_RISK_RATE)
    risk=m.PAPER_BALANCE*risk_rate; tp=m.target_market_for_net_profit(side,entry,nloss*m.NET_RISK_REWARD); qty=min(risk/nloss,m.PAPER_BALANCE*m.MAX_NOTIONAL_SHARE/entry)
    actual_risk=qty*nloss
    m.paper_position={'symbol':a['symbol'],'side':side,'setup':a.get('setup') or 'BREAKOUT','regime':a['regime'],'score':a.get('score',0),'entry_price':entry,'qty':qty,'stop_loss':sl,'take_profit':tp,'risk_distance':dist,'initial_risk_usdc':actual_risk,'risk_rate':risk_rate,'quality_tier':quality,'net_rr':m.NET_RISK_REWARD,'mae_r':0.0,'mfe_r':0.0,'breakeven_moved':False,'profit_mode':False,'z_entry':float(a.get('z_momentum') or 0),'entry_trigger':float(a.get('entry_trigger') or a.get('armed_trigger') or price),'entry_spread_pct':float(a.get('real_spread_pct') or 0),'entry_kind':a.get('entry_kind','CLOSED_CANDLE'),'last_danger_score':0,'opened_at':m.utcnow().isoformat()}
    m.last_entry_candle[a['symbol']]=a['candle_time']; m.save_state(); m.log_signal(a,'ENTER',f"{quality} risk={risk_rate*100:.2f}% {m.paper_position['entry_kind']} z={m.paper_position['z_entry']:.2f}")

def close_trade(price,reason):
    if not m.paper_position:return
    p=m.paper_position; e=float(p['entry_price']); q=float(p['qty']); x=price*(1-m.SLIPPAGE_RATE if p['side']=='LONG' else 1+m.SLIPPAGE_RATE)
    gross=(x-e)*q if p['side']=='LONG' else (e-x)*q; fees=(e*q+x*q)*m.FEE_RATE; net=gross-fees; risk=max(float(p.get('initial_risk_usdc') or 0),1e-12); rr=net/risk; mfe=float(p.get('mfe_r',0)); mae=float(p.get('mae_r',0)); cap=(rr/mfe*100) if mfe>0 and rr>0 else 0; age=(m.utcnow()-datetime.fromisoformat(p['opened_at'])).total_seconds()/60
    detail=f'{reason} | {p.get("quality_tier","STANDARD")} risk={float(p.get("risk_rate",m.RISK_PER_TRADE))*100:.2f}% R={rr:.2f} MFE={mfe:.2f} MAE={mae:.2f} CAP={cap:.0f}% DUR={age:.1f}m Z={float(p.get("z_entry",0)):.2f} DANGER={int(p.get("last_danger_score",0))}'
    m.PAPER_BALANCE+=net; now=m.utcnow(); t={**p,'exit_price':x,'gross_pnl':gross,'fees':fees,'pnl':net,'reason':detail,'closed_at':now.isoformat(),'realized_r':rr,'profit_capture_pct':cap,'duration_min':age}; m.save_trade(t); m.trade_history.insert(0,t); m.trade_history=m.trade_history[:500]
    _,streak,_,_=m.daily_risk_status(); cd=2 if net<0 else 0
    if net<0 and streak>=m.MAX_CONSECUTIVE_LOSSES: cd=m.LOSS_STREAK_COOLDOWN_MIN
    m.cooldown_until=now+m.timedelta(minutes=cd); m.paper_position=None; m.save_state()

async def monitor(symbol):
    now=time.monotonic(); old=_monitor_cache.get(symbol)
    if old and now-old['ts']<MONITOR_REFRESH_SECONDS:return old['data']
    k,bk=await asyncio.gather(m.get_klines(symbol,'1m',limit=60),book(symbol)); closes=[float(x[4]) for x in k[:-1]]; data={'z3':z_momentum(closes,3,30),'book':float(bk['imbalance']),'spread':float(bk['spread_pct'])}; _monitor_cache[symbol]={'ts':now,'data':data}; return data

async def manage_position():
    if not m.paper_position:return
    p=m.paper_position; price=await m.get_live_price(p['symbol'],max_age=1.0); e=float(p['entry_price']); d=float(p['risk_distance']); mr=(price-e)/d if p['side']=='LONG' else (e-price)/d; p['mfe_r']=max(float(p.get('mfe_r',0)),mr); p['mae_r']=min(float(p.get('mae_r',0)),mr)
    if not p.get('breakeven_moved') and mr>=BREAKEVEN_TRIGGER_R: p['stop_loss']=e*(1+m.ROUND_TRIP_COST) if p['side']=='LONG' else e*(1-m.ROUND_TRIP_COST); p['breakeven_moved']=True; m.save_state()
    mfe=float(p.get('mfe_r',0)); p['profit_mode']=p.get('profit_mode') or mfe>=PROFIT_MODE_R
    if p.get('profit_mode') and mr>=PROFIT_MIN_LOCK_R and mfe-mr>=PROFIT_GIVEBACK_R: close_trade(price,'PROFIT PULLBACK'); return
    sl,tp=float(p['stop_loss']),float(p['take_profit'])
    if p['side']=='LONG':
        if price<=sl: close_trade(price,'BREAK EVEN' if p.get('breakeven_moved') else 'STOP LOSS'); return
        if price>=tp: close_trade(price,'TAKE PROFIT'); return
    else:
        if price>=sl: close_trade(price,'BREAK EVEN' if p.get('breakeven_moved') else 'STOP LOSS'); return
        if price<=tp: close_trade(price,'TAKE PROFIT'); return
    age=(m.utcnow()-datetime.fromisoformat(p['opened_at'])).total_seconds()/60
    if age>=1:
        mon=await monitor(p['symbol']); trigger=float(p.get('entry_trigger') or e); score=0
        if p['side']=='LONG': score+=mon['z3']<=-Z_DANGER; score+=mon['book']<=.47; score+=price<trigger*.9995
        else: score+=mon['z3']>=Z_DANGER; score+=mon['book']>=.53; score+=price>trigger*1.0005
        score+=mon['spread']>MAX_REAL_SPREAD_PCT; p['last_danger_score']=int(score)
        if score>=DANGER_EXIT_SCORE and mr<=DANGER_MAX_MR: close_trade(price,'DANGER EXIT'); return
    if age>=m.MAX_TRADE_MINUTES and mr<.35: close_trade(price,'TIME EXIT')

def choose_best(rows):
    confirmed=[]; armed=[]
    for x in rows:
        if x.get('signal') in ('LONG','SHORT') and m.last_entry_candle.get(x['symbol'])!=x.get('candle_time'): confirmed.append(((int(x.get('score',0)),abs(float(x.get('z_momentum') or 0))),x))
        elif x.get('armed_side') in ('LONG','SHORT') and m.last_entry_candle.get(x['symbol'])!=x.get('candle_time'): armed.append(((abs(float(x.get('z_momentum') or 0)),-float(x.get('armed_distance_atr') or 999)),x))
    if confirmed: return sorted(confirmed,key=lambda z:z[0],reverse=True)[0][1]
    if armed:return sorted(armed,key=lambda z:z[0],reverse=True)[0][1]
    return None

async def cycle():
    try:
        await manage_position()
        if m.paper_position: m.last_cycle_at=m.utcnow().isoformat(); return
        now=m.utcnow()
        if m.cooldown_until and now<m.cooldown_until: m.last_cycle_at=now.isoformat(); return
        _,streak,blocked,_=m.daily_risk_status()
        # After a loss streak, close_trade() already sets cooldown_until. Do not block
        # the strategy for the rest of the UTC day once that cooldown expires.
        if blocked: m.last_cycle_at=now.isoformat(); return
        rows=await m.analyze_all(); best=choose_best(rows)
        if best:
            price=await m.get_live_price(best['symbol'],max_age=1.0)
            if best.get('signal') in ('LONG','SHORT'): best['entry_kind']='CLOSED_CANDLE'; best['entry_trigger']=price; open_trade(best,price)
            elif best.get('armed_side') in ('LONG','SHORT'):
                side=best['armed_side']; trigger=float(best['armed_trigger']); crossed=price>=trigger if side=='LONG' else price<=trigger
                if crossed and float(best.get('real_spread_pct') or 1)<=MAX_REAL_SPREAD_PCT:
                    a=dict(best); a['signal']=side; a['raw_signal']=side; a['setup']='BREAKOUT'; a['score']=max(int(best.get('long_score') if side=='LONG' else best.get('short_score') or 0),m.MIN_SCORE); a['entry_kind']='ARMED_INTRABAR'; a['entry_trigger']=trigger; open_trade(a,price)
        m.last_cycle_at=m.utcnow().isoformat()
    except Exception as e: m.last_error=f'{type(e).__name__}: {e}'; print('V8 FLY CYCLE',e)

def install(module):
    global m
    if getattr(module,'_fly_layer_installed',False):return module
    m=module; module.strategy_analysis=strategy; module.open_trade=open_trade; module.close_trade=close_trade; module.manage_position=manage_position; module.choose_best=choose_best; module.cycle=cycle; module.FLY_LAYER_BUILD=BUILD; module.app.title='V8 Adaptive Breakout Scalper — Fly Layer'; module._fly_layer_installed=True
    return module
