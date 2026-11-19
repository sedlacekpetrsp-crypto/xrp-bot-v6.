"""Nezávislý přepočet fáze B z `phaseB_trades.csv` (dodatek 2 bod 6). Neimportuje phase_b ani runner.

Přepočítá z cen vstupu/výstupu: hrubý výnos, náklady ×1/×2/×3 s fundingem, E (průměr čistého ×1 kulaté),
Δ = G(kulaté) − G(placebo), denní PnL a Sharpe/DSR (vlastní vzorec Bailey & López de Prado) a porovná s
`phaseB_results.json`. Výstup: seznam neshod (prázdný = shoda). Použití:
  python -m research.k9_round_number.verify_phase_b --trades ... --results ...
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from statistics import NormalDist

import pandas as pd

RT, FUND = 0.0014, 0.0003
TOL = 1e-9


def _dsr(daily: list[float], n_trials: int, var_annual: float) -> float:
    t = len(daily)
    mu = sum(daily) / t
    m2 = sum((x - mu) ** 2 for x in daily) / t
    sd = math.sqrt(m2)
    sr = mu / math.sqrt(m2 * t / (t - 1))
    skew = sum((x - mu) ** 3 for x in daily) / t / sd ** 3
    kurt = sum((x - mu) ** 4 for x in daily) / t / m2 ** 2
    nd, g = NormalDist(), 0.5772156649015329
    v = var_annual / 365
    sr0 = math.sqrt(v) * ((1 - g) * nd.inv_cdf(1 - 1 / n_trials) + g * nd.inv_cdf(1 - 1 / (n_trials * math.e)))
    return nd.cdf((sr - sr0) * math.sqrt(t - 1) / math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr * sr))


def recompute(trades: pd.DataFrame, start: str, end: str, n_trials: int, var_annual: float = 0.5) -> dict:
    tr = trades.copy()
    tr["g"] = tr["direction"] * (tr["exit"] / tr["entry"] - 1)
    for m in (1, 2, 3):
        tr[f"n{m}"] = tr["g"] - m * (RT + FUND * tr["funding_crossings"])
    r, p = tr[tr["kind"] == "round"], tr[tr["kind"] == "placebo"]
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    s = s.tz_localize("UTC") if s.tz is None else s.tz_convert("UTC")
    e = e.tz_localize("UTC") if e.tz is None else e.tz_convert("UTC")
    days = pd.date_range(s.floor("D"), e.floor("D"), freq="D")
    d = pd.to_datetime(r["entry_time"], utc=True).dt.floor("D")
    daily = r.groupby(d)["n1"].sum().reindex(days, fill_value=0.0)
    return {"E": float(r["n1"].mean()), "x2": float(r["n2"].mean()), "x3": float(r["n3"].mean()),
            "delta_placebo": float(r["g"].mean() - p["g"].mean()), "dsr": _dsr(daily.tolist(), n_trials, var_annual),
            "gross_mismatch": int((tr["g"] - tr["gross"]).abs().gt(TOL).sum()),
            "net_mismatch": int(sum((tr[f"n{m}"] - tr[f"net_x{m}"]).abs().gt(TOL).sum() for m in (1, 2, 3)))}


def compare(rec: dict, res: dict) -> list[str]:
    bad = []
    pairs = [("E", res["E_net_x1"]["point"]), ("x2", res["net_x2_mean"]), ("x3", res["net_x3_mean"]),
             ("delta_placebo", res["delta_vs_placebo"]["point"]), ("dsr", res["dsr"]["dsr"])]
    for k, v in pairs:
        if not math.isclose(rec[k], v, rel_tol=1e-6, abs_tol=1e-9):
            bad.append(f"{k}: přepočet {rec[k]} ≠ runner {v}")
    for k in ("gross_mismatch", "net_mismatch"):
        if rec[k]:
            bad.append(f"{k}: {rec[k]} řádků")
    return bad


def main(argv=None) -> int:  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", default="research/k9_round_number/phaseB_trades.csv")
    ap.add_argument("--results", default="research/k9_round_number/phaseB_results.json")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", required=True, help="poslední den závěrečného úseku v datech (UTC)")
    a = ap.parse_args(argv)
    res = json.load(open(a.results))
    rec = recompute(pd.read_csv(a.trades), a.start, a.end, res["dsr"]["n_trials"])
    bad = compare(rec, res)
    print(json.dumps({"recomputed": rec, "mismatches": bad}, ensure_ascii=False, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
