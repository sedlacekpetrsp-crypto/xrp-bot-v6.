"""K11 delisting event: data-first executable-liquidity gate, NOT a signal/backtest.

All inputs must be known as-of the proposed order timestamp. Conservative cost
bounds deliberately exclude alpha and future prices. No external IO.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite


@dataclass(frozen=True)
class Quote:
    observed_at: datetime
    available_at: datetime
    bid: float
    ask: float
    bid_depth_usd: float
    ask_depth_usd: float


@dataclass(frozen=True)
class GateResult:
    eligible: bool
    reason: str
    round_trip_cost_bps: float | None = None


def execution_gate(quote: Quote, decision_at: datetime, notional_usd: float,
                   taker_fee_bps: float = 5.0, slippage_bps_per_side: float = 2.0,
                   max_quote_age_seconds: int = 30, max_cost_bps: float = 42.0,
                   min_depth_multiple: float = 2.0) -> GateResult:
    """Reject unknown, stale, crossed, thin or too-expensive quotes.

    Cost = observed full bid/ask spread + 2*(taker fee + modeled slippage).
    Funding, borrow and market impact beyond this bound are NOT included;
    passing does not authorize a trade or performance evaluation.
    """
    dates = (quote.observed_at, quote.available_at, decision_at)
    if any(d.tzinfo is None or d.utcoffset() is None for d in dates):
        return GateResult(False, "timezone_missing")
    observed, available, decision = (d.astimezone(timezone.utc) for d in dates)
    if available < observed or available > decision or observed > decision:
        return GateResult(False, "pit_unavailable")
    if max_quote_age_seconds < 0 or (decision - observed).total_seconds() > max_quote_age_seconds:
        return GateResult(False, "stale_quote")
    values = (quote.bid, quote.ask, quote.bid_depth_usd, quote.ask_depth_usd,
              notional_usd, taker_fee_bps, slippage_bps_per_side, max_cost_bps,
              min_depth_multiple)
    if not all(isfinite(v) for v in values):
        return GateResult(False, "nonfinite")
    if min(quote.bid, quote.ask, notional_usd) <= 0 or min(
        quote.bid_depth_usd, quote.ask_depth_usd, taker_fee_bps,
        slippage_bps_per_side, max_cost_bps, min_depth_multiple
    ) < 0:
        return GateResult(False, "invalid_input")
    if quote.ask <= quote.bid:
        return GateResult(False, "crossed_or_locked")
    if min(quote.bid_depth_usd, quote.ask_depth_usd) < min_depth_multiple * notional_usd:
        return GateResult(False, "insufficient_depth")
    mid = (quote.bid + quote.ask) / 2
    spread_bps = (quote.ask - quote.bid) / mid * 10000
    total = spread_bps + 2 * (taker_fee_bps + slippage_bps_per_side)
    if total > max_cost_bps:
        return GateResult(False, "cost_exceeds_cap", total)
    return GateResult(True, "diagnostic_only", total)
