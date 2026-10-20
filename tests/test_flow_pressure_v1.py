from dataclasses import replace
import unittest
from research.flow_pressure_v1 import Config, backtest, signal


def sample():
    bars = [dict(open=100., high=101., low=99., close=100., volume=100., taker_buy_base=50.) for _ in range(80)]
    for i in range(28, 31):
        bars[i] = dict(open=100., high=102., low=99., close=101., volume=200., taker_buy_base=150.)
    return bars


def test_requires_real_buy_pressure():
    bars = sample()
    assert signal(bars, 30) is not None
    for b in bars:
        b['taker_buy_base'] = b['volume']/2
    assert backtest(bars) == []


def test_signal_is_causal_and_entry_is_next_open():
    bars = sample()
    assert signal(bars, 30) == signal(bars[:31], 30)
    trades = backtest(bars)
    assert trades
    assert all(t['entry_index'] == t['signal_index']+1 for t in trades)
    assert all(t['net_return'] == t['gross_return']-t['fees'] for t in trades)


def test_ambiguous_bar_stops_first():
    bars = sample()
    first = backtest(bars)[0]
    bars[first['entry_index']].update(high=120., low=80.)
    assert backtest(bars)[0]['reason'] == 'STOP'


def test_gap_stop_uses_open_and_higher_costs_hurt():
    bars = sample()
    first = backtest(bars)[0]
    bars[first['entry_index']+1].update(open=90., low=89., high=91., close=90.)
    trade = backtest(bars)[0]
    assert trade['reason'] == 'GAP_STOP'
    assert trade['exit'] < 90.
    assert backtest(bars, replace(Config(), fee=0.0019))[0]['net_return'] < trade['net_return']


def test_invalid_volume_and_nan_rejected():
    for value in (101., float('nan')):
        bars = sample()
        bars[0]['taker_buy_base'] = value
        with unittest.TestCase().assertRaises(ValueError):
            backtest(bars)

if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")
