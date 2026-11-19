"""Syntetické testy kolektoru K11 kroku 0 (bez sítě, bez cen, bez výnosů)."""
import hashlib
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from research import k11_step0_collector as c

UTC = timezone.utc
T = datetime(2025, 3, 10, 9, 0, tzinfo=UTC)
CODE = "a" * 32


@pytest.mark.parametrize("title,etype", [
    ("Binance Will Delist ANT, MULTI, VAI, XMR on 2024-02-20", "spot_delist"),
    ("Binance Will Delist BTCST, DREP & MITH", "spot_delist"),
    ("Binance Margin Will Delist ABC/BTC", "margin_delist"),
    ("Binance Futures Will Delist USDⓈ-M ABCUSDT Perpetual Contract", "futures_delist"),
    ("Binance Will Delist ABCUSDT Perpetual Contract", "futures_delist"),
    ("Notice of Removal of Spot Trading Pairs - 2025-03-10", "pair_removal"),
    ("Binance Will Extend Monitoring Tag to Include ABC", "monitoring_tag"),
    ("Binance Vote to Delist Results", "vote_to_delist"),
])
def test_classify_title(title, etype):
    assert c.classify_title(title) == etype


def test_parse_tokens_and_fail_closed():
    assert c.parse_tokens("Binance Will Delist ANT, MULTI, VAI, XMR on 2024-02-20") == ["ANT", "MULTI", "VAI", "XMR"]
    assert c.parse_tokens("Binance Will Delist BTCST, DREP & MITH") == ["BTCST", "DREP", "MITH"]
    assert c.parse_tokens("Binance Will Delist Bitcoin Standard Hashrate Token (BTCST)") == ["BTCST"]
    assert c.parse_tokens("Binance Will Delist Some Tokens") is None          # žádný ticker ⇒ nehádat
    assert c.parse_tokens("Binance Will Delist ABC, ABC") is None             # duplicita ⇒ nejednoznačné


def test_extract_codes_html_and_json():
    html = b'<a href="/en/support/announcement/binance-will-delist-abc-' + CODE.encode() + b'">x</a>'
    assert c.extract_codes(html) == {CODE}
    assert c.extract_codes(json.dumps({"code": "b" * 32}).encode()) == {"b" * 32}
    assert c.extract_codes(b"<div id=root></div>") == set()


def test_parse_cdx_only_200_and_real_timestamp():
    rows = [["timestamp", "original", "statuscode", "digest"],
            ["20250310093000", "u", "200", "D1"], ["20250310093100", "u", "302", "D2"]]
    assert c.parse_cdx(rows) == [(datetime(2025, 3, 10, 9, 30, tzinfo=UTC), "u", "D1")]
    with pytest.raises(ValueError):
        c.parse_cdx([rows[0], ["2025031009", "u", "200", "D"]])


def test_needed_captures_window_and_digest_dedupe_keeps_all_times():
    caps = [(T - timedelta(days=8), "u", "A"), (T - timedelta(days=6), "u", "B"),
            (T + timedelta(hours=1), "u", "B"), (T + timedelta(hours=25), "u", "C")]
    got = c.needed_captures(caps, [T])
    assert list(got) == ["B"]                                   # 1 stažení na digest
    assert got["B"][1] == [T - timedelta(days=6), T + timedelta(hours=1)]  # oba okamžiky zachovány


def test_same_digest_later_capture_still_corroborates():
    """Snímek se stejným digestem v [release−24 h, release) a v [release, +24 h] ⇒ ok, ne unverified."""
    net = FakeNet()
    early, late = T - timedelta(hours=2), T + timedelta(hours=3)
    rows = [["timestamp", "original", "statuscode", "digest"],
            [early.strftime("%Y%m%d%H%M%S"), "https://www.binance.com/en/support/announcement/c-161", "200", "D"],
            [late.strftime("%Y%m%d%H%M%S"), "https://www.binance.com/en/support/announcement/c-161", "200", "D"]]
    orig = net.__call__

    class Net(FakeNet):
        def __call__(self, url):
            if url.startswith("https://web.archive.org/cdx") and "c-161" in url:
                return 200, json.dumps(rows).encode()
            return orig(url)
    n2 = Net()
    n2.files = net.files
    out, _ = c.collect(n2)
    assert {r["pit_status"] for r in out if r["event_type"] == "spot_delist"} == {"ok"}


def test_pit_unrendered_snapshot_ignored_and_contradiction():
    assert c.pit_for_article(CODE, T, [(T + timedelta(hours=2), set())])[0] == "unverified"
    assert c.pit_for_article(CODE, T, [(T + timedelta(hours=2), {CODE})])[0] == "ok"
    assert c.pit_for_article(CODE, T, [(T - timedelta(days=3), {CODE}), (T + timedelta(hours=2), {CODE})])[0] \
        == "contradicted"
    assert c.pit_for_article(CODE, T, [(T + timedelta(hours=2), {"f" * 32})])[0] == "unverified"


