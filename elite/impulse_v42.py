"""Event-driven hourly impulse, stabilization and confirmation hypotheses."""
from statistics import mean
from elite.research_engine import Decision, aggregate, validate


def signals(bars, name):
    if name not in ('v42', 'v43'):
        raise ValueError('unknown impulse candidate')
    out = {}; pending = None
    for k in range(60, len(bars)):
        _, o, h, l, c = bars[k]
        a = mean(max(bars[j][2]-bars[j][3], abs(bars[j][2]-bars[j-1][4]),
                     abs(bars[j][3]-bars[j-1][4])) for j in range(k-14, k))
        buy = False; distance = 0.
        if pending is not None:
            born, high, low, frozen_atr = pending
            if k-born > 12 or l < low:
                pending = None
            elif k-born >= 4:
                quiet = bars[k-3:k]
                stable = (min(b[3] for b in quiet) >= low and
                          max(b[2] for b in quiet)-min(b[3] for b in quiet) <= (high-low)/2)
                confirmation = c > max(b[2] for b in quiet)
                if name == 'v42':
                    held = min(b[3] for b in quiet) >= (high+low)/2
                else:
                    held = c > (high+low)/2
                buy = stable and confirmation and held
                if buy:
                    distance = max(c-min(b[3] for b in quiet), 1.5*frozen_atr)
                    pending = None
        # One active event. New event can only be acted on in a later hour.
        if pending is None and not buy and a > 0:
            span = h-l
            up = c-o >= 2*a and span > 0 and c >= l+.8*span
            down = o-c >= 2*a and span > 0 and c <= l+.2*span
            if (name == 'v42' and up) or (name == 'v43' and down):
                pending = (k, h, l, a)
        out[bars[k][0]] = Decision(distance if buy else 0, 2*distance, max_bars=72*12)
    return out


def decisions(rows, name):
    validate(rows)
    return signals(aggregate(rows, 12), name)
