"""Synthetic tests only; never load market data."""
import pytest

from research.g1_power_preflight.g1_block_bootstrap import (
    paired_block_bss, percentile_interval,
)


def test_identical_losses_zero_skill():
    assert paired_block_bss([0.1, 0.2], [0.1, 0.2],
                            block_days=14, replicates=12, seed=2) == [0.0] * 12


def test_half_loss_constant_skill():
    result = paired_block_bss([0.1] * 7, [0.2] * 7,
                              block_days=3, replicates=20, seed=1)
    assert all(abs(x - 0.5) < 1e-12 for x in result)


def test_reproducible_and_seed_sensitive():
    args = ([0.1, 0.4, 0.2, 0.8], [0.3, 0.5, 0.7, 0.9])
    a = paired_block_bss(*args, block_days=2, replicates=20, seed=4)
    assert a == paired_block_bss(*args, block_days=2, replicates=20, seed=4)
    assert a != paired_block_bss(*args, block_days=2, replicates=20, seed=5)


def test_pairing_keeps_proportional_losses():
    assert all(abs(x - 0.75) < 1e-12 for x in paired_block_bss(
        [0.25, 0.5, 0.75], [1, 2, 3], block_days=2, replicates=20, seed=1))


@pytest.mark.parametrize("m,r", [([], []), ([1], []), ([1], [0]),
                                  ([float("nan")], [1]), ([-1], [1]),
                                  ([1], [float("inf")]), ([True], [1])])
def test_invalid_losses(m, r):
    with pytest.raises(ValueError):
        paired_block_bss(m, r, block_days=2, replicates=2, seed=1)


@pytest.mark.parametrize("block,reps,seed", [(0, 2, 1), (2, 0, 1),
                                              (True, 2, 1), (2, 2, True)])
def test_invalid_controls(block, reps, seed):
    with pytest.raises(ValueError):
        paired_block_bss([1], [2], block_days=block, replicates=reps, seed=seed)


def test_interval():
    assert percentile_interval([0, 10], alpha=0.2) == pytest.approx((1, 9))


def test_invalid_interval():
    with pytest.raises(ValueError):
        percentile_interval([])
