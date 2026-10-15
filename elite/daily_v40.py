"""Fixed daily hypotheses, signals only on fully closed UTC days."""
from statistics import mean
from elite.research_engine import Decision, aggregate, validate


def signal(bars, k, name):
    if name not in ('v40', 'v41'):
        raise ValueError('unknown daily candidate')
    if k < 60:
        return Decision()
    c = bars[k][4]
    atr = mean(max(bars[j][2]-bars[j][3], abs(bars[j][2]-bars[j-1][4]),
                   abs(bars[j][3]-bars[j-1][4])) for j in range(k-19, k+1))
    if name == 'v40':
        buy = c > max(b[2] for b in bars[k-20:k])
        sell = c < min(b[3] for b in bars[k-10:k])
        return Decision(2*atr if buy else 0, exit=sell)
    # Pullback recovery in a rising 50-day trend, distinct entry from breakout.
    slow = mean(b[4] for b in bars[k-49:k+1])
    prior = mean(b[4] for b in bars[k-59:k-9])
    buy = (c > slow > prior and bars[k-3][4] > bars[k-2][4] > bars[k-1][4]
           and c > bars[k-1][2])
    return Decision(2*atr if buy else 0, 4*atr, exit=c < slow, max_bars=20*288)


def decisions(rows, name):
    validate(rows)
    bars = aggregate(rows, 288)
    return {bars[k][0]: signal(bars, k, name) for k in range(60, len(bars))}
