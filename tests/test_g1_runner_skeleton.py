"""Synthetic, data-free tests for the G1 runner skeleton (B4 evaluation half)."""
import math
import random

import numpy as np
import pytest

from research.g1_power_preflight import g1_runner_skeleton as r

SHA = "a" * 40


def _fold(name, n, seed, *, signal, episodes=4, base=0.08, ref="M0"):
    """Calibrated candidate: latent logit risk with dispersion ``signal``; y ~ Bernoulli(q)."""
    rng = random.Random(seed)
    b0 = math.log(base / (1 - base))
    q = [1 / (1 + math.exp(-(b0 + signal * rng.gauss(0, 1)))) for _ in range(n)]
    y = [1 if rng.random() < qi else 0 for qi in q]
    if sum(y) == 0:
        y[n // 2] = 1
    pc = [min(max(qi, 0.001), 0.999) for qi in q]
    pr = [base] * n
    return {"name": name, "reference_name": ref, "reference_selected_before_test": True,
            "y": y, "p_candidate": pc, "p_reference": pr, "grouped_positive_episodes": episodes}


def _folds(signal, k=5, n=250, episodes=5):
    return [_fold(f"F{2022 + i}", n, 100 + i, signal=signal, episodes=episodes) for i in range(k)]


def _run(folds, **kw):
    kw.setdefault("replicates", 300)
    return r.evaluate_g1(folds, g0_ok=True, pregate_status="PASS", **kw)


def test_guard_accepts_exact_and_rejects_mismatch():
    r.check_one_shot_guard(SHA, SHA, f"G1-ONE-SHOT-{SHA}")
    with pytest.raises(r.InvalidRun):
        r.check_one_shot_guard("b" * 40, SHA, f"G1-ONE-SHOT-{SHA}")
    with pytest.raises(r.InvalidRun):
        r.check_one_shot_guard(SHA, SHA, "G1-ONE-SHOT-abc")
    with pytest.raises(r.InvalidRun):
        r.check_one_shot_guard("abc", "abc", "G1-ONE-SHOT-abc")


def test_strong_signal_go_and_frozen_flag():
    res = _run(_folds(2.0))
    assert res["verdict"] == "GO", res
    assert res["frozen_config"] is False and "NON_FROZEN_CONFIG" in res["flags"]
    assert res["status"] == "SYNTHETIC_ONLY" and res["label"] == "EXPLORATORY_SCREEN"


def test_frozen_config_full_replicates_go():
    res = r.evaluate_g1(_folds(2.0), g0_ok=True, pregate_status="PASS")
    assert res["frozen_config"] is True and res["flags"] == [] and res["verdict"] == "GO"


def test_null_candidate_never_go():
    fs = _folds(0.0)
    for f in fs:  # candidate = reference + noise -> BSS <= 0
        rng = random.Random(f["name"])
        f["p_candidate"] = [min(max(p + rng.gauss(0, 0.03), 0.001), 0.999) for p in f["p_reference"]]
    res = _run(fs)
    assert res["verdict"] == "NO-GO" and res["pooled_bss"] <= 0


def test_pooled_bss_is_ratio_of_sums_not_mean_of_folds():
    fs = [_fold("A", 60, 1, signal=2.0, episodes=7), _fold("B", 200, 2, signal=0.5, episodes=7),
          _fold("C", 60, 3, signal=1.0, episodes=7)]
    res = _run(fs)
    lc = sum((p - t) ** 2 for f in fs for p, t in zip(f["p_candidate"], f["y"]))
    lr = sum((p - t) ** 2 for f in fs for p, t in zip(f["p_reference"], f["y"]))
    assert math.isclose(res["pooled_bss"], 1 - lc / lr, rel_tol=1e-12)
    mean_fold = sum(pf["bss"] for pf in res["per_fold"]) / 3
    assert not math.isclose(res["pooled_bss"], mean_fold, rel_tol=1e-6)


@pytest.mark.parametrize("mutate,needle", [
    (lambda f: f["p_candidate"].__setitem__(3, float("nan")), "non-finite"),
    (lambda f: f["p_reference"].__setitem__(0, 0.0), "(0,1)"),
    (lambda f: f.__setitem__("reference_selected_before_test", False), "ex-ante"),
    (lambda f: f.__setitem__("reference_name", "B3"), "reference must"),
    (lambda f: f.__setitem__("y", f["y"][:-1]), "length"),
    (lambda f: f["y"].__setitem__(0, True), "0/1"),
    (lambda f: f["p_candidate"].__setitem__(0, 1.5), "outside"),
])
def test_invalid_inputs_fail_closed(mutate, needle):
    fs = _folds(2.0)
    mutate(fs[1])
    res = _run(fs)
    assert res["verdict"] == "INVALID_RUN" and needle in res["reason"]
    assert "pooled_bss" not in res


def test_fold_shorter_than_two_max_blocks_invalid():
    fs = _folds(2.0)
    fs[0] = _fold("short", 55, 9, signal=2.0, episodes=5)
    res = _run(fs)
    assert res["verdict"] == "INVALID_RUN" and "2*28" in res["reason"]


def test_g0_and_pregate_stop_before_metrics():
    assert r.evaluate_g1(_folds(2.0), g0_ok=False, pregate_status="PASS")["verdict"] == "INVALID_RUN"
    res = r.evaluate_g1(_folds(2.0), g0_ok=True, pregate_status="POWER_NO_GO")
    assert res["verdict"] == "POWER_NO_GO" and "pooled_bss" not in res


def test_low_n_and_low_folds():
    assert _run(_folds(2.0, episodes=3, k=5))["verdict"] == "INCONCLUSIVE_LOW_N"  # 15 < 20
    fs = _folds(2.0, k=5, episodes=10)
    for f in fs[2:]:
        f["grouped_positive_episodes"] = 2   # only 2 evaluable folds, total 26
    res = _run(fs)
    assert res["verdict"] == "INCONCLUSIVE_LOW_FOLDS" and "pooled_bss" not in res


def test_two_thirds_fold_rule_blocks_go():
    # 3 evaluable folds, 2 with negative BSS -> GO impossible even if pooled > 0.05
    fs = [_fold("A", 300, 1, signal=2.5, episodes=7), _fold("B", 60, 2, signal=0.0, episodes=7),
          _fold("C", 60, 3, signal=0.0, episodes=7)]
    for f in fs[1:]:
        f["p_candidate"] = [0.3] * len(f["y"])
    res = _run(fs)
    assert res["required_positive_folds"] == 2
    assert res["positive_evaluable_folds"] == 1
    assert res["verdict"] != "GO"


def test_numpy_inputs_accepted_and_deterministic():
    fs = _folds(2.0)
    for f in fs:
        f["p_candidate"] = list(np.asarray(f["p_candidate"], dtype=np.float64))
        f["y"] = list(np.asarray(f["y"], dtype=np.int64))
    a, b = _run(fs), _run(fs)
    assert a["verdict"] == "GO" and a["ci95"] == b["ci95"]


def test_calibration_slope_recovers_known_slope():
    rng = random.Random(7)
    xs = [rng.uniform(-3, 1) for _ in range(20000)]
    p = [1 / (1 + math.exp(-x)) for x in xs]
    y = [1 if rng.random() < 1 / (1 + math.exp(-(0.5 * x))) else 0 for x in xs]
    assert abs(r.calibration_slope(y, p) - 0.5) < 0.06
    with pytest.raises(r.InvalidRun):
        r.calibration_slope([0] * 10, [0.1] * 10)


def test_overconfident_candidate_fails_calibration_gate():
    fs = _folds(2.0)
    res_ok = _run(fs)
    for f in fs:  # push probabilities to extremes -> slope << 0.5 or BSS collapses
        f["p_candidate"] = [0.999 if p > 0.3 else 0.001 for p in f["p_candidate"]]
        f["y"][5] = 1 - f["y"][5]  # inject a confident miss per fold
    res = _run(fs)
    assert res_ok["verdict"] == "GO"
    assert res["verdict"] != "GO"


def test_constant_candidate_is_no_go_not_invalid():
    fs = _folds(2.0)
    for f in fs:
        f["p_candidate"] = list(f["p_reference"])
    res = _run(fs)
    assert res["verdict"] == "NO-GO" and res["pooled_bss"] == 0
    assert "CAL_SLOPE_UNDEFINED" in res["flags"] and res["calibration_slope"] is None


def test_separating_candidate_cannot_go_without_slope():
    fs = _folds(2.0)
    for f in fs:
        f["p_candidate"] = [0.9 if t else 0.02 for t in f["y"]]
    res = _run(fs)
    assert res["pooled_bss"] > 0.05 and res["verdict"] == "INCONCLUSIVE"
    assert "CAL_SLOPE_UNDEFINED" in res["flags"]
