"""Claude review of 392ffb7/660fb18 (synthetic only)."""
from research.g1_precision_denominator_preflight import preflight_denominators, wilson_lower


def test_small_budget_makes_precision_impossible():
    # 5 alert episodes: even 5/5 has Wilson lower bound < 0.6
    r = preflight_denominators(21, 5)
    assert r["precision_possible"] is False and r["minimum_precision_true_alerts"] is None


def test_exact_minima_match_pr73():
    assert preflight_denominators(21, 21)["minimum_recall_hits"] == 15
    assert preflight_denominators(21, 21)["minimum_precision_true_alerts"] == 18
    assert wilson_lower(15, 21) > 0.5 > wilson_lower(14, 21)


def test_recall_denominator_validated_too():
    import pytest
    with pytest.raises(ValueError):
        preflight_denominators(0, 10)
