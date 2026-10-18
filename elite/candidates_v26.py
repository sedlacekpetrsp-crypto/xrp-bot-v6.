"""Predeclared 4h high-volume breakout and rejection signals."""
from statistics import mean,median
from elite.research_engine import aggregate,Decision,validate
from elite.volume_v26 import align_volume


def signal(bars,volumes,k,name,require_volume=True):
    if name not in ('v26','v27'):raise ValueError('unknown volume candidate')
    if k<200:return Decision()
    _,o,h,l,c=bars[k]
    atr=mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
                 abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))
    baseline=median(volumes[k-20:k])
    active=(baseline>0 and volumes[k]>=2*baseline) if require_volume else True
    if name=='v26':
        buy=active and c>max(b[2] for b in bars[k-20:k])
        return Decision(3*atr if buy else 0,exit=c<min(b[3] for b in bars[k-10:k]),max_bars=2016)
    buy=(active and h>l and min(o,c)-l>=.5*(h-l) and c>o and c>bars[k-1][4]
         and l<min(b[3] for b in bars[k-6:k]))
    return Decision(2*atr if buy else 0,4*atr,max_bars=576)


def decisions(rows,volumes,name,require_volume=True):
    validate(rows);align_volume(rows,volumes)
    bars=aggregate(rows,48)
    sums=[sum(v for _,v in volumes[b[0]-47:b[0]+1]) for b in bars]
    return {b[0]:signal(bars,sums,k,name,require_volume) for k,b in enumerate(bars) if k>=200}
