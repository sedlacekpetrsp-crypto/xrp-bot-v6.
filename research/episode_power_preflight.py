"""Pre-data power triage, not a profitability backtest.

All assumptions must be preregistered. DEFF is a conservative user-supplied
cluster/serial-dependence inflation, not inferred from observed strategy returns.
Normal approximation is optimistic for small effective sample sizes.
"""
from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import NormalDist


@dataclass(frozen=True)
class PowerScreen:
    n_episodes: int
    sigma_return: float
    roundtrip_fee: float
    roundtrip_slippage: float
    design_effect: float  # mandatory; justify with clustering/horizon model
    multiplicity: int = 1
    alpha: float = 0.05
    power: float = 0.80

    def evaluate(self) -> dict:
        nums = (self.sigma_return, self.roundtrip_fee, self.roundtrip_slippage,
                self.design_effect, self.alpha, self.power)
        if (type(self.n_episodes) is not int or self.n_episodes < 2
                or type(self.multiplicity) is not int or self.multiplicity < 1
                or any(type(v) not in (int, float) or not isfinite(v) for v in nums)
                or self.sigma_return <= 0 or self.roundtrip_fee < 0
                or self.roundtrip_slippage < 0 or self.design_effect < 1
                or not 0 < self.alpha <= 0.10 or not 0.5 < self.power < 1):
            raise ValueError("Invalid preregistered power-screen inputs")
        n_eff = self.n_episodes / self.design_effect
        if n_eff < 2:
            raise ValueError("Effective independent episode count below 2")
        normal = NormalDist()
        # Two-sided family-wise error bound; conservative for one-sided net > 0.
        z_alpha = normal.inv_cdf(1 - self.alpha / (2 * self.multiplicity))
        z_power = normal.inv_cdf(self.power)
        mde = (z_alpha + z_power) * self.sigma_return / sqrt(n_eff)
        cost = self.roundtrip_fee + self.roundtrip_slippage
        required = max(mde + cost, 3 * cost)
        return {
            "n_effective": n_eff,
            "minimum_detectable_gross_return": mde,
            "roundtrip_cost": cost,
            "required_gross_return_for_net_detection": mde + cost,
            "required_gross_return_for_gate": required,
            "small_sample_warning": n_eff < 30,
            "power_assumption": self.power,
            "alpha_assumption": self.alpha,
            "status": "DIAGNOSTIC_ONLY",
            "assumptions": "preregistered DEFF and sigma; normal approximation; two-sided Bonferroni; no observed returns",
        }
