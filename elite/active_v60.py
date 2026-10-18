"""Hourly V57 without its 42-bar slow-trend entry gate; exits unchanged."""
from dataclasses import replace
from statistics import mean
from elite.research_engine import aggregate
from elite.adaptive_v56 import adaptive_average
from elite.faster_v57 import decisions as baseline


def entry(close,average,k):
    return close[k-1]<=average[k-1] and close[k]>average[k] and average[k]>average[k-6]


def decisions(rows):
    original=baseline(rows,'v57')
    bars=aggregate(rows,12);close=[b[4] for b in bars];average=adaptive_average(close)
    out={}
    for k in range(48,len(bars)):
        atr=mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
                     abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))
        out[bars[k][0]]=replace(original[bars[k][0]],stop_distance=3*atr if entry(close,average,k) else 0)
    return out


def prepare(rows,btc=None):
    return {'v60':decisions(rows),'v57_control':baseline(rows,'v57')}


def activity_failures(periods,days):
    return ['below_three_trades_per_week_'+p for p in periods if periods[p]['base']['trades']*7<3*days[p]]