def _minutes(start, end):
    return set(range(int(start.timestamp()) // 60, int(end.timestamp()) // 60))


def test_perp_and_coverage():
    full = _minutes(T - timedelta(days=7), T + timedelta(days=14))
    assert c.perp_and_coverage(full, T)[:2] == (True, True)
    hole = full - {int((T + timedelta(minutes=75)).timestamp()) // 60}   # díra v hodině vstupu
    assert c.perp_and_coverage(hole, T)[0] is False
    short = _minutes(T - timedelta(days=7), T + timedelta(hours=20))      # konec < t+L+24 h
    perp_ok, cov_ok, info = c.perp_and_coverage(short, T)
    assert perp_ok is False and cov_ok is False  # frozen full window; do not truncate denominator
    sparse = {m for m in full if m % 10}                                   # 90 % minut
    assert c.perp_and_coverage(sparse, T)[1] is False


def _zip(minutes, micro=False):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        mult = 60_000_000 if micro else 60_000
        lines = ["open_time,open,high,low,close"] + [f"{m * mult},1,1,1,1" for m in sorted(minutes)]
        z.writestr("x.csv", "\n".join(lines))
    return buf.getvalue()


def test_open_minutes_reads_only_timestamps_ms_and_us():
    ms = {int(T.timestamp()) // 60, int(T.timestamp()) // 60 + 1}  # realistické časy (µs > 1e14)
    assert c.open_minutes(_zip(ms)) == ms
    assert c.open_minutes(_zip(ms, micro=True)) == ms


def test_open_minutes_rejects_non_numeric_row_after_header():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "open_time,open\n1741597200000,1\nGARBAGE,1\n")
    with pytest.raises(ValueError):
        c.open_minutes(buf.getvalue())


def test_verify_checksum():
    z = _zip({1})
    good = (hashlib.sha256(z).hexdigest() + "  x.zip").encode()
    assert c.verify_checksum(z, good) == hashlib.sha256(z).hexdigest()
    with pytest.raises(ValueError):
        c.verify_checksum(z, ("0" * 64).encode())
    with pytest.raises(ValueError):
        c.verify_checksum(z, b"")


class FakeNet:
    """Syntetický svět: 1 spotový článek se 2 tokeny, 1 margin článek, 1 nečitelný spotový titulek."""

    def __init__(self, corrupt_checksum=False, cms_status=200, perp_alias=False):
        self.corrupt, self.cms_status, self.alias = corrupt_checksum, cms_status, perp_alias
        self.files = {}
        full = _minutes(T - timedelta(days=7), T + timedelta(days=15))
        for tok in ("AAA", "BBB"):
            sym = ("1000" if (alias := perp_alias and tok == "BBB") else "") + f"{tok}USDT"
            for d in c.days(T):
                day0 = datetime(d.year, d.month, d.day, tzinfo=UTC)
                mins = {m for m in full if day0.timestamp() // 60 <= m < (day0 + timedelta(days=1)).timestamp() // 60}
                url = f"{c.VISION}/daily/klines/{sym}/1m/{sym}-1m-{d.isoformat()}.zip"
                z = _zip(mins)
                self.files[url] = z
                self.files[url + ".CHECKSUM"] = (("0" * 64) if corrupt_checksum else hashlib.sha256(z).hexdigest()).encode()
            for m in (2, 3):
                url = f"{c.VISION}/monthly/fundingRate/{sym}/{sym}-fundingRate-2025-{m:02d}.zip"
                self.files[url] = b"f"
                self.files[url + ".CHECKSUM"] = hashlib.sha256(b"f").hexdigest().encode()
            del alias

    def __call__(self, url):
        if url.startswith("https://www.binance.com/bapi"):
            if self.cms_status != 200:
                return self.cms_status, b""
            page = int(url.split("pageNo=")[1].split("&")[0])
            arts = [] if page > 1 else [
                {"code": CODE, "title": "Binance Will Delist AAA, BBB on 2025-03-20",
                 "releaseDate": int(T.timestamp() * 1000)},
                {"code": "c" * 32, "title": "Binance Margin Will Delist AAA/BTC", "releaseDate": int(T.timestamp() * 1000)},
                {"code": "d" * 32, "title": "Binance Will Delist 2019-old", "releaseDate": 1_546_300_800_000}]
            return 200, json.dumps({"data": {"catalogs": [{"articles": arts}]}}).encode()
        if url.startswith("https://web.archive.org/cdx"):
            if "c-161" not in url:
                return 200, b""
            ts = (T + timedelta(hours=3)).strftime("%Y%m%d%H%M%S")
            return 200, json.dumps([["timestamp", "original", "statuscode", "digest"],
                                    [ts, "https://www.binance.com/en/support/announcement/c-161", "200", "D"]]).encode()
        if url.startswith("https://web.archive.org/web/"):
            return 200, ('<a href="/en/support/announcement/x-' + CODE + '">').encode()
        if url in self.files:
            return 200, self.files[url]
        return 404, b""


def test_collect_end_to_end_synthetic(tmp_path):
    rows, man = c.collect(FakeNet())
    spot = [r for r in rows if r["event_type"] == "spot_delist"]
    assert [r["token"] for r in spot] == ["AAA", "BBB"]
    assert all(r["pit_ok"] and r["perp_ok"] and r["coverage_ok"] for r in spot)
    assert man["gate"]["eligible_events"] == 2 and man["gate"]["independent_articles"] == 1
    assert man["verdict"] == "DATA_NO_GO"          # 2 < 60 — brána beze změny
    assert man["returns_computed"] is False
    assert man["articles_in_window"] == 2           # článek z 2019 mimo okno
    assert any(r["event_type"] == "margin_delist" for r in rows)
    out = c.write_outputs(rows, man, tmp_path)
    assert (tmp_path / "events.csv").read_text().splitlines()[0].startswith("article_id,token")
    assert len(out["events_csv_sha256"]) == 64


def test_collect_perp_alias_recorded():
    rows, _ = c.collect(FakeNet(perp_alias=True))
    bbb = next(r for r in rows if r["token"] == "BBB")
    assert bbb["perp_symbol"] == "1000BBBUSDT" and bbb["token"] == "BBB"


def test_collect_bad_checksum_fails_closed():
    rows, man = c.collect(FakeNet(corrupt_checksum=True))
    assert not any(r.get("coverage_ok") for r in rows)
    assert man["gate"]["eligible_events"] == 0


def test_collect_cms_blocked_is_no_go():
    rows, man = c.collect(FakeNet(cms_status=451))
    assert rows == [] and man["verdict"] == "DATA_NO_GO" and "451" in man["enumeration_error"]


def test_unparsed_share_forces_no_go(monkeypatch):
    monkeypatch.setattr(c, "MAX_UNPARSED_SHARE", -1.0)
    _, man = c.collect(FakeNet())
    assert man["verdict"] == "DATA_NO_GO"


def test_single_bad_checksum_day_fails_closed_even_if_coverage_high():
    net = FakeNet()
    d = (T + timedelta(days=10)).date().isoformat()
    net.files[f"{c.VISION}/daily/klines/AAAUSDT/1m/AAAUSDT-1m-{d}.zip.CHECKSUM"] = b"0" * 64
    rows, _ = c.collect(net)
    aaa = next(r for r in rows if r["token"] == "AAA")
    assert aaa["checksum_ok"] is False and aaa["coverage_ok"] is False
    assert next(r for r in rows if r["token"] == "BBB")["coverage_ok"] is True


def test_missing_funding_month_fails_coverage():
    net = FakeNet()
    del net.files[f"{c.VISION}/monthly/fundingRate/BBBUSDT/BBBUSDT-fundingRate-2025-03.zip"]
    rows, _ = c.collect(net)
    bbb = next(r for r in rows if r["token"] == "BBB")
    assert bbb["funding_ok"] is False and bbb["coverage_ok"] is False


def test_coverage_denominator_not_truncated_at_last_archive_minute():
    """A 2-day archive must not appear 100% covered in the 21-day frozen window."""
    truncated = _minutes(T - timedelta(days=7), T + timedelta(days=2))
    perp_ok, coverage_ok, info = c.perp_and_coverage(truncated, T)
    assert perp_ok is True  # entry hour and 24h post-entry are present
    assert coverage_ok is False
    assert 0.42 < info["minute_coverage"] < 0.44


def test_coverage_full_window_passes_and_empty_fails():
    full = _minutes(T - timedelta(days=7), T + timedelta(days=14))
    assert c.perp_and_coverage(full, T)[1] is True
    assert c.perp_and_coverage(set(), T)[1] is False


def test_coverage_one_missing_day_below_threshold():
    full = _minutes(T - timedelta(days=7), T + timedelta(days=14))
    missing_day = _minutes(T + timedelta(days=12), T + timedelta(days=13))
    assert c.perp_and_coverage(full - missing_day, T)[1] is True  # 20/21 >= .95
    missing_two = missing_day | _minutes(T + timedelta(days=11), T + timedelta(days=12))
    assert c.perp_and_coverage(full - missing_two, T)[1] is False
