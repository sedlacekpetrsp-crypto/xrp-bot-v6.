"""Synthetic, data-free fold stratification regression tests."""
import pytest
from research.g1_power_preflight.g1_stratified_cbb import stratified_paired_bss


def test_constant_ratio_preserved_across_folds():
    folds = [([1.0] * 56, [2.0] * 56), ([3.0] * 56, [6.0] * 56)]
    assert all(abs(v - 0.5) < 1e-12 for v in stratified_paired_bss(
        folds, block_days=28, replicates=20, seed=11))


def test_seed_reproducibility():
    folds = [([0.1 + (i % 7) / 10 for i in range(60)],
              [0.3 + (i % 11) / 10 for i in range(60)])]
    a = stratified_paired_bss(folds, block_days=14, replicates=30, seed=1)
    assert a == stratified_paired_bss(folds, block_days=14, replicates=30, seed=1)
    assert a != stratified_paired_bss(folds, block_days=14, replicates=30, seed=2)


@pytest.mark.parametrize("folds,block", [
    ([], 14),
    ([([1.0] * 27, [2.0] * 27)], 14),
    ([([1.0] * 56, [2.0] * 55)], 28),
    ([([1.0] * 56, [0.0] * 56)], 28),
    ([([1.0] * 56, [float("nan")] * 56)], 28),
    ([([True] * 56, [2.0] * 56)], 28),
])
def test_fail_closed(folds, block):
    with pytest.raises(ValueError):
        stratified_paired_bss(folds, block_days=block, replicates=5, seed=1)


def test_folds_not_crossed_and_pooled_weighted_by_rows():
    folds = [([0.0] * 56, [1.0] * 56), ([2.0] * 112, [1.0] * 112)]
    vals = stratified_paired_bss(folds, block_days=28, replicates=10, seed=3)
    assert all(v == pytest.approx(-1 / 3) for v in vals)


@pytest.mark.parametrize("block,reps,seed", [(0, 10, 1), (14, 0, 1),
                                              (True, 10, 1), (14, 10, True)])
def test_bad_controls(block, reps, seed):
    with pytest.raises(ValueError):
        stratified_paired_bss([([1.0] * 56, [2.0] * 56)],
                              block_days=block, replicates=reps, seed=seed)


def test_pooled_loss_sum_overflow_fails_closed():
    # Each row is finite, but the pooled sum exceeds binary64 range.
    folds = [([1e308] * 56, [1e308] * 56)]
    with pytest.raises(ValueError, match="overflow"):
        stratified_paired_bss(folds, block_days=28, replicates=2, seed=7)


def test_finite_input_can_produce_nonfinite_bss_and_is_rejected():
    # Small positive reference loss, huge model loss: ratio overflows.
    folds = [([1e300] * 56, [1e-300] * 56)]
    with pytest.raises(ValueError, match="nonfinite pooled bootstrap BSS"):
        stratified_paired_bss(folds, block_days=28, replicates=2, seed=7)
