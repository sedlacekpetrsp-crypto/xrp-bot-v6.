"""Nezávislá review (Claude, dialog 0430) modulu research/episode_power_preflight.py @ e3507d8.

Strict xfail = doložený nález; po opravě ChatGPT test přejde na XPASS -> strict selže -> odstranit xfail.
Jen syntetické vstupy, žádná tržní data, žádný backtest.
"""
import inspect
from statistics import NormalDist

import pytest

from research.episode_power_preflight import PowerScreen

BASE = {"n_episodes": 25, "sigma_return": .02, "roundtrip_fee": .0019, "roundtrip_slippage": .0004}


@pytest.mark.xfail(strict=True, reason="R1 MAJOR: chybí efektivní N (překryv/shlukování epizod) - surové N dává optimistické MDE")
def test_r1_effective_n_design_effect():
    params = inspect.signature(PowerScreen).parameters
    assert "design_effect" in params or "n_effective" in params
    # 100 epizod v 25 shlucích po 4 s ICC 1.0 = 25 nezávislých informací
    r100 = PowerScreen(**(BASE | {"n_episodes": 100, "design_effect": 4.0})).evaluate()
    r25 = PowerScreen(**BASE).evaluate()
    assert r100["minimum_detectable_gross_return"] == pytest.approx(r25["minimum_detectable_gross_return"])


@pytest.mark.xfail(strict=True, reason="R2 MINOR: klíč minimum_detectable_net_return = MDE - náklad nemá statistický význam (může být záporný)")
def test_r2_no_meaningless_net_key():
    r = PowerScreen(**(BASE | {"n_episodes": 10_000})).evaluate()
    assert "minimum_detectable_net_return" not in r


@pytest.mark.xfail(strict=True, reason="R3 MINOR: normální kvantily místo t při malém N podhodnocují MDE (n=25 o ~4 %)")
def test_r3_small_sample_t_correction():
    r = PowerScreen(**BASE).evaluate()
    # t_{0.975,24} + t_{0.80,24} = 2.9208 (scipy), normal 2.8016
    assert r["minimum_detectable_gross_return"] >= 2.92 * .02 / 5 - 1e-6


@pytest.mark.xfail(strict=True, reason="R4 MINOR: multiplicity>1 jen ValueError; Bonferroni kvantil lze spočítat bez předregistrovaného čísla")
def test_r4_bonferroni_multiplicity():
    r = PowerScreen(**(BASE | {"multiplicity": 10})).evaluate()
    z = NormalDist().inv_cdf(1 - .05 / 2 / 10) + .84
    assert r["minimum_detectable_gross_return"] == pytest.approx(z * .02 / 5, rel=1e-3)


@pytest.mark.xfail(strict=True, reason="R5 MINOR: výstup neobsahuje bránu rámce 'hrubá hrana >= 3x náklad' (STATE 2026-11-08 13:38)")
def test_r5_three_x_cost_gate_reported():
    r = PowerScreen(**BASE).evaluate()
    assert r["required_gross_return_for_gate"] == pytest.approx(max(.0112 + .0023, 3 * .0023))


def test_known_mde_reproduced_independently():
    z = NormalDist().inv_cdf(.975) + NormalDist().inv_cdf(.80)
    r = PowerScreen(**BASE).evaluate()
    assert r["minimum_detectable_gross_return"] == pytest.approx(z * .02 / 5, rel=2e-3)
    assert r["required_gross_return_for_net_detection"] == pytest.approx(r["minimum_detectable_gross_return"] + .0023)
