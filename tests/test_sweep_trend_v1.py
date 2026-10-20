from research.sweep_trend_v1 import Config, backtest

def sample():
    bars = []
    for i in range(80):
        bars.append({"open": 100., "high": 101., "low": 99., "close": 100., "volume": 1000.})
    return bars

def test_no_signals_in_flat_range():
    assert backtest(sample()) == []

def test_entry_is_after_signal_and_fees_are_deducted():
    bars = sample()
    bars[60] = {"open":100.,"high":101.,"low":97.,"close":100.5,"volume":1000.}
    trades = backtest(bars, Config(trend_period=10))
    assert trades
    assert all(t["entry_index"] == t["signal_index"]+1 for t in trades)
    assert all(t["net_return"] < t["gross_return"] for t in trades)

def test_both_brackets_hit_counts_as_stop():
    bars = sample()
    bars[60] = {"open":100.,"high":101.,"low":97.,"close":100.5,"volume":1000.}
    bars[61] = {"open":100.,"high":120.,"low":80.,"close":100.,"volume":1000.}
    trades = backtest(bars, Config(trend_period=10))
    assert trades[0]["reason"] == "STOP"
    assert trades[0]["net_return"] < 0
