"""Syntetické testy mechaniky inventury A1 krok 1 (ne důkaz čehokoli o trhu)."""
import datetime as dt
import hashlib
import io
import urllib.error
import zipfile

from research.new_listing_inventory import inventory as inv


def _zip(rows):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("x.csv", "open_time,open\n" + "\n".join(",".join(map(str, r)) for r in rows))
    return b.getvalue()


def _ms(d, h=0, m=0):
    return int(dt.datetime(d.year, d.month, d.day, h, m, tzinfo=dt.timezone.utc).timestamp() * 1000)


class FakeVision:
    def __init__(self, files, bad_checksum=()):
        self.files, self.bad = files, set(bad_checksum)

    def __call__(self, url):
        if url.endswith(".CHECKSUM"):
            base = url[: -len(".CHECKSUM")]
            if base not in self.files:
                raise urllib.error.HTTPError(url, 404, "nf", None, None)
            h = "0" * 64 if base in self.bad else hashlib.sha256(self.files[base]).hexdigest()
            return f"{h}  {base.rsplit('/', 1)[1]}".encode()
        if url not in self.files:
            raise urllib.error.HTTPError(url, 404, "nf", None, None)
        return self.files[url]


def _symbol(sym, days, first_minute=(9, 0)):
    files, keys = {}, []
    by_month = {}
    for d in days:
        by_month.setdefault((d.year, d.month), []).append(d)
    for (y, m), ds in by_month.items():
        url = f"{inv.VISION}/data/futures/um/monthly/klines/{sym}/1d/{sym}-1d-{y}-{m:02d}.zip"
        files[url] = _zip([[_ms(d), 1.0] for d in ds])
        keys.append(f"data/futures/um/monthly/klines/{sym}/1d/{sym}-1d-{y}-{m:02d}.zip")
    f = days[0]
    files[f"{inv.VISION}/data/futures/um/daily/klines/{sym}/1m/{sym}-1m-{f.isoformat()}.zip"] = _zip(
        [[_ms(f, *first_minute), 1.0], [_ms(f, first_minute[0], first_minute[1] + 1), 1.0]])
    fkeys = [f"data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{y}-{m:02d}.zip" for (y, m) in by_month]
    return files, keys, fkeys


def _span(a, b):
    return [a + dt.timedelta(i) for i in range((b - a).days + 1)]


def test_universe_filter():
    assert inv.is_usdt_perp("BTCUSDT")
    assert not inv.is_usdt_perp("BTCUSDT_230331")
    assert not inv.is_usdt_perp("BTCUSDC")
    assert not inv.is_usdt_perp("ETHBUSD")


def test_active_listing_first_minute_and_eligible(tmp_path):
    days = _span(dt.date(2023, 3, 10), inv.END_DAY)
    files, kk, fk = _symbol("NEWUSDT", days, (8, 30))
    row, man = inv.analyse_symbol("NEWUSDT", kk, fk, tmp_path, FakeVision(files))
    assert row["first_trade_utc"].startswith("2023-03-10T08:30")
    assert row["first_trade_source"] == "1m_first_bar"
    assert row["status"] == "active" and row["missing_days"] == 0 and row["funding_ok"]
    assert all(m["checksum"] == "ok" for m in man)
    inv.apply_exchangeinfo(row, {"NEWUSDT": {"onboardDate": inv.dt.datetime(2023, 3, 10, 8, tzinfo=dt.timezone.utc).timestamp() * 1000, "status": "TRADING"}})
    assert inv.eligibility(row) == (True, "")
    assert "price" not in str(row).lower()


def test_early_delisting_is_kept_not_dropped(tmp_path):
    days = _span(dt.date(2022, 5, 1), dt.date(2022, 8, 15))  # < 180 dní, delisting
    files, kk, fk = _symbol("DEADUSDT", days)
    row, _ = inv.analyse_symbol("DEADUSDT", kk, fk, tmp_path, FakeVision(files))
    inv.apply_exchangeinfo(row, {})
    assert row["status"] == "delisted"
    assert inv.eligibility(row) == (True, "")


def test_reused_ticker_and_missing_days(tmp_path):
    days = _span(dt.date(2021, 1, 1), dt.date(2021, 6, 30)) + _span(dt.date(2023, 1, 1), inv.END_DAY)
    days = [d for d in days if d not in (dt.date(2021, 2, 1), dt.date(2021, 2, 2), dt.date(2021, 2, 3))]
    files, kk, fk = _symbol("OLDUSDT", days)
    row, _ = inv.analyse_symbol("OLDUSDT", kk, fk, tmp_path, FakeVision(files))
    assert row["gap_segments"] == 2 and row["reused_ticker"]
    assert row["missing_days_first180"] == 3
    inv.apply_exchangeinfo(row, None)
    assert row["exchangeinfo_status"] == "unavailable"
    assert inv.eligibility(row) == (False, "reused_ticker")


def test_checksum_mismatch_and_missing_funding(tmp_path):
    days = _span(dt.date(2024, 1, 1), dt.date(2024, 12, 31))
    files, kk, fk = _symbol("BADUSDT", days)
    bad = f"{inv.VISION}/data/futures/um/monthly/klines/BADUSDT/1d/BADUSDT-1d-2024-05.zip"
    row, man = inv.analyse_symbol("BADUSDT", kk, fk[1:], tmp_path, FakeVision(files, [bad]))
    assert [m["checksum"] for m in man].count("MISMATCH") == 1
    assert not row["funding_ok"]
    inv.apply_exchangeinfo(row, {"BADUSDT": {"status": "SETTLING"}})
    assert row["status"] == "delisted"
    assert inv.eligibility(row) == (False, "funding_incomplete")


def test_gates():
    rows = []
    for y in range(2021, 2026):
        for i in range(20):
            rows.append({"eligible_a1": True, "first_day": f"{y}-02-01", "status": "delisted" if i < 3 else "active",
                         "first_trade_utc": f"{y}-02-01T08:00:00+00:00", "onboard_date_utc": f"{y}-02-01T07:00:00+00:00"})
    g, _ = inv.gates(rows, {"ok": 10})
    assert g["GO"] and g["G4_onboard_match_ge_90pct"]["pass"]
    g, _ = inv.gates(rows[:50], {"ok": 10, "MISMATCH": 1})
    assert not g["GO"] and not g["G1_eligible_ge_100"]["pass"] and not g["G5_checksums_ok"]["pass"]
