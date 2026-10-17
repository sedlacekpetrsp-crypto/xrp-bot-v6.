"""V57 with one-ATR buffer on both trend-exit closes; initial stop unchanged."""
from dataclasses import replace
from statistics import mean
from elite.research_engine import aggregate
from elite.adaptive_v56 import adaptive_average
from elite.faster_v57 import decisions as baseline


def exit_condition(close,average,atr,k):
    return close[k]<average[k]-atr[k] and close[k-1]<average[k-1]-atr[k-1]


def decisions(rows):
    original=baseline(rows,'v57')
    bars=aggregate(rows,12);close=[b[4] for b in bars]
    average=adaptive_average(close);atr=[None]*len(bars)
    for k in range(14,len(bars)):
        atr[k]=mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
                        abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))
    return {bars[k][0]:replace(original[bars[k][0]],exit=exit_condition(close,average,atr,k))
            for k in range(48,len(bars))}


def prepare(rows,btc=None):
    return {'v59':decisions(rows),'v57_control':baseline(rows,'v57')}
