"""Frozen V12–V14 hypotheses, with explicit links to prior strategy families."""
from statistics import mean
from elite.research_engine import aggregate,Decision
from elite.candidates_v8 import candidate_decision as prior_decision


def simple_rsi(closes):
    changes=[b-a for a,b in zip(closes,closes[1:])]
    gains=sum(max(x,0) for x in changes);losses=-sum(min(x,0) for x in changes)
    return 100*gains/(gains+losses) if gains+losses else 50.


def candidate_decision(bars,k,name):
    if name not in ('v12','v13','v14'):raise ValueError('unknown candidate')
    if k<200:return Decision()
    if name=='v12':
        s=prior_decision(bars,k,'v8')
        return Decision(s.stop_distance,s.target_distance,max_bars=144)
    close=[b[4] for b in bars[k-20:k+1]]
    atr=mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))
    if atr<=0:return Decision()
    if name=='v13':
        now=simple_rsi(close[-15:]);previous=simple_rsi(close[-16:-1])
        buy=previous<=30<now and close[-1]>close[-2]
        return Decision(3*atr if buy else 0,6*atr,max_bars=2016)
    ranges=[b[2]-b[3] for b in bars[k-24:k]]
    current=bars[k];prev=bars[k-1];width=current[2]-current[3]
    buy=(width>0 and ranges[-1]<=min(ranges) and current[4]>prev[2] and current[4]>current[1]
         and current[4]>=current[3]+.8*width)
    return Decision(2*atr if buy else 0,6*atr,max_bars=576)


def decisions(rows,name):
    if name not in ('v12','v13','v14'):raise ValueError('unknown candidate')
    bars=aggregate(rows,48 if name=='v13' else 12)
    return {bars[k][0]:candidate_decision(bars,k,name) for k in range(200,len(bars))}
