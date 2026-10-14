"""Frozen failed-breakdown reversal and delayed breakout-retest hypotheses."""
from statistics import mean
from elite.research_engine import aggregate,Decision


def atr(bars,k):
    return mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
                    abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))


def signals(bars,name):
    if name not in ('v24','v25'):raise ValueError('unknown candidate')
    out={};pending=None
    for k in range(200,len(bars)):
        _,o,h,l,c=bars[k];a=atr(bars,k)
        if a<=0:continue
        if name=='v24':
            floor=min(b[3] for b in bars[k-24:k])
            buy=l<floor<c and c>o and c>=l+.75*(h-l)
            d=Decision(2*a if buy else 0,4*a,max_bars=576)
        else:
            buy=False
            if pending is not None:
                born,level,old_atr=pending
                if k-born>24 or c<level-old_atr:
                    pending=None
                elif l<=level<c and c>mean(b[4] for b in bars[k-167:k+1]):
                    buy=True;pending=None
            # Retest must be on a LATER completed hour. No same-bar entry.
            if not buy and pending is None and c>max(b[2] for b in bars[k-72:k]):
                pending=(k,max(b[2] for b in bars[k-72:k]),a)
            d=Decision(3*a if buy else 0,exit=c<min(b[3] for b in bars[k-24:k]),max_bars=2016)
        out[bars[k][0]]=d
    return out


def decisions(rows,name):
    return signals(aggregate(rows,48 if name=='v24' else 12),name)
