import importlib.util
import pathlib

import numpy as np

_p = pathlib.Path(__file__).resolve().parents[1] / "research/g1_power_preflight/g1_bss_power.py"


def _mod():
    spec = importlib.util.spec_from_file_location("g1_bss_power", _p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_episode_placement_non_overlapping_with_gap():
    m = _mod()
    rng = np.random.default_rng(1)
    for _ in range(50):
        y, starts = m.place_episodes(rng, m.N_DAYS, 21, 14)
        assert y.sum() == 21 * 14
        assert np.all(np.diff(starts) >= 14 + 14)


def test_block_bootstrap_identity_when_model_equals_reference():
    m = _mod()
    rng = np.random.default_rng(2)
    br = rng.random(300)
    assert np.allclose(m.block_bootstrap_bss(br.copy(), br, 14, 50, rng), 0.0)


def test_null_skill_never_go_and_power_monotone():
    m = _mod()
    rng = np.random.default_rng(3)
    null = m.simulate(0.0, 21, 8, sims=20, B=200, rng=rng)
    strong = m.simulate(3.0, 21, 8, sims=20, B=200, rng=rng)
    assert null["P_GO"] == 0.0
    assert strong["P_GO"] > null["P_GO"]
    assert strong["true_bss_pooled"] > 0.5
