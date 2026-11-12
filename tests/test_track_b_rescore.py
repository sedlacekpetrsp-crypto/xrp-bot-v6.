import copy

from tools.research.track_b_rescore import score


def _m(net, ret, dd, trades, pf=1.5, wo3=100.0):
    return {"net_pnl": net, "return_pct": ret, "max_drawdown_pct": dd, "trades": trades,
            "profit_factor": pf, "net_without_top3": wo3}


def _base():
    blocks = {f"{p}/x{c}": _m(500, 5, 10, 15) for p in ("tuning", "validation", "final_test") for c in (1, 2, 3)}
    bh = {k: _m(1000, 10, 50, 0) for k in blocks}
    return {"strategy": blocks, "buy_hold": bh}


def test_all_pass():
    r = score(_base())
    assert r["passed"] and r["failed"] == []


def test_each_criterion_fails():
    cases = {
        "B1": lambda d: d["strategy"]["validation/x2"].update(profit_factor=1.1),
        "B2": lambda d: d["strategy"]["final_test/x1"].update(max_drawdown_pct=31),
        "B3": lambda d: d["strategy"]["final_test/x2"].update(net_pnl=-1),
        "B4": lambda d: d["strategy"]["validation/x1"].update(net_without_top3=-1),
        "B5": lambda d: (d["strategy"]["validation/x1"].update(trades=10), d["strategy"]["final_test/x1"].update(trades=9)),
        "B6": lambda d: d["strategy"]["tuning/x1"].update(net_pnl=-0.01),
    }
    for key, mutate in cases.items():
        d = copy.deepcopy(_base())
        mutate(d)
        assert score(d)["failed"] == [key], key


def test_dd_boundary_inclusive():
    d = _base()
    d["strategy"]["validation/x1"]["max_drawdown_pct"] = 30.0  # = 0,6 × 50
    assert score(d)["checks"]["B2_dd_le_0_6_bh_val_and_final"]


def test_nested_basket_benchmark():
    d = _base()
    d["buy_hold"] = {k: {"basket_50_50": v, "BTC_only": _m(1, 1, 5, 0)} for k, v in d["buy_hold"].items()}
    assert score(d)["passed"]  # DD limit z koše (50 %), ne z BTC_only (5 %)


def test_grid_uses_chosen_variant():
    base = _base()
    grid = {}
    for k, v in base["strategy"].items():
        grid[f"A/{k}"] = v
        bad = dict(v, net_pnl=-5)
        grid[f"B/{k}"] = bad
    r = score({"grid": grid, "buy_hold": base["buy_hold"], "verdict": {"chosen": "A"}})
    assert r["passed"]
