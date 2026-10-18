"""V48: freeze trend qualification before pullback; no account feedback."""
from statistics import mean
from elite.research_engine import aggregate, Decision, validate
from elite.candidates_v8 import efficiency

class Setup:
    def __init__(self):
        self.born=None
        self.pulled=False
        self.counts=dict(armed=0,pullbacks=0,confirmed=0,entries=0,expired=0,invalidated=0)

    def step(self,k,close,mid,atr,er,trend):
        buy=False
        if self.born is not None:
            if not trend or k-self.born>48:
                self.counts['invalidated' if not trend else 'expired']+=1
                self.born=None;self.pulled=False
            elif self.pulled and close>mid:
                self.counts['confirmed']+=1
                buy=atr>0 and 6*atr/close>=.02
                if buy:self.counts['entries']+=1
                self.born=None;self.pulled=False
                # Confirmation consumes setup even if cost hurdle fails.
                return Decision(3*atr if buy else 0,6*atr,exit=not trend,max_bars=7*288)
            elif not self.pulled and close<=mid:
                self.pulled=True;self.counts['pullbacks']+=1
        if self.born is None and trend and er>=.35 and close>mid:
            self.born=k;self.pulled=False;self.counts['armed']+=1
        return Decision(exit=not trend,max_bars=7*288)


def prepare(rows):
    validate(rows);bars=aggregate(rows,12);out={};setup=Setup()
    for k in range(200,len(bars)):
        c=[b[4] for b in bars[k-200:k+1]]
        atr=mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
                     abs(bars[j][3]-bars[j-1][4])) for j in range(k-14,k))
        trend=c[-1]>mean(c[-168:])>mean(c[-192:-24])
        out[bars[k][0]]=setup.step(k,c[-1],mean(c[-24:]),atr,efficiency(c[-50:-1]),trend)
    return out,setup.counts


def decisions(rows,name='v48'):
    if name!='v48':raise ValueError('unknown staged candidate')
    return prepare(rows)[0]
