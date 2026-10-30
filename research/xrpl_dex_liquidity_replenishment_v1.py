"""Frozen XRPL DEX funded-liquidity signal and XRP simulator."""
from dataclasses import dataclass
import math
DAY=86_400_000;STRIDE=120_000
@dataclass(frozen=True)
class Config:
    atr_n:int=14;stop_atr:float=2.;reward_r:float=3.;max_hold:int=5;risk_fraction:float=.005;notional_cap:float=.20;fee:float=.00095;slippage:float=.00020
def _funded(offer):
    try:v=float(offer['owner_funds'])
    except (KeyError,TypeError,ValueError):return None
    return v if math.isfinite(v) and v>0 else None
def summarize(ledger,asks,bids,band=.02,limit=400):
    if ledger.get('validated') is not True or asks.get('validated') is not True or bids.get('validated') is not True:raise ValueError('unvalidated')
    idx=int(ledger['ledger_index']);h=ledger['ledger_hash']
    if int(asks['ledger_index'])!=idx or int(bids['ledger_index'])!=idx or asks['ledger_hash']!=h or bids['ledger_hash']!=h:raise ValueError('ledger mismatch')
    aa=[]
    for o in asks.get('offers',[]):
        f=_funded(o)
        if f is None:continue
        xrp=float(o['TakerGets'])/1e6;usd=float(o['TakerPays']['value']);price=usd/xrp
        if xrp>0 and price>0:aa.append((price,min(xrp,f/1e6)))
    bb=[]
    for o in bids.get('offers',[]):
        f=_funded(o)
        if f is None:continue
        usd=float(o['TakerGets']['value']);xrp=float(o['TakerPays'])/1e6;price=usd/xrp
        if xrp>0 and price>0:bb.append((price,min(usd,f)/price))
    if not aa or not bb:return None
    ask=min(p for p,q in aa if q>0);bid=max(p for p,q in bb if q>0)
    if bid>=ask:return None
    mid=(ask+bid)/2;spread=(ask-bid)/mid
    if spread>band:return None
    ask_cut=mid*(1+band);bid_cut=mid*(1-band)
    def raw_price(o,side):
        return float(o['TakerPays']['value'])/(float(o['TakerGets'])/1e6) if side=='ask' else float(o['TakerGets']['value'])/(float(o['TakerPays'])/1e6)
    if len(asks.get('offers',[]))==limit and raw_price(asks['offers'][-1],'ask')<=ask_cut:return None
    if len(bids.get('offers',[]))==limit and raw_price(bids['offers'][-1],'bid')>=bid_cut:return None
    ad=sum(q for p,q in aa if p<=ask_cut);bd=sum(q for p,q in bb if p>=bid_cut)
    if ad<=0 or bd<=0:return None
    return dict(ledger_index=idx,ledger_hash=h,timestamp=int(ledger['close_time_ms']),best_ask=ask,best_bid=bid,mid=mid,spread=spread,ask_depth_xrp=ad,bid_depth_xrp=bd,total_depth_xrp=ad+bd)
def entry_day(t):return ((t+2*DAY+DAY-1)//DAY)*DAY
def make_signals(obs):
    out={}
    for a,b in zip(obs,obs[1:]):
        if a is not None and b is not None and b['ledger_index']-a['ledger_index']==STRIDE and b['total_depth_xrp']>a['total_depth_xrp'] and b['spread']<=.02:
            out[entry_day(b['timestamp'])]=dict(observation_timestamp=b['timestamp'],ledger_index=b['ledger_index'],ledger_hash=b['ledger_hash'],spread=b['spread'],prior_depth_xrp=a['total_depth_xrp'],total_depth_xrp=b['total_depth_xrp'],ask_depth_xrp=b['ask_depth_xrp'],bid_depth_xrp=b['bid_depth_xrp'])
    return out
def validate(rows):
    for i,x in enumerate(rows):
        if i and x['timestamp']<=rows[i-1]['timestamp']:raise ValueError('price order')
        if not 0<x['low']<=min(x['open'],x['close'])<=max(x['open'],x['close'])<=x['high']:raise ValueError('OHLC')
def atr(rows,i,n):
    if i<n+1:return None
    if any(rows[j]['timestamp']-rows[j-1]['timestamp']!=DAY for j in range(i-n,i)):return None
    return sum(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-rows[j-1]['close']),abs(rows[j]['low']-rows[j-1]['close'])) for j in range(i-n,i))/n
def backtest(rows,start,end,c=Config(),initial=10000.):
    validate(rows);equity=initial;trades=[];curve=[dict(timestamp=start,equity=initial)];i=0
    while i<len(rows):
        b=rows[i];s=b.get('dex_signal');a=atr(rows,i,c.atr_n)
        if not s or not(start<=b['timestamp']<end) or a is None or entry_day(s['observation_timestamp'])!=b['timestamp']:i+=1;continue
        raw=b['open'];entry=raw*(1+c.slippage);stop=entry-c.stop_atr*a
        if stop<=0:i+=1;continue
        qty=min(equity*c.risk_fraction/(entry-stop),equity*c.notional_cap/entry);target=entry+c.reward_r*(entry-stop);entry_fee=qty*entry*c.fee;before=equity;j=i
        while j<len(rows) and rows[j]['timestamp']<end:
            x=rows[j]
            if j>i and x['timestamp']-rows[j-1]['timestamp']!=DAY:raw_exit,reason,ei,et=rows[j-1]['close'],'DATA_GAP',j-1,rows[j-1]['timestamp']
            elif x['open']<=stop:raw_exit,reason,ei,et=x['open'],'GAP_STOP',j,x['timestamp']
            elif x['low']<=stop:raw_exit,reason,ei,et=stop,'STOP',j,x['timestamp']
            elif x['open']>=target or x['high']>=target:raw_exit,reason,ei,et=target,'TARGET',j,x['timestamp']
            elif j-i+1>=c.max_hold:raw_exit,reason,ei,et=x['close'],'TIME',j,x['timestamp']
            else:
                mark=x['low']*(1-c.slippage);curve.append(dict(timestamp=x['timestamp'],equity=before+qty*(mark-entry)-entry_fee-qty*mark*c.fee));j+=1;continue
            fill=raw_exit*(1-c.slippage);exit_fee=qty*fill*c.fee;gross=qty*(raw_exit-raw);fill_pnl=qty*(fill-entry);fees=entry_fee+exit_fee;pnl=fill_pnl-fees;equity+=pnl
            trades.append(dict(**s,entry_timestamp=b['timestamp'],exit_timestamp=et,entry_index=i,exit_index=ei,entry_equity=before,raw_entry=raw,raw_exit=raw_exit,entry=entry,exit=fill,qty=qty,atr=a,stop=stop,target=target,leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill_pnl,fees=fees,pnl=pnl,equity=equity,reason=reason,cost_fee=c.fee,cost_slippage=c.slippage));curve.append(dict(timestamp=et,equity=equity));i=ei+1;break
        else:i+=1
    return trades,curve
