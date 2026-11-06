"""Kolo 10: statistická síla (syntetika, není důkaz ziskovosti)."""
import math

from tools.research import trade_stats as ts


def test_four_winning_trades_cannot_pass_sign_test_at_allocated_alpha():
    assert ts.sign_test_p([1, 2, 3, 4]) == 1 / 16          # reprodukce R9-7: 4 obchody, PF = ∞
    assert ts.sign_test_p([1, 2, 3, 4]) > 0.00625
    assert ts.sign_test_min_n(0.00625) == 8 and ts.sign_test_p([1] * 8) < 0.00625


def test_bootstrap_lower_bound_reproducible_and_wider_for_small_samples():
    big = [1.0 if i % 3 else -1.5 for i in range(300)]       # průměr > 0
    small = big[:6]
    lb_big = ts.stationary_bootstrap_ci(big)
    assert lb_big == ts.stationary_bootstrap_ci(big)          # pevné seed
    assert lb_big > 0 and ts.stationary_bootstrap_ci(small) < lb_big


def test_effective_n_drops_with_autocorrelation():
    iid = [(-1) ** i for i in range(200)]
    trend = [1.0] * 100 + [-1.0] * 100
    assert ts.effective_n(trend) < 50 < ts.effective_n(iid)


def test_concentration_and_required_n():
    c = ts.concentration([100, -10, -10, -10, 5])
    assert c["remove_best_to_flip"] == 1 and c["top_k_share_of_gains"] == 1.0
    assert ts.required_n(cv=10, alpha=0.00625) > ts.required_n(cv=2, alpha=0.00625)
    assert ts.required_n(cv=10, alpha=0.00625) == 1116  # ((z_0,99375 + z_0,8) · 10)²
