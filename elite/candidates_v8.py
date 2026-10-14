"""Frozen V8–V11 research hypotheses. Only completed aggregate bars."""
from math import log
from statistics import mean, pstdev
from elite.research_engine import aggregate, Decision


def efficiency(close):
    distance=sum(abs(b-a) for a,b in zip(close,close[1:]))
    return abs(close[-1]-close[0])/distance if distance else 0.


def candidate_decision(bars,k,name):
    c=[b[4] for b in bars[max(0,k-240):k+1]]
    if len(c)<201: return Decision()
    tr=[max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
            abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1)]
    atr=mean(tr)
    if atr<=0:return Decision()
    if name=='v8':
        # Shock is c[-2]; baseline returns end at c[-3].
        baseline=[log(c[j]/c[j-1]) for j in range(len(c)-32,len(c)-2)]
        sigma=pstdev(baseline)
        shock=log(c[-2]/c[-3])
        midpoint=(bars[k-1][2]+bars[k-1][3])/2
        buy=sigma>0 and shock < -2.5*sigma and c[-1]>c[-2] and c[-1]>midpoint
        return Decision(2*atr if buy else 0,4*atr,max_bars=576)
    if name=='v9':
        baseline=c[-49:-1]; mid=mean(baseline); std=pstdev(baseline)
        buy=std>0 and c[-1]<mid-2.5*std and efficiency(c[-49:])<.25 and c[-1]>c[-2]
        return Decision(2*atr if buy else 0,3*atr,exit=c[-1]>=mid,max_bars=288)
    if name=='v10':
        slow=mean(c[-120:]); oldslow=mean(c[-126:-6]); fast=mean(c[-20:]); oldfast=mean(c[-21:-1])
        buy=c[-1]>slow and slow>oldslow and bars[k-1][3]<=oldfast and c[-2]<=oldfast and c[-1]>fast
        return Decision(3*atr if buy else 0,exit=c[-1]<mean(c[-60:]),max_bars=2016)
    if name=='v11':
        slow=mean(c[-168:]); oldslow=mean(c[-192:-24])
        buy=(c[-1]>max(b[2] for b in bars[k-72:k]) and efficiency(c[-73:])>.35
             and c[-1]>slow and slow>oldslow)
        return Decision(4*atr if buy else 0,exit=c[-1]<min(b[3] for b in bars[k-24:k]))
    raise ValueError('unknown candidate')


def decisions(rows,name):
    if name not in ('v8','v9','v10','v11'):raise ValueError('unknown candidate')
    bars=aggregate(rows,48 if name in ('v8','v10') else 12)
    return {bars[k][0]:candidate_decision(bars,k,name) for k in range(200,len(bars))}
