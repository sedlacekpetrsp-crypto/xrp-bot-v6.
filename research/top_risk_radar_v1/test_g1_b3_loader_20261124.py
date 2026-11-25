"""Synthetic tests for the G1 B3 loader (no market data, no network, no fit)."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1 import g1_b3_loader as L

UTC = timezone.utc
M = timedelta(minutes=1)
SHA_X = "a" * 64
SHA_B = "b" * 64
D0 = datetime(2024, 12, 1, tzinfo=UTC)          # first minute of data
KEY = datetime(2025, 1, 2, 0, 5, tzinfo=UTC)    # decision key (31 daily closes back to 2024-12-02)
END = KEY + M + L.HORIZON + timedelta(hours=1)  # data end, label matured


def price(sym: str, t: datetime) -> float:
    k = (t - D0) / M
    base = 0.6 if sym == "X" else 60000.0
    return base * (1 + 0.05 * math.sin(k / 1440.0 * 0.9) + 0.002 * math.sin(k / 37.0))


def bars(sym: str, start=D0, end=END, sha=None, override=None, skip=(), ms=True):
    out, t = [], start
    override = override or {}
    while t < end:
        if t not in skip:
            p = price(sym, t)
            o, h, lo, c, n = override.get(t, (p, p * 1.0005, p * 0.9995, p, 7))
            out.append(L.Bar(t, o, h, lo, c, n, sha or (SHA_X if sym == "X" else SHA_B)))
        t += M
    return out


def series(sym, **kw):
    return L.MinuteSeries("XRPUSDT" if sym == "X" else "BTCUSDT", bars(sym, **kw))


def row(xrp=None, btc=None, as_of=END, key=KEY):
    return L.build_g1_rows(xrp or series("X"), btc or series("B"), [key], as_of)[0]


def csv_line(t, o=1.0, h=1.1, lo=0.9, c=1.0, n=3, us=False):
    mult = 1_000_000 if us else 1000
    ot = int(t.timestamp() * mult)
    ct = ot + 60 * mult - 1
    return f"{ot},{o},{h},{lo},{c},10,{ct},10,{n},1,1,0"


# --- parser -----------------------------------------------------------------
def test_parse_ms_and_us_and_header():
    t = datetime(2024, 12, 31, 23, 59, tzinfo=UTC)
    got = L.parse_klines_1m(["open_time,o,h,l,c,v,ct,q,n,tb,tq,i", csv_line(t), csv_line(t + M, us=True)], SHA_X)
    assert [b.open_time for b in got] == [t, t + M]
    assert got[1].archive_sha256 == SHA_X


@pytest.mark.parametrize("lines", [
    [csv_line(D0), csv_line(D0)],                               # duplicate
    [csv_line(D0 + M), csv_line(D0)],                           # out of order
    [csv_line(D0, lo=1.05)],                                    # low > close
    [csv_line(D0, h=0.95)],                                     # high < open
    [csv_line(D0, o=0)],                                        # non-positive
    [csv_line(D0, o="nan")],                                    # non-finite
    [csv_line(D0, n=-1)],                                       # negative trades
    [csv_line(D0).rsplit(",", 1)[0]],                           # 11 columns
    [csv_line(D0 + timedelta(seconds=30))],                     # off-minute open
    [csv_line(D0).replace(str(int(D0.timestamp() * 1000) + 59999), str(int(D0.timestamp() * 1000) + 119999))],
])
def test_parse_fails_closed(lines):
    with pytest.raises(L.LoaderError):
        L.parse_klines_1m(lines, SHA_X)


def test_parse_rejects_bad_archive_hash():
    with pytest.raises(L.LoaderError):
        L.parse_klines_1m([csv_line(D0)], "A" * 64)


def test_duplicate_minute_across_archives_is_invalid():
    with pytest.raises(L.LoaderError):
        L.MinuteSeries("XRPUSDT", bars("X", end=D0 + 3 * M) + bars("X", start=D0 + 2 * M, end=D0 + 4 * M))


# --- usable row ---------------------------------------------------------------
def test_usable_row_has_frozen_b3_features_and_provenance():
    r = row()
    assert r["status"] == "usable" and r["y"] in (0, 1)
    assert tuple(r["features"]) == L.B3_FEATURES
    assert all(math.isfinite(v) for v in r["features"].values())
    assert r["decision_at_utc"] == "2025-01-02T00:06:00+00:00"
    assert r["provenance"]["features"]["source_archive_sha256"] == [SHA_X, SHA_B]
    assert r["provenance"]["features"]["max_available_at_utc"] == "2025-01-02T00:01:00+00:00"   # close + 60 s < 00:05
    assert r["reference_price"] == pytest.approx(price("X", KEY))


def test_btc_rv30_matches_manual_population_std():
    closes = [price("B", KEY.replace(minute=0) - L.DAY * i - M) for i in range(30, -1, -1)]
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, 31)]
    mu = sum(rets) / 30
    assert row()["features"]["btc_realized_vol_30d"] == pytest.approx(
        math.sqrt(sum((x - mu) ** 2 for x in rets) / 30), rel=1e-12)


# --- PIT boundary (manifest v1 par. 3 + G1_PIT_0005_BOUNDARY_QA) ------------------
def test_crash_inside_minute_0005_is_not_a_label():
    p = price("X", KEY)
    r = row(series("X", override={KEY: (p, p, 0.70 * p, p, 9)}))
    assert r["status"] == "usable" and r["y"] == 0 and r["reference_price"] == pytest.approx(p)


def test_minute_0006_touch_is_positive():
    p = price("X", KEY)
    q = price("X", KEY + M)
    r = row(series("X", override={KEY + M: (q, q, 0.8 * p, q, 9)}))
    assert r["y"] == 1


def test_horizon_end_is_exclusive():
    p = price("X", KEY)
    last = KEY + M + L.HORIZON - M
    first_out = KEY + M + L.HORIZON
    q1, q2 = price("X", last), price("X", first_out)
    assert row(series("X", override={last: (q1, q1, 0.79 * p, q1, 4)}))["y"] == 1
    assert row(series("X", override={first_out: (q2, q2, 0.79 * p, q2, 4)}))["y"] == 0


def test_reference_is_close_not_open():
    p = price("X", KEY)
    r = row(series("X", override={KEY: (2 * p, 2 * p, p, p, 3)}))
    assert r["reference_price"] == pytest.approx(p)


# --- exclusions, never imputed -------------------------------------------------------
def test_zero_trade_reference_minute_excluded():
    p = price("X", KEY)
    r = row(series("X", override={KEY: (p, p, p, p, 0)}))
    assert (r["status"], r["reason"]) == ("excluded", "no_trade_in_minute_0005")


def test_missing_reference_minute_excluded():
    assert row(series("X", skip={KEY}))["reason"] == "no_trade_in_minute_0005"


def test_missing_minute_in_horizon_excluded_even_after_hit():
    p = price("X", KEY)
    q = price("X", KEY + M)
    r = row(series("X", override={KEY + M: (q, q, 0.5 * p, q, 9)}, skip={KEY + timedelta(days=5)}))
    assert r["reason"] == "missing_minutes_in_horizon"


def test_missing_daily_close_bar_excludes_row():
    gap = datetime(2024, 12, 20, 23, 59, tzinfo=UTC)
    assert row(btc=series("B", skip={gap}))["reason"] == "incomplete_daily_bar"


def test_intraday_gap_outside_close_bar_does_not_drop_day():
    gap = datetime(2024, 12, 20, 12, 0, tzinfo=UTC)
    assert row(btc=series("B", skip={gap}))["status"] == "usable"


def test_insufficient_lookback_excluded():
    late = series("X", start=datetime(2024, 12, 5, tzinfo=UTC))
    assert row(late)["reason"] == "incomplete_daily_bar"


def test_unmatured_positive_is_not_usable():
    """Block B: an early hit never relaxes the full-horizon maturity rule."""
    p = price("X", KEY)
    q = price("X", KEY + M)
    xs = series("X", override={KEY + M: (q, q, 0.5 * p, q, 9)})
    r = row(xs, as_of=KEY + timedelta(days=3))
    assert (r["status"], r["reason"]) == ("excluded", "unmatured")


# --- perturbation (no leakage) -----------------------------------------------------
def _perturb(after: datetime, factor: float):
    return {t: (price("X", t) * factor,) * 2 + (price("X", t) * factor * 0.5, price("X", t) * factor, 1)
            for t in (after + M * i for i in range(0, int((END - after) / M)))}


def test_future_minutes_from_0000_do_not_change_features():
    base = row()
    day0 = KEY.replace(minute=0)
    ov = {t: v for t, v in _perturb(day0, 3.0).items() if t != KEY}
    pert = row(series("X", override=ov))
    assert pert["features"] == base["features"]
    assert pert["provenance"]["features"] == base["provenance"]["features"]


def test_minutes_after_0006_do_not_change_features_or_reference():
    base = row()
    pert = row(series("X", override=_perturb(KEY + M, 0.1)))
    assert pert["features"] == base["features"] and pert["reference_price"] == base["reference_price"]
    assert pert["y"] == 1   # label does see the future, by design


# --- input contract ------------------------------------------------------------------
def test_off_grid_decision_rejected():
    with pytest.raises(ValueError):
        row(key=KEY.replace(minute=6))


def test_as_of_beyond_data_rejected():
    with pytest.raises(L.LoaderError):
        row(as_of=END + timedelta(days=1))


def test_swapped_symbols_rejected():
    with pytest.raises(L.LoaderError):
        L.build_g1_rows(series("B"), series("X"), [KEY], END)


def test_summary_and_hash_deterministic():
    rows = L.build_g1_rows(series("X"), series("B"), [KEY, KEY + L.DAY], END)
    s = L.exclusion_summary(rows)
    assert s["rows"] == 2 and s["usable"] + sum(s["excluded"].values()) == 2
    assert L.rows_sha256(rows) == L.rows_sha256(L.build_g1_rows(series("X"), series("B"), [KEY, KEY + L.DAY], END))


def test_perturbation_test_is_sensitive_to_last_available_bar():
    """Control: the 23:59 bar before the decision day IS a feature input."""
    t = KEY.replace(minute=0) - M
    p = price("X", t)
    assert row(series("X", override={t: (p, 2 * p, p, 2 * p, 5)}))["features"] != row()["features"]


# --- review 6053223820 (ChatGPT, PR #78) -------------------------------------------
@pytest.mark.parametrize("as_of", [KEY, KEY - L.DAY, KEY + M - timedelta(microseconds=1)])
def test_decision_after_as_of_emits_no_payload(as_of):
    r = row(as_of=as_of)
    assert (r["status"], r["reason"]) == ("excluded", "decision_after_as_of")
    assert not {"features", "reference_price", "provenance", "y"} & set(r)


def test_decision_exactly_at_as_of_is_unmatured_with_reference_only():
    r = row(as_of=KEY + M)
    assert r["reason"] == "unmatured" and r["provenance"]["label"] is None
    assert r["provenance"]["reference"]["bar_open_utc"] == KEY.isoformat()


def test_feature_reference_label_provenance_separated_full_horizon():
    sha_ref, sha_last = "c" * 64, "d" * 64
    p = price("X", KEY)
    q = price("X", KEY + M)
    last = KEY + M + L.HORIZON - M
    xb = []
    for b in bars("X", override={KEY + M: (q, q, 0.5 * p, q, 9)}):   # early hit at 00:06
        if b.open_time == KEY:
            b = L.Bar(b.open_time, b.open, b.high, b.low, b.close, b.trades, sha_ref)
        elif b.open_time == last:
            b = L.Bar(b.open_time, b.open, b.high, b.low, b.close, b.trades, sha_last)
        xb.append(b)
    r = row(L.MinuteSeries("XRPUSDT", xb))
    assert r["y"] == 1
    prov = r["provenance"]
    assert prov["reference"]["archive_sha256"] == sha_ref
    assert sha_last in prov["label"]["archive_sha256"] and SHA_X in prov["label"]["archive_sha256"]
    assert prov["label"]["last_bar_utc"] == last.isoformat()
    assert sha_ref not in prov["features"]["source_archive_sha256"]
    assert sha_last not in prov["features"]["source_archive_sha256"]
