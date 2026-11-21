"""Nezávislá review (Claude) modulu research/episode_power_preflight.py.

Kolo 1 (dialog 0430) @ e3507d8: R1 MAJOR, R2-R5 MINOR jako strict xfail.
Kolo 2 (dialog 0432) @ 65e4d6c/a790382: R1, R2, R4, R5 opraveny -> xfail odstraněn;
R3 vyřešen kompromisem (varování N_eff < 30, bez t-korekce) -> zbytková mez zůstává jako strict xfail.
Jen syntetické vstupy, žádná tržní data, žádný backtest.
"""
import inspect
from statistics import NormalDist

import pytest

from research.episode_power_preflight import PowerScreen

BASE = {"n_episodes": 25, "sigma_return": .02, "roundtrip_fee": .0019,
        "roundtrip_slippage": .0004, "design_effect": 1.0}
Z = NormalDist().inv_cdf(.975) + NormalDist().inv_cdf(.80)


def test_r1_design_effect_mandatory_and_equivalent_to_clusters():
    p = inspect.signature(PowerScreen).parameters["design_effect"]
    assert p.default is inspect.Parameter.empty
    # 100 epizod v 25 shlucích po 4 s ICC 1.0 = 25 nezávislých informací
    r100 = PowerScreen(**(BASE | {"n_episodes": 100, "design_effect": 4.0})).evaluate()
    r25 = PowerScreen(**BASE).evaluate()
    assert r100["n_effective"] == pytest.approx(25)
    assert r100["minimum_detectable_gross_return"] == pytest.approx(r25["minimum_detectable_gross_return"])


def test_r1_icc_formula_reproduced():
    # DEFF = 1 + (m-1)*ICC, m=5, ICC=0.25 -> 2.0; 300 epizod -> N_eff 150
    r = PowerScreen(**(BASE | {"n_episodes": 300, "design_effect": 1 + 4 * .25})).evaluate()
    assert r["n_effective"] == pytest.approx(150)
    assert r["minimum_detectable_gross_return"] == pytest.approx(Z * .02 / 150 ** .5)


def test_r1_bool_and_subunit_deff_rejected():
    for bad in (True, .99, 0, float("inf")):
        with pytest.raises(ValueError):
            PowerScreen(**(BASE | {"design_effect": bad})).evaluate()


def test_r2_no_meaningless_net_key():
    r = PowerScreen(**(BASE | {"n_episodes": 10_000})).evaluate()
    assert "minimum_detectable_net_return" not in r


def test_r3_small_sample_flagged():
    assert PowerScreen(**BASE).evaluate()["small_sample_warning"] is True
    assert PowerScreen(**(BASE | {"n_episodes": 60, "design_effect": 2.0})).evaluate()["small_sample_warning"] is False
    assert PowerScreen(**(BASE | {"n_episodes": 59, "design_effect": 2.0})).evaluate()["small_sample_warning"] is True


@pytest.mark.xfail(strict=True, reason="R3 zbytková mez (přijatý kompromis): bez t-korekce je MDE při N_eff=25 podhodnoceno o ~4 %; "
                                       "volající musí při small_sample_warning použít t/simulaci")
def test_r3_residual_no_t_correction():
    r = PowerScreen(**BASE).evaluate()
    # t_{0.975,24} + t_{0.80,24} = 2.9208 (scipy), normal 2.8016
    assert r["minimum_detectable_gross_return"] >= 2.92 * .02 / 5 - 1e-6


def test_r4_bonferroni_multiplicity():
    r = PowerScreen(**(BASE | {"multiplicity": 10})).evaluate()
    z = NormalDist().inv_cdf(1 - .05 / 2 / 10) + NormalDist().inv_cdf(.80)
    assert r["minimum_detectable_gross_return"] == pytest.approx(z * .02 / 5, rel=1e-9)


def test_r5_three_x_cost_gate_reported():
    r = PowerScreen(**BASE).evaluate()
    assert r["required_gross_return_for_gate"] == pytest.approx(max(Z * .02 / 5 + .0023, 3 * .0023))
    big = PowerScreen(**(BASE | {"n_episodes": 1_000_000})).evaluate()
    assert big["required_gross_return_for_gate"] == pytest.approx(3 * .0023)


def test_zero_cost_no_division():
    r = PowerScreen(**(BASE | {"roundtrip_fee": 0, "roundtrip_slippage": 0})).evaluate()
    assert r["required_gross_return_for_gate"] == pytest.approx(r["minimum_detectable_gross_return"])


def test_q11b_threshold_consistent():
    """N_eff* = ((z_a+z_b)*sigma/(2*cost))^2 je přesně bod, kde MDE + cost = 3*cost."""
    cost, sigma = .0023, .02
    n_star = (Z * sigma / (2 * cost)) ** 2
    r = PowerScreen(**(BASE | {"n_episodes": round(n_star * 1000), "design_effect": 1000.0})).evaluate()
    assert r["required_gross_return_for_net_detection"] == pytest.approx(3 * cost, rel=1e-3)


def test_known_mde_reproduced_independently():
    r = PowerScreen(**BASE).evaluate()
    assert r["minimum_detectable_gross_return"] == pytest.approx(Z * .02 / 5, rel=1e-9)
    assert r["required_gross_return_for_net_detection"] == pytest.approx(r["minimum_detectable_gross_return"] + .0023)
