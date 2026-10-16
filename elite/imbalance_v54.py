"""Hourly trigger from rolling daily taker imbalance, independent of V18."""
from statistics import mean
from elite.research_engine import aggregate, validate, Decision
from elite.flow_v28 import align_flow
from elite.cross_market_v18 import decisions as control


def hourly_signals(bars, totals):
    if len(bars) != len(totals):
        raise ValueError('hourly volume length mismatch')
    out = {}; previous = None
    for k in range(24, len(bars)):
        volume = sum(v for v, buy in totals[k-23:k+1])
        buys = sum(buy for v, buy in totals[k-23:k+1])
        imbalance = (2*buys-volume)/volume if volume > 0 else None
        atr = mean(max(bars[j][2]-bars[j][3], abs(bars[j][2]-bars[j-1][4]),
                       abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))
        change = bars[k][4]/bars[k-24][4]-1
        buy = (imbalance is not None and previous is not None and
               previous <= .05 < imbalance and 0 <= change <= .02 and
               4*atr >= .02*bars[k][4])
        out[bars[k][0]] = Decision(2*atr if buy else 0, 4*atr,
                                  exit=imbalance is not None and imbalance < 0,
                                  max_bars=576)
        previous = imbalance
    return out


def decisions(rows, flow):
    validate(rows); align_flow(rows, flow)
    bars = aggregate(rows,12)
    totals = [(sum(v for ts,v,buy in flow[b[0]-11:b[0]+1]),
               sum(buy for ts,v,buy in flow[b[0]-11:b[0]+1])) for b in bars]
    return hourly_signals(bars,totals)


def prepare(rows, btc, flow):
    return {'v54': decisions(rows,flow), 'v18_control': control(rows,btc,'v18')}
