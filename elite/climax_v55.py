"""Event-anchored volume-weighted recovery after a completed selloff bar."""
from statistics import mean
from elite.research_engine import aggregate, validate, Decision
from elite.flow_v28 import align_flow
from elite.cross_market_v18 import decisions as control


def signals(bars, totals):
    if len(bars) != len(totals): raise ValueError('volume length mismatch')
    out = {}; anchor = None
    for k in range(20,len(bars)):
        _,o,h,l,c = bars[k]
        atr = mean(max(bars[j][2]-bars[j][3], abs(bars[j][2]-bars[j-1][4]),
                       abs(bars[j][3]-bars[j-1][4])) for j in range(k-14,k))
        volume, pv = totals[k]
        avg_volume = mean(v for v,p in totals[k-20:k])
        climax = c < o and h-l >= 2*atr and avg_volume > 0 and volume >= 2*avg_volume
        d = Decision()
        if climax:
            # The newly completed selloff supersedes any pending older setup.
            anchor = (k, l-.5*atr, volume, pv)
        elif anchor is not None:
            start, stop, total_v, total_pv = anchor
            if k-start > 6 or l <= stop:
                anchor = None
            else:
                prev_vwap = total_pv/total_v
                total_v += volume; total_pv += pv
                vwap = total_pv/total_v
                if bars[k-1][4] <= prev_vwap and c > vwap:
                    risk = c-stop
                    if risk > 0 and 2*risk >= .02*c:
                        d = Decision(risk,2*risk,max_bars=2016)
                    anchor = None
                else:
                    anchor = (start,stop,total_v,total_pv)
        out[bars[k][0]] = d
    return out


def decisions(rows,flow):
    validate(rows);align_flow(rows,flow)
    bars = aggregate(rows,48); totals=[]
    for b in bars:
        lo,hi=b[0]-47,b[0]+1
        volume=sum(v for ts,v,buy in flow[lo:hi])
        pv=sum((r[2]+r[3]+r[4])/3*f[1] for r,f in zip(rows[lo:hi],flow[lo:hi]))
        totals.append((volume,pv))
    return signals(bars,totals)


def prepare(rows,btc,flow):
    return {'v55':decisions(rows,flow),'v18_control':control(rows,btc,'v18')}
