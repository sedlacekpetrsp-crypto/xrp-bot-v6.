"""Synthetic alpha-guard checks; no market data or performance testing."""
import pytest
from research.episode_power_preflight import PowerScreen


def screen(alpha):
    return PowerScreen(n_episodes=100, sigma_return=0.01,
                       roundtrip_fee=0.00095, roundtrip_slippage=0.0002,
                       design_effect=2, alpha=alpha)


@pytest.mark.parametrize("alpha", [0, -0.01, 0.10000001, 0.5, 0.95, 1, True, float("nan"), float("inf")])
def test_reject_unsafe_alpha(alpha):
    with pytest.raises(ValueError):
        screen(alpha).evaluate()


@pytest.mark.parametrize("alpha", [0.001, 0.05, 0.10])
def test_valid_alpha_reported(alpha):
    result = screen(alpha).evaluate()
    assert result["alpha_assumption"] == alpha
    assert result["status"] == "DIAGNOSTIC_ONLY"


def test_stricter_alpha_increases_mde():
    assert screen(0.01).evaluate()["minimum_detectable_gross_return"] > screen(0.05).evaluate()["minimum_detectable_gross_return"]
