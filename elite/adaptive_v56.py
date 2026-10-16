"""Four-hour adaptive-average reclaim, fixed efficiency-based smoothing."""
from math import isfinite
from statistics import mean
from elite.research_engine import aggregate,validate,Decision
from elite.cross_market_v18 import decisions as control


def adaptive_average(close):
    if any(not isfinite(c) or c<=0 for c in close):raise ValueError('invalid close')
    out=[None]*len(close)
    if len(close)<10:return out
    out[9]=mean(close[:10])
    for k in range(10,len(close)):
        path=sum(abs(close[j]-close[j-1]) for j in range(k-9,k+1))
        efficiency=abs(close[k]-close[k-10])/path if path else 0
        smoothing=(efficiency*(2/3-2/31)+2/31)**2
        out[k]=out[k-1]+smoothing*(close[k]-out[k-1])
    return out


def signals(bars):
    close=[b[4] for b in bars];average=adaptive_average(close);out={}
    for k in range(48,len(bars)):
        weekly=mean(close[k-41:k+1]);previous_weekly=mean(close[k-47:k-5])
        buy=(close[k-1]<=average[k-1] and close[k]>average[k] and
             average[k]>average[k-6] and weekly>previous_weekly and close[k]>weekly)
        atr=mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
                     abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))
        sell=close[k]<average[k] and close[k-1]<average[k-1]
        out[bars[k][0]]=Decision(3*atr if buy else 0,exit=sell,max_bars=4032)
    return out


def decisions(rows):
    validate(rows)
    return signals(aggregate(rows,48))


def prepare(rows,btc):
    return {'v56':decisions(rows),'v18_control':control(rows,btc,'v18')}
