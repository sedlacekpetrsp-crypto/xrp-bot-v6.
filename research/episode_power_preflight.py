"""Pre-data economic feasibility screen; NOT a performance backtest.

Normal-approximation minimum detectable mean return for independent episodes.
Correlation, fat tails and multiple testing can only worsen this optimistic bound.
"""
from dataclasses import dataclass
from math import isfinite, sqrt

@dataclass(frozen=True)
class PowerScreen:
    n_episodes: int
    sigma_return: float
    roundtrip_fee: float
    roundtrip_slippage: float
    z_alpha: float = 1.96
    z_power: float = 0.84
    multiplicity: int = 1

    def evaluate(self) -> dict:
        values = (self.sigma_return, self.roundtrip_fee,
                  self.roundtrip_slippage, self.z_alpha, self.z_power)
        if (type(self.n_episodes) is not int or self.n_episodes < 2
                or type(self.multiplicity) is not int or self.multiplicity < 1
                or any(not isfinite(x) for x in values)
                or self.sigma_return <= 0
                or min(self.roundtrip_fee, self.roundtrip_slippage) < 0
                or min(self.z_alpha, self.z_power) <= 0):
            raise ValueError("Invalid independent-episode power inputs")
        if self.multiplicity != 1:
            raise ValueError("Multiplicity requires pre-registered adjusted critical value")
        mde = (self.z_alpha + self.z_power) * self.sigma_return / sqrt(self.n_episodes)
        cost = self.roundtrip_fee + self.roundtrip_slippage
        return {"minimum_detectable_gross_return": mde,
                "roundtrip_cost": cost,
                "minimum_detectable_net_return": mde - cost,
                "required_gross_return_for_net_detection": mde + cost,
                "status": "DIAGNOSTIC_ONLY",
                "assumptions": "iid episodes, known sigma, normal approximation; optimistic"}
