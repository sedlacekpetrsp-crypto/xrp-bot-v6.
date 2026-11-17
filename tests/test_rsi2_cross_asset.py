"""Křížový test RSI(2): mechanika na syntetických datech (není důkaz ziskovosti)."""
import io
import math
import urllib.error
import zipfile
from datetime import datetime, timedelta, timezone

from research.rsi2_cross_asset import run


def _zip(rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "".join(f"{ts},{o},{h},{l},{c},0\n" for ts, o, h, l, c in rows))
    return buf.getvalue()


def fake_fetcher(url):
    name = url.rsplit("/", 1)[1][:-4]
    sym, rest = name.split("-1d-")
    y, m = map(int, rest.split("-"))
    if sym == "AVAXUSDT" and (y, m) < (2020, 10):
        raise urllib.error.HTTPError(url, 404, "nf", None, None)
    d0 = datetime(y, m, 1, tzinfo=timezone.utc)
    rows, d = [], d0
    while d.month == m:
        t = (d - datetime(2020, 1, 1, tzinfo=timezone.utc)).days
        px = 100 * (1 + 0.002 * t) * (1 + 0.08 * math.sin(t / 3.0))  # rostoucí trend s pullbacky
        rows.append((int(d.timestamp() * 1000), px, px * 1.01, px * 0.99, px))
        d += timedelta(days=1)
    return _zip(rows)


def test_end_to_end_synthetic(tmp_path):
    market, manifest, missing = run.load(tmp_path, fetcher=fake_fetcher)
    assert any("AVAXUSDT" in m for m in missing) and all(len(market[s]) > 2000 for s in run.SYMBOLS if s != "AVAXUSDT")
    res, ledger = run.evaluate(market)
    assert set(res["basket"]) == {f"{p}/x{m}" for p in run.base.PERIODS for m in run.base.COST_MULTIPLIERS}
    # koš = součet škálovaných obchodů: čistý P/L koše ≈ součet obchodů × 1/8 (bez otevřených pozic na konci)
    for key, g in res["basket"].items():
        p, x = key.split("/")
        tr = [t for t in ledger if t["period"] == p and t["cost_multiplier"] == int(x[1:])]
        assert g["trades"] == len(tr)
        assert abs(g["net_pnl"] - sum(t["net_pnl"] for t in tr) / len(run.SYMBOLS)) < 1e-6
    assert "basket_status" in res["verdict"]
    run.write(tmp_path / "out", res, ledger, manifest, missing)
    assert (tmp_path / "out" / "RESULTS.md").read_text().startswith("# RSI(2)")
