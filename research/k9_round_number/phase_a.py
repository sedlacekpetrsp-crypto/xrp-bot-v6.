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
# Dodatek 1 (2026-11-16, před daty, dialog 0353): podíl neplatných replik > 5 % ⇒ INCONCLUSIVE;
# syntetická síla brány při pravém D1 = 2× prah (0,20), sd 1,0, korelace v dni 0,3 < 0,80 ⇒ neúspěch = INCONCLUSIVE.
MAX_INVALID_REP_FRAC = 0.05
POWER_MIN = 0.80
POWER_CELL = {"effect": 0.20, "sd": 1.0, "rho": 0.3}


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
    if valid.any():
        lo, hi = np.percentile(reps_d[valid], [2.5, 97.5])
    else:
        lo = hi = float("nan")
    # samostatné CI každého aktiva na STEJNÝCH převzorkovaných dnech (report vedle pooled, ne brána)
    for a, (rs, rc, ps, pc) in zip(assets, tabs):
        sr, cr, sp, cp = rs[idx].sum(1), rc[idx].sum(1), ps[idx].sum(1), pc[idx].sum(1)
        ok = (cr > 0) & (cp > 0)
        da = sr[ok] / cr[ok] - sp[ok] / cp[ok]
        alo, ahi = np.percentile(da, [2.5, 97.5]) if ok.any() else (float("nan"), float("nan"))
        out_assets[a].update({"lo": float(alo), "hi": float(ahi), "valid_reps": int(ok.sum())})
    return {"d": point, "lo": float(lo), "hi": float(hi), "valid_reps": int(valid.sum()), "reps": int(reps),
            "invalid_frac": float(1 - valid.mean()),
            "n_round": int(sum(v["n_round"] for v in out_assets.values())),
            "n_placebo": int(sum(v["n_placebo"] for v in out_assets.values())), "per_asset": out_assets}


