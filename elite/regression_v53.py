"""Weekly log-price trend measured on complete four-hour bars."""
import math
from statistics import mean
from elite.research_engine import aggregate, validate, Decision
from elite.cross_market_v18 import decisions as control


def trend(prices):
    if len(prices) < 3 or any(not math.isfinite(p) or p <= 0 for p in prices):
        raise ValueError('at least three positive finite prices required')
    y = [math.log(p) for p in prices]
    n = len(y); center = (n-1)/2; average = mean(y)
    sxx = sum((i-center)**2 for i in range(n))
    slope = sum((i-center)*(v-average) for i,v in enumerate(y))/sxx
    residual = sum((v-average-slope*(i-center))**2 for i,v in enumerate(y))
    # A finite floor handles exactly flat/linear synthetic data deterministically.
    se = math.sqrt(max(residual/(n-2), 1e-24)/sxx)
    return slope, slope/se


def signals(bars):
    out = {}; qualified_before = False
    for k in range(41, len(bars)):
        slope, score = trend([b[4] for b in bars[k-41:k+1]])
        atr = mean(max(bars[j][2]-bars[j][3], abs(bars[j][2]-bars[j-1][4]),
                       abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))
        qualified = score >= 3 and slope*42 >= math.log(1.02)
        buy = qualified and not qualified_before and 6*atr >= .02*bars[k][4]
        out[bars[k][0]] = Decision(3*atr if buy else 0, 6*atr,
                                  exit=score <= 0, max_bars=2016)
        qualified_before = qualified
    return out


def decisions(rows):
    validate(rows)
    return signals(aggregate(rows, 48))


def prepare(rows, btc):
    return {'v53': decisions(rows), 'v18_control': control(rows, btc, 'v18')}
