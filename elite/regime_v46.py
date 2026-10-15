"""Incremental regime/reclaim hypotheses, explicitly related to V9/V10/V11."""
from statistics import mean
from elite.research_engine import aggregate, Decision, validate
from elite.candidates_v8 import efficiency


def rule(name, previous, close, low, mid, prior_mid, atr, er, trend):
    if name not in ('v46','v47'):
        raise ValueError('unknown regime candidate')
    if name == 'v46':
        buy = trend and er >= .35 and previous <= prior_mid and close > mid
        stop = 3*atr; target = 6*atr
        sell = not trend
        expiry = 7*288
    else:
        # A completed candle sweeps below the fixed PRIOR hourly band and reclaims it.
        band = prior_mid-2*atr
        buy = er <= .2 and low < band < close < prior_mid
        stop = 2*atr; target = 4*atr
        sell = close >= mid
        expiry = 2*288
    allowed = atr > 0 and target/close >= .02
    return Decision(stop if buy and allowed else 0, target, exit=sell, max_bars=expiry)


def decisions(rows, name):
    if name not in ('v46','v47'):
        raise ValueError('unknown regime candidate')
    validate(rows);bars=aggregate(rows,12);out={}
    for k in range(200,len(bars)):
        c=[b[4] for b in bars[k-200:k+1]]
        # ATR and efficiency use only history before the signal candle.
        atr=mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
                     abs(bars[j][3]-bars[j-1][4])) for j in range(k-14,k))
        mid=mean(c[-24:]);prior=mean(c[-25:-1])
        slow=mean(c[-168:]);old=mean(c[-192:-24])
        trend=c[-1]>slow>old
        out[bars[k][0]]=rule(name,c[-2],c[-1],bars[k][3],mid,prior,atr,
                             efficiency(c[-50:-1]),trend)
    return out
