from research.k3_funding_audit.audit import (H_MS, DAY_MS, coverage, map_symbol, months, on_hour_share,
                                             pair_overlap, qualifies)


def test_map_symbol():
    assert map_symbol("XRPUSDT", "bybit") == "XRPUSDT"
    assert map_symbol("XRPUSDT", "okx") == "XRP-USDT-SWAP"
    assert map_symbol("XRPUSDT", "hyperliquid") == "XRP"
    assert map_symbol("1000PEPEUSDT", "hyperliquid") == "kPEPE"
    assert map_symbol("BTCBUSD", "okx") is None


def test_coverage_full_and_gap():
    ts = [i * 8 * H_MS for i in range(100)]
    assert coverage(ts)["coverage"] == 1.0
    gap = ts[:50] + ts[55:]
    c = coverage(gap)
    assert c["missing"] == 5 and abs(c["coverage"] - 95 / 100) < 1e-9


def test_coverage_interval_change_not_a_gap():
    a = [i * 8 * H_MS for i in range(60)]
    b = [a[-1] + (i + 1) * 4 * H_MS for i in range(60)]
    c = coverage(a + b)
    assert c["missing"] == 0 and c["interval_changes"] >= 1


def test_pair_overlap_and_gate():
    ta = [i * 8 * H_MS for i in range(3 * 600)]          # 600 dní
    tb = [i * H_MS for i in range(24 * 100, 24 * 700)]   # dny 100–700
    o = pair_overlap(ta, tb)
    assert abs(o["days"] - (ta[-1] - 100 * DAY_MS) / DAY_MS) < 0.2
    assert o["cov_a"] == 1.0 and o["cov_b"] == 1.0
    assert not qualifies(o)  # ~500 dní < 548
    assert qualifies({"days": 600, "cov_a": 0.96, "cov_b": 0.95})
    assert not qualifies({"days": 600, "cov_a": 0.94, "cov_b": 0.99})


def test_months_and_on_hour():
    assert list(months("2023-11-15", "2024-02-01")) == ["2023-11", "2023-12", "2024-01", "2024-02"]
    assert on_hour_share([0, H_MS + 5_000, H_MS // 2]) == 2 / 3
