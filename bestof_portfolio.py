"""Shared, fail-closed entry sizing for both BEST sleeves (PAPER only)."""
import math

BUILD = 'BESTOF-2026-10-11-PORTFOLIO'


def entry_budget(core, symbol, side, desired_risk):
    """Return risk and notional ceilings without mutating any trading state.

    Existing initial risk is reserved even after a stop moves to break-even.
    Hooks are optional for the standalone app/offline replay, but cannot enlarge
    the local budget. An invalid restored position or failed hook blocks entry.
    """
    try:
        if core.TRADING_MODE != 'PAPER' or symbol not in core.SYMBOLS:
            return 0., 0.
        if symbol in core.positions or len(core.positions) >= core.MAX_OPEN_POSITIONS:
            return 0., 0.
        balance = float(core.PAPER_BALANCE)
        values = [balance, float(desired_risk)]
        risks, notionals = [], []
        for p in core.positions.values():
            risk, qty, price = (float(p[k]) for k in ('risk_usdt', 'qty', 'entry_price'))
            values.extend([risk, qty, price])
            risks.append(risk)
            notionals.append(qty * price)
        if any(not math.isfinite(x) or x < 0 for x in values) or balance <= 0:
            return 0., 0.
        check = getattr(core, 'portfolio_entry_allowed', None)
        if callable(check) and not check('BEST', symbol, side)[0]:
            return 0., 0.
        total_risk = balance * core.RISK_PER_TRADE * core.MAX_OPEN_POSITIONS
        risk = min(float(desired_risk), max(0., total_risk - sum(risks)))
        allowance = getattr(core, 'portfolio_risk_allowance', None)
        if callable(allowance):
            allowed, _ = allowance('BEST', symbol, side, risk)
            allowed = float(allowed)
            if not math.isfinite(allowed) or allowed < 0:
                return 0., 0.
            risk = min(risk, allowed)
        share = min(.5, getattr(core, 'MAX_NOTIONAL_SHARE', .35))
        total_share = min(1., share * core.MAX_OPEN_POSITIONS)
        notional = min(balance * share, max(0., balance * total_share - sum(notionals)))
        return risk, notional
    except Exception:
        # A broken coordinator must never fall through to an unguarded entry.
        return 0., 0.
