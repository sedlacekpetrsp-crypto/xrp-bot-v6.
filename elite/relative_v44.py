"""Relative XRP/BTC log-price hypotheses; not a hedged or cointegrated pair."""
from math import log
from statistics import mean, pstdev
from elite.research_engine import aggregate, Decision
from elite.cross_market_v18 import align


def relative_scores(values, k):
    history = values[k-168:k]  # Current signal hour excluded from fitting.
    mu = mean(history); sd = pstdev(history)
    if sd < 1e-12:
        return None
    return (values[k-1]-mu)/sd, (values[k]-mu)/sd


def rule(previous, current, atr, btc_allowed, name):
    if name not in ('v44', 'v45'):
        raise ValueError('unknown relative candidate')
    if name == 'v44':
        buy = previous <= -2 < current < 0
        return Decision(2.5*atr if buy and btc_allowed else 0, 5*atr,
                        exit=current >= 0 or not btc_allowed, max_bars=72*12)
    buy = previous <= 2 < current
    return Decision(2.5*atr if buy and btc_allowed else 0,
                    exit=current < .5 or not btc_allowed, max_bars=168*12)


def decisions(rows, btc, name):
    if name not in ('v44', 'v45'):
        raise ValueError('unknown relative candidate')
    align(rows, btc)
    x = aggregate(rows, 12); b = aggregate(btc, 12)
    ratios = [log(a[4]/c[4]) for a,c in zip(x,b)]
    out = {}
    for k in range(200, len(x)):
        scores = relative_scores(ratios, k)
        if scores is None:
            out[x[k][0]] = Decision(exit=True)
            continue
        atr = mean(max(x[j][2]-x[j][3], abs(x[j][2]-x[j-1][4]),
                       abs(x[j][3]-x[j-1][4])) for j in range(k-13,k+1))
        allowed = b[k][4] > mean(c[4] for c in b[k-167:k+1])
        out[x[k][0]] = rule(*scores, atr, allowed, name)
    return out
