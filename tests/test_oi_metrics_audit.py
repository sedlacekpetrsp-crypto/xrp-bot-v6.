"""Mechanika auditu A3 krok 0 (syntetická data, žádné síťové volání, žádná výkonnost)."""
import datetime as dt
import io
import zipfile

from research.oi_metrics_audit import audit as A


def _zip(rows):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("x.csv", "create_time,symbol,sum_open_interest,v\n" + "\n".join(rows))
    return b.getvalue()


def test_parse_points_filters_invalid_and_dupes():
    day = dt.date(2023, 1, 2)
    rows = ["2023-01-02 00:00:00,BTCUSDT,10,1", "2023-01-02 00:00:00,BTCUSDT,10,1",  # duplicita
            "2023-01-02 00:07:00,BTCUSDT,10,1",  # nezarovnané
            "2023-01-02 00:10:00,BTCUSDT,0,1",  # nulové OI
            "2023-01-03 00:00:00,BTCUSDT,5,1",  # jiný den
            "2023-01-02 23:55:00,BTCUSDT,7,1"]
    good, bad = A.parse_points(_zip(rows), day)
    assert good == {0, 287} and bad == 3


def test_gaps_counts_hour_runs():
    d = dt.date(2023, 1, 1)
    slots = {d: set(range(288)) - set(range(12, 36))}  # 2 h díra
    assert A.gaps(slots, d, d) == (1, 2.0, 2.0)
    assert A.gaps({d: set(range(288)) - set(range(0, 11))}, d, d) == (0, 0, 0)


def test_gate_rules():
    def asset(i, cov, wq, delisted=False):
        return {"symbol": f"S{i}", "live_days": 100, "coverage": cov, "worst_quarter_cov": wq, "delisted": delisted}
    arows = [asset(i, 0.99, 0.95) for i in range(15)]
    qrows = [{"symbol": f"S{i}", "quarter": q, "coverage": 0.99, "evaluated": True}
             for i in range(15) for q in ("2022Q1", "2026Q3")]
    g = A.gate(arows, qrows)
    assert g["G1_min_assets"] and g["G2_every_quarter"] and g["G3_selection_bias"] and g["verdict"].startswith("GO")
    arows[0]["worst_quarter_cov"] = 0.89
    assert A.gate(arows, qrows)["verdict"] == "NO-GO"


def test_universe_frozen_81():
    u = A.universe(A.HERE / "listings_frozen.csv")
    assert len(u) == 81 and sum(x["delisted"] for x in u) == 23
