"""Market-neutral BTC spot/quarterly-futures carry backtest."""
from dataclasses import dataclass, replace
from math import isfinite

HOUR_MS = 3_600_000
DAY_MS = 86_400_000


@dataclass(frozen=True)
class Config:
    entry_window_days: int = 28
    entry_cutoff_days: int = 7
    minimum_annualized_basis: float = 0.08
    stop_annualized_basis: float = 0.25
    leg_fraction: float = 0.15
    spot_fee_rate: float = 0.00095
    futures_fee_rate: float = 0.00050
    slippage_rate: float = 0.00020
    initial_equity: float = 10_000.0


def annualized_basis(bar, expiry_ts, field="close"):
    remaining_days = (expiry_ts - bar["timestamp"]) / DAY_MS
    if remaining_days <= 0:
        return 0.0
    raw = bar[f"future_{field}"] / bar[f"spot_{field}"] - 1
    return raw * 365.0 / remaining_days


def validate(bars):
    stamps = []
    for bar in bars:
        values = [bar[k] for k in ("spot_open", "spot_close", "future_open", "future_close")]
        if not all(isfinite(value) and value > 0 for value in values):
            raise ValueError("Invalid synchronized prices")
        if bar["timestamp"] % HOUR_MS:
            raise ValueError("Invalid timestamp")
        stamps.append(bar["timestamp"])
    if any(stamps[i] <= stamps[i - 1] for i in range(1, len(stamps))):
        raise ValueError("Unordered bars")


def backtest_contract(bars, expiry_ts, config=Config()):
    validate(bars)
    equity = config.initial_equity; peak = equity; max_drawdown = 0.0
    position = None; trade = None; last_bar = None
    window_start = expiry_ts - config.entry_window_days * DAY_MS
    cutoff = expiry_ts - config.entry_cutoff_days * DAY_MS

    def close(bar, reason, use_close=False):
        nonlocal equity, position, trade
        suffix = "close" if use_close else "open"
        spot_raw = bar[f"spot_{suffix}"]; future_raw = bar[f"future_{suffix}"]
        spot_exit = spot_raw * (1 - config.slippage_rate)
        future_exit = future_raw * (1 + config.slippage_rate)
        spot_pnl = position["spot_qty"] * (spot_exit - position["spot_entry"])
        future_pnl = position["future_qty"] * (position["future_entry"] - future_exit)
        exit_fees = position["spot_qty"] * spot_exit * config.spot_fee_rate + position["future_qty"] * future_exit * config.futures_fee_rate
        equity += spot_pnl + future_pnl - exit_fees
        net = spot_pnl + future_pnl - position["entry_fees"] - exit_fees
        trade = {"entry_ts": position["entry_ts"], "exit_ts": bar["timestamp"],
                 "entry_annualized_basis": position["signal_basis"], "reason": reason,
                 "spot_pnl": spot_pnl, "future_pnl": future_pnl,
                 "fees": position["entry_fees"] + exit_fees, "net_pnl": net,
                 "return_on_equity": net / position["equity_before"]}
        position = None

    for i, bar in enumerate(bars):
        ts = bar["timestamp"]
        if ts < window_start: continue
        if ts > expiry_ts: break
        last_bar = bar
        contiguous = i > 0 and ts - bars[i - 1]["timestamp"] == HOUR_MS
        if position and ts >= expiry_ts:
            close(bar, "EXPIRY")
        elif position and contiguous and annualized_basis(bars[i - 1], expiry_ts) >= config.stop_annualized_basis:
            close(bar, "GAP_STOP")
        if not position and trade is None and window_start < ts <= cutoff and ts % DAY_MS == HOUR_MS and contiguous:
            signal_basis = annualized_basis(bars[i - 1], expiry_ts)
            if signal_basis >= config.minimum_annualized_basis:
                before = equity; leg_notional = equity * config.leg_fraction
                spot_entry = bar["spot_open"] * (1 + config.slippage_rate)
                future_entry = bar["future_open"] * (1 - config.slippage_rate)
                entry_fees = leg_notional * (config.spot_fee_rate + config.futures_fee_rate)
                equity -= entry_fees
                position = {"entry_ts": ts, "spot_entry": spot_entry, "future_entry": future_entry,
                            "spot_qty": leg_notional / spot_entry, "future_qty": leg_notional / future_entry,
                            "entry_fees": entry_fees, "signal_basis": signal_basis, "equity_before": before}
        marked = equity
        if position:
            marked += position["spot_qty"] * (bar["spot_close"] - position["spot_entry"])
            marked += position["future_qty"] * (position["future_entry"] - bar["future_close"])
        peak = max(peak, marked); max_drawdown = max(max_drawdown, (peak - marked) / peak)
    if position and last_bar:
        close(last_bar, "END", use_close=True)
    return {"trade": trade, "ending_equity": equity,
            "net_return": equity / config.initial_equity - 1, "max_drawdown": max_drawdown}


def with_cost_stress(config=Config()):
    return replace(config, spot_fee_rate=config.spot_fee_rate * 2,
                   futures_fee_rate=config.futures_fee_rate * 2,
                   slippage_rate=config.slippage_rate * 2)
