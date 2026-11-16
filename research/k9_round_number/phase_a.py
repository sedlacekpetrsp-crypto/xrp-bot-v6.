"""K9 fáze A: agregace D1/D2 a vyhodnocení brány (mikrostruktura, žádný výnos, žádný obchod).

Implementuje PROTOCOL.md (zmrazeno 2026-11-16):
- události = první dotyky kulatých (off 0) a placebo (0,37; 0,73) úrovní, `events.detect_touches`;
- D = průměr metriky(kulaté) − průměr metriky(placebo), stratifikace po aktivu, vážený průměr podle počtu
  kulatých událostí aktiva;
- 95% CI: blokový bootstrap přes kalendářní dny, 10 000 replikací, seed 20261116. Pro souhrn přes aktiva se
  převzorkují STEJNÉ dny pro všechna aktiva (zachová korelaci mezi aktivy v týž den); váhy jsou pevné
  (počty z původního vzorku). Toto je implementační volba k oponentuře ChatGPT, ne změna endpointu.

Mezery v datech: vstup se před detekcí rozšíří na úplnou minutovou mřížku (chybějící minuta = NaN), takže
klouzavá okna s `min_periods=60` přes mezeru nikdy nevytvoří událost (nic se neimputuje).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.k9_round_number.audit import DEV_END
from research.k9_round_number.events import (LOOKBACK, PLACEBO_OFFSETS, ROUND_OFFSETS, STEPS,
                                             detect_touches)

REPS = 10_000
SEED = 20261116
GO_D1_MIN = 0.10


def to_minute_grid(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    grid = pd.date_range(df.index.min(), df.index.max(), freq="1min", tz=df.index.tz)
    return df.reindex(grid)


def asset_events(df: pd.DataFrame, step: float, lookback: int = LOOKBACK) -> dict[str, pd.DataFrame]:
    g = to_minute_grid(df)
    rnd = pd.concat([detect_touches(g, step, o, lookback) for o in ROUND_OFFSETS], ignore_index=True)
    plc = pd.concat([detect_touches(g, step, o, lookback) for o in PLACEBO_OFFSETS], ignore_index=True)
    return {"round": rnd, "placebo": plc}


def split_period(ev: pd.DataFrame, period: str) -> pd.DataFrame:
    t = pd.to_datetime(ev["time"], utc=True)
    return ev[t < DEV_END] if period == "dev" else ev[t >= DEV_END]


def _day_table(ev: pd.DataFrame, col: str, days: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    d = pd.to_datetime(ev["time"], utc=True).dt.floor("D")
    g = ev.assign(day=d).groupby("day")[col].agg(["sum", "count"]).reindex(days, fill_value=0)
    return g["sum"].to_numpy(float), g["count"].to_numpy(float)


def pooled_diff(per_asset: dict[str, dict[str, pd.DataFrame]], col: str, reps: int = REPS,
                seed: int = SEED) -> dict:
    """Vážené D přes aktiva + 95% CI společným blokovým bootstrapem přes dny."""
    per_asset = {a: {k: v[v[col].notna()] for k, v in e.items()} for a, e in per_asset.items()}
    assets = [a for a, e in per_asset.items() if len(e["round"]) and len(e["placebo"])]
    if not assets:
        return {"d": float("nan"), "lo": float("nan"), "hi": float("nan"), "n_round": 0, "n_placebo": 0,
                "per_asset": {}}
    all_days = set()
    for a in assets:
        for k in ("round", "placebo"):
            all_days |= set(pd.to_datetime(per_asset[a][k]["time"], utc=True).dt.floor("D"))
    days = np.array(sorted(all_days))
    w = np.array([len(per_asset[a]["round"]) for a in assets], float)
    w = w / w.sum()
    point_parts, tabs, out_assets = [], [], {}
    for a in assets:
        r, p = per_asset[a]["round"], per_asset[a]["placebo"]
        d = float(r[col].mean() - p[col].mean())
        point_parts.append(d)
        out_assets[a] = {"d": d, "n_round": int(len(r)), "n_placebo": int(len(p))}
        tabs.append((*_day_table(r, col, days), *_day_table(p, col, days)))
    point = float(np.dot(w, point_parts))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(days), size=(reps, len(days)))
    reps_d = np.zeros(reps)
    valid = np.ones(reps, bool)
    for wi, (rs, rc, ps, pc) in zip(w, tabs):
        sr, cr, sp, cp = rs[idx].sum(1), rc[idx].sum(1), ps[idx].sum(1), pc[idx].sum(1)
        ok = (cr > 0) & (cp > 0)
        valid &= ok
        reps_d += wi * np.where(ok, sr / np.where(cr > 0, cr, 1) - sp / np.where(cp > 0, cp, 1), 0.0)
    lo, hi = np.percentile(reps_d[valid], [2.5, 97.5])
    return {"d": point, "lo": float(lo), "hi": float(hi), "valid_reps": int(valid.sum()),
            "n_round": int(sum(v["n_round"] for v in out_assets.values())),
            "n_placebo": int(sum(v["n_placebo"] for v in out_assets.values())), "per_asset": out_assets}


def evaluate(dev_d1: dict, dev_d2: dict, final_d1: dict) -> dict:
    """Brána fáze A dle PROTOCOL.md. Žádné jiné endpointy, žádná náhrada."""
    dev_ok = (dev_d1["d"] >= GO_D1_MIN and dev_d1["lo"] > 0 and dev_d2["d"] > 0 and dev_d2["lo"] > 0)
    final_ok = final_d1["d"] > 0 and final_d1["lo"] > 0
    verdict = "GO (jen fáze B dodatek)" if dev_ok and final_ok else "METHOD NO-GO"
    return {"verdict": verdict, "dev_pass": bool(dev_ok), "final_confirm": bool(final_ok)}


def run(frames: dict[str, pd.DataFrame], reps: int = REPS) -> dict:  # pragma: no cover — spouští se v Actions
    per = {a: asset_events(df, STEPS[a]) for a, df in frames.items()}
    res = {}
    for period in ("dev", "final"):
        sub = {a: {k: split_period(v, period) for k, v in e.items()} for a, e in per.items()}
        res[period] = {"D1": pooled_diff(sub, "r_vol", reps), "D2": pooled_diff(sub, "m2", reps)}
    res["gate"] = evaluate(res["dev"]["D1"], res["dev"]["D2"], res["final"]["D1"])
    return res
