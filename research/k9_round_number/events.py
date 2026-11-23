"""K9 fáze A: detekce prvních dotyků kulatých/placebo úrovní a mikrostrukturní metriky (bez výnosů).

Vstup: DataFrame 1m svíček (index = open_time, sloupce high, low, close, volume, taker_buy) jednoho aktiva.
Definice viz PROTOCOL.md (zmrazeno 2026-11-16). Modul nepočítá žádný výnos ani obchod.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

STEPS = {"BTCUSDT": 1000.0, "ETHUSDT": 100.0, "XRPUSDT": 0.10}
ROUND_OFFSETS = (0.0,)
PLACEBO_OFFSETS = (0.37, 0.73)
LOOKBACK = 60
_EPS = 1e-9


def level_above(x: float, step: float, off: float) -> float:
    """Nejmenší úroveň (k+off)*step ostře nad x."""
    k = math.floor(x / step - off + _EPS) + 1
    return round((k + off) * step, 10)


def level_below(x: float, step: float, off: float) -> float:
    """Největší úroveň (k+off)*step ostře pod x."""
    k = math.ceil(x / step - off - _EPS) - 1
    return round((k + off) * step, 10)


def detect_touches(df: pd.DataFrame, step: float, off: float, lookback: int = LOOKBACK) -> pd.DataFrame:
    """První dotyky úrovní (k+off)*step po >= lookback minutách bez dotyku. Jedna událost na minutu."""
    hi_prev = df["high"].shift(1).rolling(lookback, min_periods=lookback).max()
    lo_prev = df["low"].shift(1).rolling(lookback, min_periods=lookback).min()
    vol_med = df["volume"].shift(1).rolling(lookback, min_periods=lookback).median()
    share = (df["taker_buy"] / df["volume"]).where(df["volume"] > 0)
    share_med = share.shift(1).rolling(lookback, min_periods=lookback).median()
    close_prev = df["close"].shift(1)
    rows = []
    for i in range(lookback, len(df)):
        hp, lp = hi_prev.iat[i], lo_prev.iat[i]
        if np.isnan(hp) or np.isnan(lp):
            continue
        cands = []
        up = level_above(hp, step, off)
        if up <= df["high"].iat[i] + _EPS:
            cands.append((up, 1))
        dn = level_below(lp, step, off)
        if dn >= df["low"].iat[i] - _EPS:
            cands.append((dn, -1))
        if not cands:
            continue
        cp = close_prev.iat[i]
        level, direction = min(cands, key=lambda c: abs(c[0] - cp))
        vol, vm = df["volume"].iat[i], vol_med.iat[i]
        if not (vol > 0 and vm > 0):
            continue
        sh, shm = share.iat[i], share_med.iat[i]
        dir_share = sh if direction == 1 else 1.0 - sh
        dir_med = shm if direction == 1 else 1.0 - shm
        rows.append({"time": df.index[i], "level": level, "direction": direction,
                     "r_vol": math.log(vol / vm), "m2": dir_share - dir_med})
    return pd.DataFrame(rows, columns=["time", "level", "direction", "r_vol", "m2"])


def block_bootstrap_diff(a: pd.DataFrame, b: pd.DataFrame, col: str, reps: int = 10_000,
                         seed: int = 20261116) -> tuple[float, float, float]:
    """Rozdíl průměrů col (a − b) a 95% CI blokovým bootstrapem přes kalendářní dny."""
    a = a.assign(day=pd.to_datetime(a["time"]).dt.floor("D"))
    b = b.assign(day=pd.to_datetime(b["time"]).dt.floor("D"))
    days = np.array(sorted(set(a["day"]) | set(b["day"])))
    ga = a.groupby("day")[col].agg(["sum", "count"]).reindex(days, fill_value=0)
    gb = b.groupby("day")[col].agg(["sum", "count"]).reindex(days, fill_value=0)
    point = a[col].mean() - b[col].mean()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(days), size=(reps, len(days)))
    sa, ca = ga["sum"].to_numpy()[idx].sum(1), ga["count"].to_numpy()[idx].sum(1)
    sb, cb = gb["sum"].to_numpy()[idx].sum(1), gb["count"].to_numpy()[idx].sum(1)
    ok = (ca > 0) & (cb > 0)
    diffs = sa[ok] / ca[ok] - sb[ok] / cb[ok]
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(point), float(lo), float(hi)
