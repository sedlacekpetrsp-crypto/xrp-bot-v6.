"""Fixed cross-asset relative-strength hypothesis; offline spot-only simulator."""
from math import isfinite
from research.autocorr_regime_v1 import Config
STEP=3600000

def validate(markets):
    reference=None
    for symbol in ('XRPUSDT','BTCUSDT','ETHUSDT'):
        bars=markets[symbol];times=[]
        for b in bars:
            o,h,l,c=(b[k] for k in ('open','high','low','close'))
            if not all(isfinite(v) for v in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h:raise ValueError('Invalid OHLC')
            times.append(b['timestamp'])
        if any(t%STEP for t in times) or any(b<=a or (b-a)%STEP for a,b in zip(times,times[1:])):raise ValueError('Invalid timestamp/duplicate')
        if reference is not None and times!=reference:raise ValueError('Market alignment')
        reference=times

def state(markets,i):
    if i<720:return None
    x=markets["XRPUSDT"]
    if x[i]["timestamp"]-x[i-720]["timestamp"]!=720*STEP:return None
    growth={s:b[i]['close']/b[i-168]['close'] for s,b in markets.items()}
    btc=markets['BTCUSDT'];x=markets['XRPUSDT']
    a=growth['XRPUSDT']/growth['BTCUSDT'];b=growth['XRPUSDT']/growth['ETHUSDT']
    regime=btc[i]['close']/btc[i-720]['close']>1
    enter=a>1.02 and b>1.02 and growth['XRPUSDT']>1 and regime
    leave=a<=1 or b<=1 or not regime
    atr=sum(max(x[j]['high']-x[j]['low'],abs(x[j]['high']-x[j-1]['close']),abs(x[j]['low']-x[j-1]['close'])) for j in range(i-23,i+1))/24
    return enter,leave,atr

def backtest(markets,start,end,c=Config(),initial=10000.):
    validate(markets);bars=markets['XRPUSDT'];equity=initial;trades=[];position=None
    for i,b in enumerate(bars):
        if b['timestamp']<start:continue
        if b['timestamp']>=end:break
        midnight=(b['timestamp']//STEP)%24==0
        s=state(markets,i-1) if midnight else None
        if position is None and s and s[0] and s[2]>0:
            entry=b['open']*(1+c.slippage);stop=entry-2*s[2]
            if stop>0:
                qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry)
                position=dict(signal_index=i-1,entry_index=i,entry=entry,stop=stop,qty=qty)
        if position is None:continue
        p=position;raw=None;reason=None
        if b['open']<=p['stop']:raw=b['open'];reason='GAP_STOP'
        elif i>p['entry_index'] and ((s and s[1]) or b['timestamp']-bars[p['entry_index']]['timestamp']>=168*STEP):
            raw=b['open'];reason='REGIME_EXIT' if s and s[1] else 'TIME'
        elif b['low']<=p['stop']:raw=p['stop'];reason='STOP'
        elif i==len(bars)-1 or bars[i+1]['timestamp']>=end:raw=b['close'];reason='END'
        if raw is not None:
            fill=raw*(1-c.slippage);fees=c.fee*p['qty']*(p['entry']+fill)
            gross=p['qty']*(raw-p['entry']/(1+c.slippage))
            pnl=p['qty']*(fill-p['entry'])-fees;equity+=pnl
            trades.append(dict(p,exit_index=i,exit=fill,pnl=pnl,equity=equity,fees=fees,gross=gross,slippage_cost=gross-fees-pnl,reason=reason))
            position=None
    return trades
