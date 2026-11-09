"""Shared PAPER risk guard (návrh 2026-11-09, zatím NEZAPOJENO do botů).

Čistá funkce bez I/O: rozhoduje jen o NOVÝCH vstupech a o násobku rizika.
Výstupy (stop, take-profit, trailing) se nikdy neblokují.

Pravidla (5 parametrů, záměrně málo):
  1. Propad od vrcholu equity bota:  < 5 % ×1,0 · 5–10 % ×0,5 · 10–15 % ×0,25 · ≥ 15 % KILL
     (KILL = žádné nové vstupy, dokud vlastník výslovně neresetuje: reset_kill()).
  2. Denní ztráta ≥ 1,5 % equity od začátku dne (UTC) ⇒ do konce dne žádné nové vstupy.
  3. Týdenní ztráta ≥ 3 % equity od začátku ISO týdne (UTC) ⇒ do konce týdne žádné nové vstupy.
  4. Neplatná / stará data (data_ok=False) ⇒ žádný nový vstup (kill-switch na data).
  5. Max. otevřených pozic na bota (výchozí 1, jak už boti mají).
Velikost pozice: bot dál počítá qty = equity × RISK × násobek / ztráta_na_stopu
(stop je u botů odvozen z ATR/struktury ⇒ sizing podle volatility zůstává).
"""
from datetime import datetime, timezone

POLICY = "RISK-GUARD-20261109-v1"
DD_STEPS = ((0.05, 1.0), (0.10, 0.5), (0.15, 0.25))   # (horní mez propadu, násobek)
DD_KILL = 0.15
DAILY_LOSS = 0.015
WEEKLY_LOSS = 0.03


def _keys(now_ms):
    t = datetime.fromtimestamp(now_ms / 1000, timezone.utc)
    y, w, _ = t.isocalendar()
    return t.strftime("%Y-%m-%d"), f"{y}-W{w:02d}"


def _num(x):
    x = float(x)
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError("non-finite risk input")
    return x


def update(rg, equity, peak, now_ms):
    """Aktualizuje stav guardu (dict uložený ve stavu bota) podle aktuální equity."""
    rg = dict(rg or {})
    equity = _num(equity)
    peak = max(_num(peak), equity, float(rg.get("peak") or 0.0))
    rg["peak"] = peak
    day, week = _keys(now_ms)
    if rg.get("day") != day:
        rg["day"], rg["day_start"] = day, equity
    if rg.get("week") != week:
        rg["week"], rg["week_start"] = week, equity
    dd = 0.0 if peak <= 0 else max(0.0, (peak - equity) / peak)
    rg["drawdown"] = dd
    if dd >= DD_KILL and not rg.get("killed"):
        rg["killed"], rg["kill_reason"], rg["killed_at"] = True, f"DRAWDOWN {dd:.1%} >= {DD_KILL:.0%}", now_ms
    rg["policy"] = POLICY
    return rg


def check_entry(rg, equity, open_positions=0, max_positions=1, data_ok=True):
    """Vrátí (povoleno, násobek_rizika, důvod). Volat až po update()."""
    equity = _num(equity)
    if not data_ok:
        return False, 0.0, "DATA_NOT_OK"
    if rg.get("killed"):
        return False, 0.0, "KILL: " + str(rg.get("kill_reason"))
    if open_positions >= max_positions:
        return False, 0.0, "MAX_POSITIONS"
    ds, ws = _num(rg["day_start"]), _num(rg["week_start"])
    if ds > 0 and (ds - equity) / ds >= DAILY_LOSS:
        return False, 0.0, "DAILY_LOSS_LIMIT"
    if ws > 0 and (ws - equity) / ws >= WEEKLY_LOSS:
        return False, 0.0, "WEEKLY_LOSS_LIMIT"
    dd = rg.get("drawdown", 0.0)
    for limit, mult in DD_STEPS:
        if dd < limit:
            return True, mult, "OK" if mult == 1.0 else f"DRAWDOWN_THROTTLE x{mult}"
    return False, 0.0, "DRAWDOWN_KILL"


def gate(state, equity, now_ms, data_ok=True, open_positions=0, max_positions=1, peak=None):
    """Pomocník pro boty: aktualizuje state['risk_guard'] a vrátí (povoleno, násobek)."""
    rg = update(state.get("risk_guard"), equity, equity if peak is None else peak, now_ms)
    ok, mult, why = check_entry(rg, equity, open_positions, max_positions, data_ok)
    rg["last_decision"], rg["mult"] = why, mult
    state["risk_guard"] = rg
    return ok, mult


def reset_kill(rg, approved_by, now_ms):
    """Ruční reset KILL — jen na výslovný pokyn vlastníka; zapíše kdo a kdy."""
    rg = dict(rg)
    rg.update(killed=False, kill_reason=None, reset_by=str(approved_by), reset_at=now_ms)
    return rg
