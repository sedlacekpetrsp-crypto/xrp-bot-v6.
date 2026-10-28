"""Intratrade liquidation-equity drawdown bounds from minute OHLC.

Exact high/low ordering is unknown. Lower bound uses prior peaks and the
known high-before-close ordering; upper bound permits high before low.
Fees/slippage are modeled on liquidation, including open positions.
"""
import math


def drawdown_bounds(trades, bars, fee_bps=10, slippage_bps=5):
    fee, slip = fee_bps/10000, slippage_bps/10000
    if not 0 <= fee < 1 or not 0 <= slip < 1:
        raise ValueError('Invalid costs')
    cash = peak = 1.0
    lower = upper = 0.0
    last_exit = -math.inf
    for trade in trades:
        entry, end = int(trade['entry_ts']), int(trade['exit_ts'])
        if entry % 60 or end % 60 or end <= entry or entry < last_exit:
            raise ValueError('Trades must be ordered, disjoint and minute aligned')
        required = list(range(entry, end, 60)) + [end]
        if any(t not in bars for t in required):
            raise ValueError('Missing risk candles')
        units = cash/(float(bars[entry][1])*(1+slip)*(1+fee))
        liquidation = lambda price: units*price*(1-slip)*(1-fee)
        for t in range(entry, end, 60):
            o,h,l,c = map(float,bars[t][1:5])
            if not all(math.isfinite(x) and x>0 for x in [o,h,l,c]) or not l<=min(o,c)<=max(o,c)<=h:
                raise ValueError('Invalid OHLC')
            opening, high, low, close = map(liquidation,[o,h,l,c])
            peak = max(peak,opening)
            lower = max(lower,1-low/peak)
            peak = max(peak,high)
            upper = max(upper,1-low/peak)
            lower = max(lower,1-close/peak)
            upper = max(upper,lower)
        cash = liquidation(float(bars[end][1]))
        lower = max(lower,1-cash/peak)
        upper = max(upper,lower)
        peak = max(peak,cash)
        last_exit=end
    return dict(max_drawdown_lower_bound=lower,max_drawdown_upper_bound=upper,
                final_net_return=cash-1,
                method='Minute OHLC liquidation-equity bounds; exact tick drawdown unknown')
