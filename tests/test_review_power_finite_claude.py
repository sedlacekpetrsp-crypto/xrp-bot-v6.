"""Claude review (dialog 0436) of 4bf70da/9360b04: derived-output finiteness guard."""
import pytest
from research.episode_power_preflight import PowerScreen


def test_three_times_cost_overflow_fails_closed():
    # mde + cost finite, but 3 * cost overflows -> must not return inf gate
    with pytest.raises(ValueError, match="Non-finite derived"):
        PowerScreen(100, 0.03, 7e307, 0.0, 1).evaluate()


def test_huge_multiplicity_fails_closed_as_valueerror():
    # alpha/(2m) rounds 1-p to 1.0; StatisticsError is a ValueError subclass
    with pytest.raises(ValueError):
        PowerScreen(100, 0.03, 0.001, 0.001, 1, multiplicity=10**16).evaluate()


@pytest.mark.xfail(strict=True, reason="F1 MINOR: huge int n_episodes raises OverflowError, not ValueError")
def test_huge_n_episodes_raises_valueerror():
    with pytest.raises(ValueError):
        PowerScreen(10**400, 0.03, 0.001, 0.001, 1).evaluate()
