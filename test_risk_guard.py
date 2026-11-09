import pytest
import risk_guard as g

DAY = 1762646400000  # 2025-11-09 00:00 UTC (neděle)
H = 3600_000


def st(equity=10000., peak=10000., now=DAY + H, rg=None):
    return g.update(rg, equity, peak, now)


def test_normal_entry_full_risk():
    rg = st()
    assert g.check_entry(rg, 10000.) == (True, 1.0, "OK")


@pytest.mark.parametrize("equity,mult", [(9400., 0.5), (8900., 0.25)])
def test_drawdown_throttle(equity, mult):
    # equity a vrchol nastavíme tak, aby denní/týdenní limit nezasáhl (start dne = equity)
    rg = st(equity=equity, peak=10000.)
    ok, m, _ = g.check_entry(rg, equity)
    assert ok and m == mult


def test_drawdown_kill_is_sticky_until_owner_reset():
    rg = st(equity=8500., peak=10000.)
    assert g.check_entry(rg, 8500.)[0] is False and rg["killed"]
    rg = g.update(rg, 9900., 10000., DAY + 5 * 24 * H)   # i po zotavení zůstává vypnuto
    assert g.check_entry(rg, 9900.)[2].startswith("KILL")
    rg = g.reset_kill(rg, "vlastník", DAY + 6 * 24 * H)
    assert g.check_entry(rg, 9900.)[0] is True


def test_daily_limit_and_next_day_reset():
    rg = st(equity=10000.)
    rg = g.update(rg, 9840., 10000., DAY + 2 * H)
    assert g.check_entry(rg, 9840.)[2] == "DAILY_LOSS_LIMIT"
    rg = g.update(rg, 9840., 10000., DAY + 25 * H)       # nový den UTC
    assert g.check_entry(rg, 9840.)[0] is True


def test_weekly_limit():
    rg = st(equity=10000., now=DAY + 25 * H)              # pondělí = začátek týdne
    for d, eq in ((2, 9880.), (3, 9760.), (4, 9690.)):    # denně < 1,5 %, týdně ≥ 3 %
        rg = g.update(rg, eq, 10000., DAY + d * 24 * H + H)
    assert g.check_entry(rg, 9690.)[2] == "WEEKLY_LOSS_LIMIT"


def test_data_and_position_guards():
    rg = st()
    assert g.check_entry(rg, 10000., data_ok=False)[2] == "DATA_NOT_OK"
    assert g.check_entry(rg, 10000., open_positions=1)[2] == "MAX_POSITIONS"


def test_rejects_non_finite():
    with pytest.raises(ValueError):
        g.update(None, float("nan"), 10000., DAY)
