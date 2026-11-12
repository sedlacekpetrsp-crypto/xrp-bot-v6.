from research.k3_funding_audit.audit import DAY_MS, H_MS
from research.k3_funding_audit.step0b import gate, longest_run, month_list, on_hour


def test_longest_run_full_and_short():
    ts = [i * H_MS for i in range(24 * 600)]
    st, en, cov = longest_run(ts)
    assert st == 0 and cov == 1.0 and (en - st) / DAY_MS > 599


def test_longest_run_old_island_excluded():
    old = [i * H_MS for i in range(10)]
    recent = [i * H_MS for i in range(24 * 300, 24 * 500)]
    st, en, cov = longest_run(old + recent)
    assert st == 24 * 300 * H_MS and cov == 1.0


def test_on_hour_and_months():
    assert on_hour([H_MS, 2 * H_MS + 30_000, 3 * H_MS + 600_000]) == 2 / 3
    ms = month_list(0, 95 * DAY_MS)  # 1970-01-01 .. 1970-04-06
    assert ms == ["1970-01", "1970-02", "1970-03"]


def test_gate_208_days_fails():
    now = 1000 * DAY_MS
    r = {"hl_days": 208, "hl_cov": 1.0, "hl_last": now, "bn_month_share": 1.0, "hl_onhour": 1.0}
    assert not gate(r, now)
    r["hl_days"] = 600
    assert gate(r, now)
    r["hl_last"] = now - 3 * DAY_MS
    assert not gate(r, now)
