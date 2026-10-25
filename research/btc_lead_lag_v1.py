"""Frozen BTC_LEAD_LAG_IMPULSE_V1; isolated spot-only offline simulator."""
from dataclasses import dataclass
from math import isfinite

STEP = 3_600_000

@dataclass(frozen=True)
class Config:
    btc_move: float = .010
    xrp_floor: float = -.0025
    xrp_ceiling: float = .0035
    lag_gap: float = .008
    atr_window: int = 24
    stop_atr: float = 1.5
    target_r: float = 1.8
    max_hold: int = 6
    fee: float = .00095
    slippage: float = .0002
    risk: float = .005
    notional_cap: float = .20

def validate(markets):
    reference = None
    for symbol in ('BTCUSDT', 'XRPUSDT'):
        bars = markets[symbol]
        times = []
        for b in bars:
            o, h, l, c = (float(b[k]) for k in ('open', 'high', 'low', 'close'))
            if not all(isfinite(v) for v in (o, h, l, c)) or not 0 < l <= min(o, c) <= max(o, c) <= h:
                raise ValueError('invalid OHLC')
            times.append(int(b['timestamp']))
        if any(t % STEP for t in times) or any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError('invalid or duplicate timestamp')
        if reference is not None and times != reference:
            raise ValueError('market alignment')
        reference = times

def signal(markets, i, c=Config()):
    if i < c.atr_window:
        return None
    xrp, btc = markets['XRPUSDT'], markets['BTCUSDT']
    if xrp[i]['timestamp'] - xrp[i-c.atr_window]['timestamp'] != c.atr_window * STEP:
        return None
    btc_ret = btc[i]['close'] / btc[i-1]['close'] - 1
    xrp_ret = xrp[i]['close'] / xrp[i-1]['close'] - 1
    if not (btc_ret >= c.btc_move and c.xrp_floor <= xrp_ret <= c.xrp_ceiling and btc_ret-xrp_ret >= c.lag_gap):
        return None
    tr = [max(xrp[j]['high']-xrp[j]['low'], abs(xrp[j]['high']-xrp[j-1]['close']), abs(xrp[j]['low']-xrp[j-1]['close'])) for j in range(i-c.atr_window+1, i+1)]
    atr = sum(tr) / len(tr)
    return dict(atr=atr, btc_return=btc_ret, xrp_return=xrp_ret) if atr > 0 else None

def backtest(markets, start, end, c=Config(), initial=10_000.):
    validate(markets)
    bars = markets['XRPUSDT']; trades = []; equity = initial
    i = max(c.atr_window, 1)
    while i < len(bars)-1:
        if bars[i+1]['timestamp'] < start:
            i += 1; continue
        if bars[i+1]['timestamp'] >= end:
            break
        s = signal(markets, i, c)
        if s is None:
            i += 1; continue
        entry_i = i+1; entry = bars[entry_i]['open'] * (1+c.slippage)
        stop = entry-c.stop_atr*s['atr']
        if stop <= 0:
            i += 1; continue
        qty = min(equity*c.risk/(entry-stop), equity*c.notional_cap/entry)
        target = entry+c.target_r*(entry-stop)
        last_in_period = entry_i
        while last_in_period+1 < len(bars) and bars[last_in_period+1]['timestamp'] < end:
            last_in_period += 1
        exit_i = min(entry_i+c.max_hold-1, last_in_period)
        raw = bars[exit_i]['close']; reason = 'TIME' if exit_i < last_in_period else 'END'
        for j in range(entry_i, exit_i+1):
            b = bars[j]
            if b['open'] <= stop:
                exit_i, raw, reason = j, b['open'], 'GAP_STOP'; break
            if b['low'] <= stop:
                exit_i, raw, reason = j, stop, 'STOP'; break
            if b['high'] >= target:
                exit_i, raw, reason = j, target, 'TARGET'; break
        fill = raw*(1-c.slippage)
        fees = c.fee*qty*(entry+fill)
        gross = qty*(raw-entry/(1+c.slippage))
        pnl = qty*(fill-entry)-fees
        equity += pnl
        trades.append(dict(signal_index=i, entry_index=entry_i, exit_index=exit_i, entry=entry, exit=fill,
                           stop=stop, target=target, qty=qty, pnl=pnl, equity=equity, fees=fees,
                           gross=gross, slippage_cost=gross-fees-pnl, reason=reason,
                           btc_return=s['btc_return'], xrp_return=s['xrp_return']))
        if equity <= 0:
            break
        i = exit_i+1
    return trades
