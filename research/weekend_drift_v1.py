"""WEEKEND_DRIFT_V1: calendar-only spot exposure, isolated offline research.
Frozen hypothesis: positive Saturday/Sunday return premium, independent of
indicators, breakout, autocorrelation or order flow. Saturday 00:00 UTC entry,
Monday 00:00 UTC exit. 2.5% protective stop, 20% sleeve cap, 0.5% risk.
Use same fixed costs and chronological periods as autocorr; no parameter search.
"""
from datetime import datetime, timezone
from research.autocorr_regime_v1 import Config,validate

def backtest(bars,c=Config(),initial_equity=10000.):
    validate(bars);equity=initial_equity;trades=[];i=0
    while i<len(bars)-1:
        dt=datetime.fromtimestamp(bars[i]['timestamp']/1000,timezone.utc)
        if (dt.weekday(),dt.hour,dt.minute)!=(5,0,0):i+=1;continue
        entry_i=i;entry=bars[i]['open']*(1+c.slippage);stop=entry*.975
        qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry)
        end=min(i+192,len(bars)-1);raw=bars[end]['close'];reason='END'
        for j in range(i,end+1):
            b=bars[j]
            if b['open']<=stop:end,raw,reason=j,b['open'],'GAP_STOP';break
            if j==i+192:end,raw,reason=j,b['open'],'CALENDAR_EXIT';break
            if b['low']<=stop:end,raw,reason=j,stop,'STOP';break
        fill=raw*(1-c.slippage);pnl=qty*(fill-entry)-c.fee*qty*(entry+fill);equity+=pnl
        trades.append(dict(signal_index=None,entry_index=i,exit_index=end,regime='WEEKEND',qty=qty,entry=entry,exit=fill,pnl=pnl,equity=equity,reason=reason))
        i=end+1
    return trades
if __name__=='__main__':
    from research.run_autocorr_history import main
    main(backtest,'WEEKEND_DRIFT_V1',0)
