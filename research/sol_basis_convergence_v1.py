"""Market-neutral SOL spot/perpetual basis-convergence backtest."""
from dataclasses import dataclass, replace
from math import isfinite

HOUR_MS = 3_600_000


@dataclass(frozen=True)
class Config:
    entry_premium: float = 0.0040
    target_premium: float = 0.0002
    stop_premium: float = 0.0120
    maximum_hold_hours: int = 48
    cooldown_hours: int = 8
    leg_fraction: float = 0.15
    spot_fee_rate: float = 0.00095
    futures_fee_rate: float = 0.00050
    slippage_rate: float = 0.00020
    funding_credit_multiplier: float = 1.0
    funding_debit_multiplier: float = 1.0
    initial_equity: float = 10_000.0


def validate(bars, funding):
    stamps = []
    for bar in bars:
        values = [bar[k] for k in ("spot_open", "spot_close", "perp_open", "perp_close")]
        if not all(isfinite(value) and value > 0 for value in values):
            raise ValueError("Invalid synchronized prices")
        if bar["timestamp"] % HOUR_MS:
            raise ValueError("Invalid timestamp")
        stamps.append(bar["timestamp"])
    if any(stamps[i] <= stamps[i - 1] for i in range(1, len(stamps))):
        raise ValueError("Unordered bars")
    if any(ts % HOUR_MS or not isfinite(rate) for ts, rate in funding.items()):
        raise ValueError("Invalid funding")


def premium(bar, field="close"):
    return bar[f"perp_{field}"] / bar[f"spot_{field}"] - 1


def backtest(bars, funding, start_ts, end_ts, config=Config()):
    validate(bars, funding)
    equity = config.initial_equity; peak = equity; max_drawdown = 0.0
    position = None; trades = []; cooldown_until = start_ts; last_bar = None

    def close(bar, reason):
        nonlocal equity, position, cooldown_until
        spot_exit = bar["spot_open"] * (1 - config.slippage_rate)
        perp_exit = bar["perp_open"] * (1 + config.slippage_rate)
        spot_pnl = position["spot_qty"] * (spot_exit - position["spot_entry"])
        perp_pnl = position["perp_qty"] * (position["perp_entry"] - perp_exit)
        exit_fees = position["spot_qty"] * spot_exit * config.spot_fee_rate + position["perp_qty"] * perp_exit * config.futures_fee_rate
        equity += spot_pnl + perp_pnl - exit_fees
        net = spot_pnl + perp_pnl + position["funding_pnl"] - position["entry_fees"] - exit_fees
        trades.append({"entry_ts": position["entry_ts"], "exit_ts": bar["timestamp"],
                       "entry_premium": position["entry_premium"], "exit_premium": perp_exit / spot_exit - 1,
                       "reason": reason, "spot_pnl": spot_pnl, "perp_pnl": perp_pnl,
                       "funding_pnl": position["funding_pnl"], "fees": position["entry_fees"] + exit_fees,
                       "net_pnl": net, "return_on_equity": net / position["equity_before"]})
        position = None; cooldown_until = bar["timestamp"] + config.cooldown_hours * HOUR_MS

    for i, bar in enumerate(bars):
        ts = bar["timestamp"]
        if ts < start_ts: continue
        if ts >= end_ts: break
        last_bar = bar
        if position and ts in funding and ts > position["entry_ts"]:
            cashflow = position["perp_notional"] * funding[ts]  # short perp receives positive funding
            cashflow *= config.funding_credit_multiplier if cashflow >= 0 else config.funding_debit_multiplier
            equity += cashflow; position["funding_pnl"] += cashflow
        if position:
            prior_premium = premium(bars[i - 1]) if i > 0 and ts - bars[i - 1]["timestamp"] == HOUR_MS else None
            if prior_premium is not None and prior_premium >= config.stop_premium:
                close(bar, "GAP_STOP")
            elif prior_premium is not None and prior_premium <= config.target_premium:
                close(bar, "TARGET")
            elif ts - position["entry_ts"] >= config.maximum_hold_hours * HOUR_MS:
                close(bar, "TIME")
        if not position and ts >= cooldown_until and i > 0 and ts - bars[i - 1]["timestamp"] == HOUR_MS:
            setup_premium = premium(bars[i - 1])
            if setup_premium >= config.entry_premium:
                before = equity; leg_notional = equity * config.leg_fraction
                spot_entry = bar["spot_open"] * (1 + config.slippage_rate)
                perp_entry = bar["perp_open"] * (1 - config.slippage_rate)
                entry_fees = leg_notional * (config.spot_fee_rate + config.futures_fee_rate)
                equity -= entry_fees
                position = {"entry_ts": ts, "spot_entry": spot_entry, "perp_entry": perp_entry,
                            "spot_qty": leg_notional / spot_entry, "perp_qty": leg_notional / perp_entry,
                            "perp_notional": leg_notional, "entry_premium": perp_entry / spot_entry - 1,
                            "entry_fees": entry_fees, "funding_pnl": 0.0, "equity_before": before}
        marked = equity
        if position:
            marked += position["spot_qty"] * (bar["spot_close"] - position["spot_entry"])
            marked += position["perp_qty"] * (position["perp_entry"] - bar["perp_close"])
        peak = max(peak, marked); max_drawdown = max(max_drawdown, (peak - marked) / peak)
    if position and last_bar:
        synthetic = {**last_bar, "spot_open": last_bar["spot_close"], "perp_open": last_bar["perp_close"]}
        close(synthetic, "END")
    return {"trades": trades, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1, "max_drawdown": max_drawdown}


def with_cost_stress(config=Config()):
    return replace(config, spot_fee_rate=config.spot_fee_rate * 2,
                   futures_fee_rate=config.futures_fee_rate * 2,
                   slippage_rate=config.slippage_rate * 2,
                   funding_credit_multiplier=0.5, funding_debit_multiplier=2.0)
