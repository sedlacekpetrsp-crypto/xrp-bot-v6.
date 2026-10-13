"""Isolated spot-only research engine; no network, credentials or order API."""
from dataclasses import dataclass, asdict
from math import isfinite
from statistics import mean

@dataclass(frozen=True)
class Decision:
    stop_distance: float = 0.0
    target_distance: float = 0.0
    exit: bool = False
    max_bars: int = 0


def validate(rows):
    if not rows:
        raise ValueError('empty data')
    for i, (t,o,h,l,c) in enumerate(rows):
        if not all(isfinite(x) for x in (o,h,l,c)) or not 0 < l <= min(o,c) <= max(o,c) <= h:
            raise ValueError('invalid OHLC')
        if t % 300000 or (i and t-rows[i-1][0] != 300000):
            raise ValueError('invalid cadence')


def aggregate(rows, count):
    """Only complete UTC-aligned groups; retain index of last closed 5m bar."""
    result=[]
    for i in range(len(rows)):
        if rows[i][0] % (count*300000):
            continue
        chunk=rows[i:i+count]
        if len(chunk)!=count:
            continue
        result.append((i+count-1,chunk[0][1],max(r[2] for r in chunk),
                       min(r[3] for r in chunk),chunk[-1][4]))
    return result


def decisions(rows, candidate):
    if candidate=='v4':
        from elite.v4_candidate import slow_trend
        out={}
        for i in range(100,len(rows)):
            hist=rows[i-100:i+1]
            s=slow_trend([r[2] for r in hist],[r[3] for r in hist],[r[4] for r in hist])
            if s:
                out[i]=Decision(s.stop_distance,s.target_distance,max_bars=24)
        return out
    if candidate not in ('v5','v6','v7'):
        raise ValueError('unknown candidate')
    bars=aggregate(rows,48 if candidate=='v6' else 12)
    close=[b[4] for b in bars]
    out={}
    for k in range(200,len(bars)):
        tr=[max(bars[j][2]-bars[j][3],abs(bars[j][2]-close[j-1]),
                abs(bars[j][3]-close[j-1])) for j in range(k-13,k+1)]
        atr=mean(tr)
        if atr<=0: continue
        if candidate=='v5':
            buy=close[k]>max(b[2] for b in bars[k-72:k])
            sell=close[k]<min(b[3] for b in bars[k-24:k])
            d=Decision(3*atr if buy else 0,exit=sell)
        elif candidate=='v6':
            fast=mean(close[k-19:k+1]); slow=mean(close[k-59:k+1])
            prevfast=mean(close[k-20:k]); prevslow=mean(close[k-60:k])
            buy=fast>slow and prevfast<=prevslow
            d=Decision(3*atr if buy else 0,exit=fast<=slow)
        else:
            changes=[close[j]-close[j-1] for j in (k-1,k)]
            gains=sum(max(x,0) for x in changes); losses=-sum(min(x,0) for x in changes)
            rsi=100*gains/(gains+losses) if gains+losses else 50
            buy=rsi<10 and close[k]>mean(close[k-199:k+1])
            d=Decision(2*atr if buy else 0,exit=rsi>60,max_bars=288)
        out[bars[k][0]]=d
    return out


