import datetime as dt

from research.k6_bvol_audit.step0 import cadence, diff_counter, file_date, gate, lag_days, parse_csv

D0 = dt.date(2024, 1, 1)


def _days(n, points=1440, bad=()):
    return [{"date": D0 + dt.timedelta(days=i), "points": points, "outside": 0, "ok": i not in bad} for i in range(n)]


def test_gate_go_and_threshold():
    audit = D0 + dt.timedelta(days=600)
    g = gate(_days(600), 60, audit)
    assert g["GO"] and g["run_days"] == 600 and g["run_cov"] == 1.0
    assert not gate(_days(547), 60, D0 + dt.timedelta(days=547))["GO"]


def test_gate_break_not_pit_and_stale_and_cadence():
    audit = D0 + dt.timedelta(days=700)
    g = gate(_days(700, bad={100}), 60, audit)
    assert g["run_start"] == str(D0 + dt.timedelta(days=101)) and g["run_days"] == 599 and g["GO"]
    assert not gate(_days(600), 60, D0 + dt.timedelta(days=620))["GO"]  # zastaralé
    assert not gate(_days(600), 120, D0 + dt.timedelta(days=600))["GO"]  # nepovolená kadence
    assert not gate(_days(600, points=1300), 60, D0 + dt.timedelta(days=600))["GO"]  # pokrytí < 95 %


def test_fresh_run_preferred_over_older_longer():
    days = _days(1300, bad={700})
    g = gate(days, 60, D0 + dt.timedelta(days=1300))
    assert g["run_start"] == str(D0 + dt.timedelta(days=701)) and g["run_days"] == 599


def test_parse_lag_cadence():
    raw = b"calc_time,symbol,base_asset,quote_asset,index_value\n1704067200000,BTCBVOLUSDT,BTC,USDT,55.1\n1704067260000,BTCBVOLUSDT,BTC,USDT,55.2\n"
    h, ts, v = parse_csv(raw)
    assert h[0] == "calc_time" and ts == [1704067200000, 1704067260000] and v == [55.1, 55.2]
    assert cadence(diff_counter(ts)) == 60
    assert file_date("x/BTCBVOLUSDT-BVOLIndex-2024-01-01.zip") == D0
    assert lag_days("2024-01-02T06:00:00.000Z", D0) == 0.25
