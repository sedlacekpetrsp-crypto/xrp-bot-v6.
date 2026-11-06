"""Společná rozhodovací brána (kolo 9, Q1 + Q3): kombinace platných a neplatných kritérií. Není důkaz ziskovosti."""
import pytest

from tools.research import decision_gate as dg

A = ("A1_sharpe_dd", "A2_trades_ge_30", "A3_x2_pf_profit", "A4_wo_top3", "A5_final_x2")
B = ("B1_val_x2_profit_pf", "B2_dd_le_0_6_bh", "B3_final_x2_profit", "B4_val_wo_top3", "B5_trades_ge_20",
     "B6_tuning_x1_profit")
CLEAN = {"dsr": 0.99, "dsr_defects": {}, "neighbors": {"n1": (5.0, {}), "n2": (3.0, {})},
         "wf": {y: (1.0, 10, {}) for y in (2021, 2022, 2023, 2024)}}


def tr(fail=()):
    return {c: c not in fail for c in A}, {c: c not in fail for c in B}


def v(fail=(), ctx=CLEAN, **kw):
    a, b = tr(fail)
    return dg.decide(a, b, ctx, **kw)


def test_clean_pass_is_candidate_and_any_defect_blocks():
    assert v()[0] == "KANDIDÁT NA FORWARD PAPER"
    assert v(strat_bad=("final_test",))[0].startswith("NEROZHODNUTO")
    assert v(bench_bad=("validation",))[0].startswith("NEROZHODNUTO")
    assert v(blocking={"x": 1})[0].startswith("NEROZHODNUTO")
    assert v(candidate_extra_ok=False, candidate_extra_reason="latence")[0].startswith("NEROZHODNUTO")


def test_clean_rejection():
    assert v(fail=("A2_trades_ge_30", "B3_final_x2_profit"))[0] == "ZAMÍTNUTO"


@pytest.mark.parametrize("fail,strat_bad,bench_bad,expected", [
    # strategie vadná ve validaci: A2/B1 závisí na validaci ⇒ neznámé
    (("A2_trades_ge_30", "B1_val_x2_profit_pf"), ("validation",), (), "NEROZHODNUTO"),
    # A5 a B3 počítají jen z finálního testu ⇒ platné zamítnutí i při vadné validaci
    (("A5_final_x2", "B3_final_x2_profit"), ("validation",), (), "ZAMÍTNUTO"),
    # kombinace: A má platný důvod (A5), B jen neznámý (B5 závisí i na validaci) ⇒ NEROZHODNUTO
    (("A2_trades_ge_30", "A5_final_x2", "B5_trades_ge_20"), ("validation",), (), "NEROZHODNUTO"),
    # B6 jen z ladění: vada v ladění ⇒ neznámé; B3 platné ⇒ B zamítnuta; A2 platné ⇒ ZAMÍTNUTO
    (("A2_trades_ge_30", "B3_final_x2_profit", "B6_tuning_x1_profit"), ("tuning",), (), "ZAMÍTNUTO"),
    # benchmark i strategie vadné v různých obdobích
    (("A1_sharpe_dd", "B2_dd_le_0_6_bh"), ("final_test",), ("validation",), "NEROZHODNUTO"),
    (("A4_wo_top3", "B4_val_wo_top3"), ("final_test",), ("final_test",), "ZAMÍTNUTO"),
])
def test_combinations_of_valid_and_invalid_criteria(fail, strat_bad, bench_bad, expected):
    assert v(fail=fail, strat_bad=strat_bad, bench_bad=bench_bad)[0].startswith(expected)


def test_global_defects_block_both_acceptance_and_rejection():
    assert v(global_defects={"P65_H15:legs_with_price_fallback": 1})[0].startswith("NEROZHODNUTO — globální")
    assert v(fail=A + B, global_defects={"x": 1})[0].startswith("NEROZHODNUTO — globální")
    bad_dsr = {**CLEAN, "dsr": 0.1}
    assert v(ctx=bad_dsr, global_defects={"x": 1})[0].startswith("NEROZHODNUTO")