def simulate(rows, signals, start=0, end=None, fee=.001, slip=.0003, half_spread=.0001):
    """Boundary reset; prior-bar signal may enter at split's first open.

    Intrabar DD is an intentionally pessimistic high-before-low bound on bars
    that remain open, not a reconstruction of the unknown tick path.
    """
    end=len(rows) if end is None else end
    if not 0<=start<end<=len(rows) or not all(isfinite(x) and 0<=x<.1 for x in (fee,slip,half_spread)):
        raise ValueError('bad settings')
    adverse=slip+half_spread
    cash=10000.; pos=None; ledger=[]; daily={}
    peak=10000.; dd=0.; bound_peak=10000.; bound_dd=0.; costs=0.
    def liq(price):
        return cash if pos is None else cash+pos['qty']*price*(1-adverse)*(1-fee)
    for i in range(start,end):
        ts,o,h,l,c=rows[i]
        signal=signals.get(i-1,Decision())
        just_exited=False
        # Existing orders and gap stops take precedence over new signals.
        if pos:
            px=None; reason=None
            if o<=pos['stop']: px=o; reason='STOP_GAP'
            elif pos['target'] and o>=pos['target']: px=pos['target']; reason='TARGET_GAP'
            elif signal.exit: px=o; reason='SIGNAL'
            elif pos['expiry'] and i>=pos['expiry']: px=o; reason='TIME'
            if px is not None:
                fill=px*(1-adverse); proceeds=pos['qty']*fill*(1-fee)
                costs+=pos['qty']*(px-fill+fill*fee)
                cash+=proceeds
                ledger.append(dict(entry_index=pos['index'],exit_index=i,entry_timestamp=rows[pos['index']][0],exit_timestamp=ts,
                                   pnl=cash-pos['before'],reason=reason))
                pos=None; just_exited=True
        if pos is None and not just_exited and signal.stop_distance>0:
            entry=o*(1+adverse); stop=entry-signal.stop_distance
            if stop>0:
                # Planned loss includes both fees and adverse exit fill.
                loss_per_unit=entry*(1+fee)-stop*(1-adverse)*(1-fee)
                qty=min(cash*.005/loss_per_unit,cash*.35/(entry*(1+fee)))
                before=cash; cash-=qty*entry*(1+fee)
                costs+=qty*(entry-o+entry*fee)
                pos=dict(qty=qty,stop=stop,target=entry+signal.target_distance if signal.target_distance else 0,
                         before=before,index=i,expiry=i+signal.max_bars if signal.max_bars else 0)
        if pos:
            px=None; reason=None
            if l<=pos['stop']: px=min(o,pos['stop']); reason='STOP'
            elif pos['target'] and h>=pos['target']: px=pos['target']; reason='TARGET'
            if px is not None:
                # Include possible favourable excursion before execution; bound only.
                bound_peak=max(bound_peak,liq(h))
                fill=px*(1-adverse); costs+=pos['qty']*(px-fill+fill*fee)
                cash+=pos['qty']*fill*(1-fee)
                ledger.append(dict(entry_index=pos['index'],exit_index=i,entry_timestamp=rows[pos['index']][0],exit_timestamp=ts,
                                   pnl=cash-pos['before'],reason=reason))
                pos=None
                bound_dd=max(bound_dd,(bound_peak-cash)/bound_peak)
            else:
                bound_peak=max(bound_peak,liq(h))
                bound_dd=max(bound_dd,(bound_peak-liq(l))/bound_peak)
        if i==end-1 and pos:
            fill=c*(1-adverse); costs+=pos['qty']*(c-fill+fill*fee)
            cash+=pos['qty']*fill*(1-fee)
            ledger.append(dict(entry_index=pos['index'],exit_index=i,entry_timestamp=rows[pos['index']][0],exit_timestamp=ts,
                               pnl=cash-pos['before'],reason='BOUNDARY'))
            pos=None
        equity=liq(c)
        peak=max(peak,equity); dd=max(dd,(peak-equity)/peak)
        bound_peak=max(bound_peak,equity); bound_dd=max(bound_dd,(bound_peak-equity)/bound_peak)
        daily[ts//86400000]=equity
    gp=sum(max(t['pnl'],0) for t in ledger); gl=-sum(min(t['pnl'],0) for t in ledger)
    return dict(net_pnl=cash-10000,return_pct=(cash/10000-1)*100,trades=len(ledger),
                profit_factor=gp/gl if gl else None,close_mtm_drawdown_pct=dd*100,
                intrabar_drawdown_bound_pct=bound_dd*100,costs=costs,trade_log=ledger,daily_equity=daily)
