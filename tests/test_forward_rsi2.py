"""Forward PAPER RSI(2): mechanika na syntetických datech (není důkaz ziskovosti)."""
import importlib.util
import io
import math
import urllib.error
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "fwd", Path(__file__).resolve().parents[1] / "research" / "forward" / "rsi2_pullback" / "run.py")
fwd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fwd)
TODAY = date(2026, 12, 20)


def px(d):
    t = (d - date(2025, 1, 1)).days
    return 100 * (1 + 0.003 * t) * (1 + 0.06 * math.sin(t / 2.5))


def zrows(days):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "".join(
            f"{int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1_000_000)},{px(d)},{px(d)*1.01},{px(d)*0.99},{px(d)},0\n"
            for d in days))
    return buf.getvalue()


def fetcher(url):
    name = url.rsplit("/", 1)[1][:-4]
    parts = name.split("-1d-")[1].split("-")
    if "/monthly/" in url:
        y, m = map(int, parts)
        if (y, m) >= (2026, 11):
            raise urllib.error.HTTPError(url, 404, "nf", None, None)
        d, days = date(y, m, 1), []
        while d.month == m:
            days.append(d)
            d += timedelta(days=1)
        return zrows(days)
    d = date(*map(int, parts))
    if d == date(2026, 11, 20):  # chybějící denní soubor
        raise urllib.error.HTTPError(url, 404, "nf", None, None)
    return zrows([d])


def test_forward_runs_and_respects_start(tmp_path):
    st = fwd.run(["BTCUSDT"], tmp_path / "c", tmp_path / "o", today=TODAY, fetcher=fetcher)
    assert st["start"] == "2026-11-07" and st["updated_for"] == "2026-12-19"
    rows = (tmp_path / "o" / "trades.csv").read_text().splitlines()[1:]
    assert rows, "syntetický trend s pullbacky musí vygenerovat obchody"
    assert all(r.split(",")[2] >= "2026-11-08" for r in rows)  # vstup nejdřív open dne po prvním signálu
    x1, x2 = st["by_cost"]["x1"], st["by_cost"]["x2"]
    assert x1["closed_trades"] == x2["closed_trades"] and x2["return_pct"] < x1["return_pct"]
    assert (tmp_path / "o" / "STATUS.md").read_text().startswith("# Forward PAPER")
