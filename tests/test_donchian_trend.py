"""Mechanika Donchian backtestu na syntetických datech (není důkaz ziskovosti)."""
import io
import zipfile
from datetime import date, datetime, timedelta, timezone

import pytest

from research.donchian_trend import run

D0 = datetime(2023, 1, 1, tzinfo=timezone.utc)


def bars_from(rows):
    """rows: list (open, high, low, close) po dnech od 2023-01-01."""
    return [{"ts": int((D0 + timedelta(days=i)).timestamp() * 1000), "open": o, "high": h, "low": l, "close": c}
            for i, (o, h, l, c) in enumerate(rows)]


def flat(n, px=100.0):
    return [(px, px + 1, px - 1, px)] * n


def test_breakout_enters_next_open_and_channel_exit_next_open_with_costs():
    rows = flat(25) + [(100, 110, 100, 108)]          # den 25: close 108 > max high 101 ⇒ signál
    rows += [(109, 112, 108, 111)] * 3                # den 26: vstup za open 109
    rows += [(105, 106, 90, 92)]                      # den 29 (30. 1.): close 92 < min low posledních 10 ⇒ výstup
    rows += [(93, 94, 92, 93)] + flat(3, 93.0)        # den 30 (31. 1.): výstup za open 93
    b = bars_from(rows)
    tr, cv = run.simulate(b, date(2023, 1, 1), date(2023, 2, 10), n=20, k=50.0, mult=1, equity=1000.0)
    assert len(tr) == 1
    t = tr[0]
    assert t["entry_day"] == "2023-01-27" and t["exit_day"] == "2023-01-31"
    assert t["entry_px"] == pytest.approx(109 * (1 + run.SLIP))
    assert t["exit_px"] == pytest.approx(93 * (1 - run.SLIP))
    assert t["reason"] == "CHANNEL_EXIT"
    assert t["fees"] == pytest.approx(t["qty"] * t["entry_px"] * run.FEE + t["qty"] * t["exit_px"] * run.FEE)
    assert cv[max(cv)] == pytest.approx(1000.0 + t["net_pnl"])


def test_gap_below_stop_exits_at_open_not_at_stop():
    rows = flat(25) + [(100, 110, 100, 108), (109, 110, 108, 109), (80, 82, 75, 78)] + flat(3, 78.0)
    b = bars_from(rows)
    tr, _ = run.simulate(b, date(2023, 1, 1), date(2023, 2, 5), n=20, k=2.0, mult=1, equity=1000.0)
    assert tr[0]["reason"] == "STOP"
    assert tr[0]["exit_px"] == pytest.approx(80 * (1 - run.SLIP))  # gap: open 80 < stop


def test_intraday_stop_exits_at_stop_price():
    rows = flat(25) + [(100, 110, 100, 108), (109, 110, 108, 109), (105, 106, 60, 104)] + flat(3, 104.0)
    b = bars_from(rows)
    tr, _ = run.simulate(b, date(2023, 1, 1), date(2023, 2, 5), n=20, k=2.0, mult=1, equity=1000.0)
    t = tr[0]
    assert t["reason"] == "STOP" and t["exit_px"] == pytest.approx(t["stop"] * (1 - run.SLIP))


def test_no_signal_without_close_above_previous_highs():
    rows = flat(25) + [(100, 130, 99, 100.5)] + flat(5)  # high vysoko, ale close pod předchozím max high
    tr, _ = run.simulate(bars_from(rows), date(2023, 1, 1), date(2023, 2, 1), n=20, k=2.0, mult=1)
    assert tr == []


def test_position_closed_at_period_end_and_costs_scale():
    rows = flat(25) + [(100, 110, 100, 108)] + [(109, 112, 108, 111)] * 5
    b = bars_from(rows)
    t1, _ = run.simulate(b, date(2023, 1, 1), date(2023, 1, 31), n=20, k=50.0, mult=1)
    t3, _ = run.simulate(b, date(2023, 1, 1), date(2023, 1, 31), n=20, k=50.0, mult=3)
    assert t1[0]["reason"] == "END_OF_PERIOD"
    assert t3[0]["fees"] > 2.9 * t1[0]["fees"]


def test_parse_handles_microseconds_and_header():
    us = int(datetime(2025, 3, 1, tzinfo=timezone.utc).timestamp() * 1_000_000)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "open_time,open,high,low,close\n" + f"{us},1,2,0.5,1.5,0,0\n")
    bars = run.parse(buf.getvalue())
    assert len(bars) == 1 and run.day(bars[0]["ts"]) == date(2025, 3, 1)


def test_atr_wilder():
    b = bars_from([(10, 12, 8, 10)] * 25)
    a = run.atr_series(b, n=20)
    assert a[18] is None and a[19] == pytest.approx(4.0) and a[24] == pytest.approx(4.0)


def test_verdict_rejects_when_any_check_fails():
    good = {"sharpe": 2.0, "max_drawdown_pct": 10.0, "trades": 40, "profit_factor": 2.0, "net_pnl": 100.0,
            "net_without_top3": 10.0}
    bh = {"sharpe": 1.0, "max_drawdown_pct": 50.0}
    res = {"grid": {f"V/{p}/x{m}": dict(good) for p in run.PERIODS for m in (1, 2, 3)},
           "buy_hold": {f"{p}/x{m}": dict(bh) for p in run.PERIODS for m in (1, 2, 3)}}
    assert run.verdict(res, "V")["status"].startswith("KANDIDÁT")
    res["grid"]["V/validation/x1"]["trades"] = 29
    assert run.verdict(res, "V")["status"] == "ZAMÍTNUTO"
