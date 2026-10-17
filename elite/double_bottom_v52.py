"""Confirmed hourly double bottom; pivots become known two hours later."""
from statistics import mean
from elite.research_engine import aggregate, validate, Decision
from elite.cross_market_v18 import decisions as control


def hourly_signals(bars):
    out = {}; previous_pivot = None; setup = None
    for k in range(16, len(bars)):
        atr = mean(max(bars[j][2]-bars[j][3], abs(bars[j][2]-bars[j-1][4]),
                       abs(bars[j][3]-bars[j-1][4])) for j in range(k-13, k+1))
        p = k-2
        if all(bars[p][3] < bars[j][3] for j in (p-2, p-1, p+1, p+2)):
            # A newly confirmed pivot replaces any older untriggered pattern.
            setup = None
            if previous_pivot is not None:
                a = previous_pivot
                if 6 <= p-a <= 48 and abs(bars[p][3]-bars[a][3]) <= .5*atr:
                    floor = min(bars[p][3], bars[a][3])
                    neck = max(bars[j][2] for j in range(a+1, p))
                    if neck-floor >= atr:
                        setup = (floor-.5*atr, neck, k+24)
            previous_pivot = p
        d = Decision()
        if setup is not None:
            stop, neck, expiry = setup
            if k > expiry or bars[k][3] <= stop:
                setup = None
            elif bars[k-1][4] <= neck < bars[k][4]:
                risk = bars[k][4]-stop
                if risk > 0 and 2*risk >= .02*bars[k][4]:
                    d = Decision(risk, 2*risk, max_bars=864)
                # One attempt, including rejected target-size cases.
                setup = None
        out[bars[k][0]] = d
    return out


def decisions(rows):
    validate(rows)
    return hourly_signals(aggregate(rows, 12))


def prepare(rows, btc):
    return {'v52': decisions(rows), 'v18_control': control(rows, btc, 'v18')}
