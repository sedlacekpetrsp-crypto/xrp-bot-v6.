"""Predeclared aggregate taker-flow confirmation and absorption hypotheses."""
from statistics import mean
from elite.research_engine import aggregate,Decision,validate
from elite.flow_v28 import align_flow


def ratio(pairs):
    total=sum(v for v,b in pairs)
    return sum(b for v,b in pairs)/total if total>0 else None


def signal(bars,flows,k,name,require_flow=True):
    if name not in ('v28','v29'):raise ValueError('unknown flow candidate')
    if k<200:return Decision()
    _,o,h,l,c=bars[k]
    atr=mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
                 abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))
    if name=='v28':
        share=ratio(flows[k-2:k+1])
        active=not require_flow or (share is not None and share>.55)
        buy=active and c>max(b[2] for b in bars[k-72:k])
        return Decision(3*atr if buy else 0,exit=c<min(b[3] for b in bars[k-24:k]))
    share=ratio(flows[k:k+1])
    active=not require_flow or (share is not None and share<.5)
    buy=(active and h>l and min(o,c)-l>=.5*(h-l) and c>o and c>bars[k-1][4]
         and l<min(b[3] for b in bars[k-6:k]))
    return Decision(2*atr if buy else 0,4*atr,max_bars=576)


def decisions(rows,flows,name,require_flow=True):
    validate(rows);align_flow(rows,flows)
    count=12 if name=='v28' else 48
    bars=aggregate(rows,count)
    sums=[(sum(v for _,v,buy in flows[b[0]-count+1:b[0]+1]),
           sum(buy for _,v,buy in flows[b[0]-count+1:b[0]+1])) for b in bars]
    return {b[0]:signal(bars,sums,k,name,require_flow) for k,b in enumerate(bars) if k>=200}