def exposure_table(per_asset: dict[str, dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """Expozice kulaté vs placebo po aktivu × roku × hodině UTC (počty + průměrná úroveň jako cenová proxy).

    Jen popis nerovnováhy (dodatek 1, bod 1); NEslouží k přelaďování placebo ani k vážení.
    """
    rows = []
    for a, e in per_asset.items():
        for k in ("round", "placebo"):
            ev = e[k]
            if ev.empty:
                continue
            t = pd.to_datetime(ev["time"], utc=True)
            g = ev.assign(year=t.dt.year, hour=t.dt.hour).groupby(["year", "hour"])
            agg = g.agg(n=("level", "size"), mean_level=("level", "mean")).reset_index()
            rows.append(agg.assign(asset=a, kind=k))
    if not rows:
        return pd.DataFrame(columns=["asset", "kind", "year", "hour", "n", "mean_level"])
    return pd.concat(rows, ignore_index=True)[["asset", "kind", "year", "hour", "n", "mean_level"]]


def power_table(round_per_day: np.ndarray, placebo_per_day: np.ndarray, effects=(0.10, 0.15, 0.20),
                sds=(0.5, 1.0), rhos=(0.0, 0.3), sims: int = 200, reps: int = 1000,
                seed: int = SEED) -> pd.DataFrame:
    """Syntetická (ne-výkonnostní) síla brány D1 pro dané počty událostí na den.

    Vstup = jen POČTY událostí na den (z kroku 0/detekce), žádná hodnota metriky. Model: r = efekt·[kulatá] +
    denní šok (var rho·sd²) + šum (var (1−rho)·sd²); síla = P(D1 ≥ GO_D1_MIN a dolní mez CI > 0).
    """
    rc = np.asarray(round_per_day, int)
    pc = np.asarray(placebo_per_day, int)
    n_days = len(rc)
    rng = np.random.default_rng(seed)
    out = []
    for sd in sds:
        for rho in rhos:
            for eff in effects:
                hits = 0
                for _ in range(sims):
                    day_shock = rng.normal(0, np.sqrt(rho) * sd, n_days)
                    noise_sd = np.sqrt(1 - rho) * sd
                    rs = rc * (eff + day_shock) + rng.normal(0, 1, n_days) * noise_sd * np.sqrt(rc)
                    ps = pc * day_shock + rng.normal(0, 1, n_days) * noise_sd * np.sqrt(pc)
                    if rc.sum() == 0 or pc.sum() == 0:
                        continue
                    d = rs.sum() / rc.sum() - ps.sum() / pc.sum()
                    idx = rng.integers(0, n_days, size=(reps, n_days))
                    cr, cp = rc[idx].sum(1), pc[idx].sum(1)
                    ok = (cr > 0) & (cp > 0)
                    if not ok.any():
                        continue
                    bd = rs[idx].sum(1)[ok] / cr[ok] - ps[idx].sum(1)[ok] / cp[ok]
                    lo = np.percentile(bd, 2.5)
                    hits += int(d >= GO_D1_MIN and lo > 0)
                out.append({"effect": eff, "sd": sd, "rho": rho, "n_days": n_days,
                            "n_round": int(rc.sum()), "n_placebo": int(pc.sum()), "power": hits / sims})
    return pd.DataFrame(out)


def decisive_power(table: pd.DataFrame) -> float:
    c = POWER_CELL
    m = table[(table["effect"] == c["effect"]) & (table["sd"] == c["sd"]) & (table["rho"] == c["rho"])]
    return float(m["power"].iloc[0]) if len(m) else float("nan")


def evaluate(dev_d1: dict, dev_d2: dict, final_d1: dict, power: float | None = None) -> dict:
    """Brána fáze A dle PROTOCOL.md + dodatek 1. Žádné jiné endpointy, žádná náhrada, prahy se nemění."""
    dev_ok = (dev_d1["d"] >= GO_D1_MIN and dev_d1["lo"] > 0 and dev_d2["d"] > 0 and dev_d2["lo"] > 0)
    final_ok = final_d1["d"] > 0 and final_d1["lo"] > 0
    inval = max(r.get("invalid_frac", 0.0) for r in (dev_d1, dev_d2, final_d1))
    low_power = power is None or not (power >= POWER_MIN)
    if inval > MAX_INVALID_REP_FRAC:
        verdict = "INCONCLUSIVE (neplatné repliky)"
    elif dev_ok and final_ok:
        verdict = "GO (jen fáze B dodatek)"
    elif low_power:
        verdict = "INCONCLUSIVE (nízká síla)"
    else:
        verdict = "METHOD NO-GO"
    return {"verdict": verdict, "dev_pass": bool(dev_ok), "final_confirm": bool(final_ok),
            "max_invalid_frac": float(inval), "power": power}


def run(frames: dict[str, pd.DataFrame], reps: int = REPS) -> dict:  # pragma: no cover — spouští se v Actions
    per = {a: asset_events(df, STEPS[a]) for a, df in frames.items()}
    res = {}
    for period in ("dev", "final"):
        sub = {a: {k: split_period(v, period) for k, v in e.items()} for a, e in per.items()}
        res[period] = {"D1": pooled_diff(sub, "r_vol", reps), "D2": pooled_diff(sub, "m2", reps)}
    # síla se počítá PŘED výsledky jen z počtů událostí na den ve vývojovém období (pooled přes aktiva)
    dev = {a: {k: split_period(v, "dev") for k, v in e.items()} for a, e in per.items()}
    days = sorted({d for e in dev.values() for v in e.values()
                   for d in pd.to_datetime(v["time"], utc=True).dt.floor("D")})
    cnt = {k: sum(pd.to_datetime(e[k]["time"], utc=True).dt.floor("D").value_counts().reindex(days, fill_value=0)
                  .to_numpy() for e in dev.values()) for k in ("round", "placebo")}
    res["power_table"] = power_table(cnt["round"], cnt["placebo"])
    res["exposure"] = exposure_table(per)
    res["gate"] = evaluate(res["dev"]["D1"], res["dev"]["D2"], res["final"]["D1"],
                           decisive_power(res["power_table"]))
    return res
