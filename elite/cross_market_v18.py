"""Causal BTC-conditioned XRP signals. Both markets must be aligned and closed."""
from statistics import mean
from elite.research_engine import aggregate,validate,Decision,decisions as xrp_decisions


def align(xrp,btc):
    validate(xrp);validate(btc)
    if len(xrp)!=len(btc) or any(a[0]!=b[0] for a,b in zip(xrp,btc)):
        raise ValueError('XRP/BTC timestamps do not exactly match')


def signal(x,b,k,name,original=None):
    if name not in ('v18','v19','v20'):raise ValueError('unknown candidate')
    if k<200:return Decision()
    xc=[r[4] for r in x[k-200:k+1]];bc=[r[4] for r in b[k-200:k+1]]
    bslow=mean(bc[-168:])
    if name=='v18':
        if original is None:raise ValueError('V18 requires original V5 signal')
        allowed=bc[-1]>bslow and bslow>mean(bc[-192:-24])
        return Decision(original.stop_distance if allowed else 0,original.target_distance,
                        original.exit,original.max_bars)
    atr=mean(max(x[j][2]-x[j][3],abs(x[j][2]-x[j-1][4]),abs(x[j][3]-x[j-1][4])) for j in range(k-13,k+1))
    if atr<=0:return Decision()
    xr=xc[-1]/xc[-25]-1;br=bc[-1]/bc[-25]-1
    if name=='v19':
        buy=(xr-br>.01 and br>0 and xc[-1]>mean(xc[-168:]) and xc[-2]<=mean(xc[-25:-1]) and xc[-1]>mean(xc[-24:]))
        return Decision(3*atr if buy else 0,exit=xc[-1]<mean(xc[-72:]),max_bars=2016)
    buy=(br>=.02 and xr<=0 and bc[-1]>bslow and xc[-2]<=mean(xc[-7:-1]) and xc[-1]>mean(xc[-6:]))
    return Decision(3*atr if buy else 0,6*atr,max_bars=576)


def decisions(xrp,btc,name):
    align(xrp,btc)
    x=aggregate(xrp,12);b=aggregate(btc,12)
    original=xrp_decisions(xrp,'v5') if name=='v18' else {}
    return {x[k][0]:signal(x,b,k,name,original.get(x[k][0])) for k in range(200,len(x))}