def test_unmapped_criterion_is_conservative():
    assert dg.decide({"NEW": False}, {"NEW2": False}, CLEAN, strat_bad=("tuning",))[0].startswith("NEROZHODNUTO")
    assert dg.decide({"NEW": False}, {"NEW2": False}, CLEAN)[0] == "ZAMÍTNUTO"


def test_robustness_failure_on_clean_data_rejects_tainted_or_unevaluable_does_not():
    assert v(ctx={**CLEAN, "dsr": 0.5})[0] == "ZAMÍTNUTO"                           # skutečné statistické selhání
    assert v(ctx={**CLEAN, "dsr": 0.5, "dsr_defects": {"x": 1}})[0].startswith("NEROZHODNUTO")
    assert v(ctx={**CLEAN, "dsr": None})[0].startswith("NEROZHODNUTO")             # nehodnotitelné ≠ selhání
    assert v(fail=("A2_trades_ge_30", "B3_final_x2_profit"), ctx={**CLEAN, "dsr": None})[0] == "ZAMÍTNUTO"
    nb_bad = {**CLEAN, "neighbors": {"n1": (-1.0, {"legs_with_price_fallback": 2}), "n2": (3.0, {})}}
    assert dg.robustness_status(nb_bad)["neighbors_val_x2_profit"] == "fail_unknown"
    nb_real = {**CLEAN, "neighbors": {"n1": (-1.0, {"x": 1}), "n2": (-2.0, {})}}
    assert dg.robustness_status(nb_real)["neighbors_val_x2_profit"] == "fail"


@pytest.mark.parametrize("wf,expected", [
    ({1: (1, 5, {}), 2: (1, 5, {}), 3: (1, 5, {}), 4: (-1, 5, {})}, "pass"),
    ({1: (1, 5, {}), 2: (1, 5, {}), 3: (1, 5, {"gap": 1}), 4: (-1, 5, {})}, "pass_tainted"),
    ({1: (1, 5, {}), 2: (1, 5, {}), 3: (-1, 5, {}), 4: (-1, 5, {})}, "fail"),
    ({1: (1, 5, {}), 2: (1, 5, {}), 3: (-1, 5, {"gap": 1}), 4: (-1, 5, {})}, "fail_unknown"),
    ({1: (1, 5, {}), 2: (1, 5, {}), 3: (0, 0, {}), 4: (-1, 5, {})}, "fail_unknown"),  # fold bez obchodů = nehodnotitelný
    ({1: (1, 5, {}), 2: (-1, 5, {}), 3: (-1, 5, {"gap": 1}), 4: (-1, 5, {})}, "fail"),  # ani vadný fold by nestačil
])
def test_walk_forward_fold_integrity(wf, expected):
    assert dg.robustness_status({**CLEAN, "wf": wf})["walk_forward_ge_3_of_4"] == expected


def test_no_threshold_or_exclusion_parameters_exist():
    import inspect
    src = inspect.getsource(dg)
    for word in ("threshold", "exclude", "drop_trades", "recompute"):
        assert word not in src.lower()


def test_track_b_alone_cannot_grant_candidate_kolo10():
    a, b = tr(fail=("A2_trades_ge_30",))  # A neprošla na čistých datech, B prošla
    verdict, d = dg.decide(a, b, CLEAN)
    assert verdict.startswith("NEROZHODNUTO") and "stopa B" in verdict and d["track_b"] == "pass"
    a, b = tr(fail=("B3_final_x2_profit",))  # A prošla ⇒ kandidát možný
    assert dg.decide(a, b, CLEAN)[0] == "KANDIDÁT NA FORWARD PAPER"
    assert dg.TRACK_B_CAN_GRANT_CANDIDATE is False
