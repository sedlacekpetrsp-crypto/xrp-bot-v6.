"""Offline spot LONG hypothesis. Never connects to an exchange or submits orders.

Consumes CLOSED bars with taker_buy_base (Binance kline field 9).
No parameter optimization: defaults fixed before first historical evaluation.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Config:
    window: int = 20
    flow_window: int = 3
    buy_share: float = 0.60
    volume_multiple: float = 1.25
    stop_atr: float = 1.5
    reward_risk: float = 2.0
    max_hold: int = 16
    fee: float = 0.00095
    slippage: float = 0.0002


def validate(bars):
    for b in bars:
        vals = [b[k] for k in ('open', 'high', 'low', 'close', 'volume', 'taker_buy_base')]
        if not all(isfinite(v) for v in vals):
            raise ValueError('Non-finite input')
        if not (0 < b['low'] <= min(b['open'], b['close']) <= max(b['open'], b['close']) <= b['high']):
            raise ValueError('Invalid OHLC')
        if not 0 <= b['taker_buy_base'] <= b['volume']:
            raise ValueError('Invalid taker volume')


def signal(bars, i, c=Config()):
    if i < c.window or i < c.flow_window:
        return None
    b = bars[i]
    past = bars[i-c.window:i]
    recent = bars[i-c.flow_window+1:i+1]
    volume = sum(x['volume'] for x in recent)
    baseline = sum(x['volume'] for x in past) / c.window
    if not volume or not baseline:
        return None
    share = sum(x['taker_buy_base'] for x in recent) / volume
    vwap = sum(x['close'] * x['volume'] for x in past) / sum(x['volume'] for x in past)
    atr = sum(max(bars[j]['high']-bars[j]['low'], abs(bars[j]['high']-bars[j-1]['close']), abs(bars[j]['low']-bars[j-1]['close'])) for j in range(i-c.window+1, i+1)) / c.window
    if (share >= c.buy_share and volume / c.flow_window >= baseline * c.volume_multiple
            and b['close'] > vwap and b['close'] > bars[i-c.flow_window]['close'] and atr > 0):
        return atr
    return None


def backtest(bars, c=Config()):
    validate(bars)
    trades = []
    i = c.window
    while i < len(bars)-1:
        atr = signal(bars, i, c)
        if atr is None:
            i += 1
            continue
        entry_i = i+1
        entry = bars[entry_i]['open'] * (1+c.slippage)
        stop = entry-c.stop_atr*atr
        target = entry+c.reward_risk*c.stop_atr*atr
        if stop <= 0:
            i += 1
            continue
        end = min(entry_i+c.max_hold-1, len(bars)-1)
        reason = 'END_OF_DATA' if end == len(bars)-1 else 'TIME'
        raw_exit = bars[end]['close']
        for j in range(entry_i, end+1):
            b = bars[j]
            if b['open'] <= stop:
                end, raw_exit, reason = j, b['open'], 'GAP_STOP'
                break
            if b['low'] <= stop:
                end, raw_exit, reason = j, stop, 'STOP'
                break
            if b['high'] >= target:
                end, raw_exit, reason = j, target, 'TARGET'
                break
        fill = raw_exit*(1-c.slippage)
        gross = (fill-entry)/entry
        fees = c.fee*(1+fill/entry)
        trades.append(dict(signal_index=i, entry_index=entry_i, exit_index=end,
                           entry=entry, exit=fill, stop=stop, target=target,
                           reason=reason, gross_return=gross, fees=fees, net_return=gross-fees))
        i = end+1
    return trades
