"""PAPER-only deterministic pre-performance cost feasibility arithmetic.

This is NOT a backtest, signal generator, or profitability estimate.
Use before proposing any directional strategy to reject gross-edge claims
that cannot cover explicit round-trip costs. Rates are fractions, not percent.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Union

Number = Union[str, int, Decimal]


def _rate(value: Number, name: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError(f"{name}: use Decimal, int or decimal string; no bool/float")
    try:
        result = Decimal(value)
    except (ValueError, ArithmeticError, TypeError) as exc:
        raise ValueError(f"{name}: invalid decimal") from exc
    if not result.is_finite() or result < 0 or result >= 1:
        raise ValueError(f"{name}: rate must be finite and in [0,1)")
    return result


@dataclass(frozen=True)
class CostGate:
    entry_fee: Decimal
    exit_fee: Decimal
    entry_slippage: Decimal
    exit_slippage: Decimal

    def __post_init__(self) -> None:
        # Direct dataclass construction must not bypass the same fail-closed
        # contract as from_rates. frozen=True requires object.__setattr__.
        for name in ("entry_fee", "exit_fee", "entry_slippage", "exit_slippage"):
            object.__setattr__(self, name, _rate(getattr(self, name), name))

    @classmethod
    def from_rates(
        cls, entry_fee: Number, exit_fee: Number,
        entry_slippage: Number, exit_slippage: Number
    ) -> "CostGate":
        return cls(*(_rate(v, name) for name, v in (
            ("entry_fee", entry_fee), ("exit_fee", exit_fee),
            ("entry_slippage", entry_slippage), ("exit_slippage", exit_slippage)
        )))

    def minimum_gross_return(self) -> Decimal:
        """Gross price return needed for net terminal wealth >= starting wealth.

        Long spot, buy fee and adverse entry slippage increase effective cost;
        sell fee and adverse exit slippage decrease realized proceeds.
        Assumes fees charged on notional and no funding/borrow/taxes.
        """
        return (
            (1 + self.entry_slippage) * (1 + self.entry_fee)
            / ((1 - self.exit_slippage) * (1 - self.exit_fee))
            - 1
        )

    def net_return(self, gross_return: Number) -> Decimal:
        if isinstance(gross_return, bool) or isinstance(gross_return, float):
            raise ValueError("gross_return: use exact decimal")
        try:
            gross = Decimal(gross_return)
        except (ValueError, ArithmeticError, TypeError) as exc:
            raise ValueError("gross_return: invalid decimal") from exc
        if not gross.is_finite() or gross <= -1:
            raise ValueError("gross_return: must be finite and greater than -1")
        return (
            (1 + gross) * (1 - self.exit_slippage) * (1 - self.exit_fee)
            / ((1 + self.entry_slippage) * (1 + self.entry_fee))
            - 1
        )
