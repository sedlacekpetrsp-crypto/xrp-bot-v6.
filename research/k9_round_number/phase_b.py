"""K9 fáze B (výnos po průrazu kulaté úrovně) — implementace PROTOCOL.md dodatek 2 (+ oprava 1).

STAV: kód připravený PŘED daty. Na tržních datech se smí spustit jen přes `phase_b_run.py`, který vyžaduje
řádek vlastníka „SCHVÁLENO: výkonnost K9“ (fail closed). Testy používají výhradně syntetické svíčky.

Pravidla (dodatek 2, body 1–6):
- událost = první dotyk z fáze A (`events.detect_touches`, stejné úrovně S, kulaté off 0 / placebo 0,37 + 0,73);
- směr = směr průrazu; vstup = open minuty t+1; výstup = close minuty t+H; bez stopu/TP/páky, 1 jednotka notional;
- na aktivu max. 1 pozice (zvlášť „portfolio“ kulaté a placebo); signál v době pozice se ignoruje — pozice blokuje
  minuty t..t+H i tehdy, když je obchod neplatný (chybějící minuta), aby počty odpovídaly předpočtené síle;
- chybějící minuta v okně t+1..t+H ⇒ obchod neplatný (vykázat podíl; > 1 % ⇒ INCONCLUSIVE);
- náklady 0,14 % round trip ×1/×2/×3; funding 0,03 % nepříznivě za každé 00/08/16 UTC v intervalu
  [vstup, konec minuty t+H) — vstup přesně v čase fundingu se počítá (konzervativně); funding × stejný multiplikátor;
- vývoj (t < 2024-01-01): ekonomická předbrána max_H G_dev(H) ≥ 0,42 %, jinak NO-GO a závěr se NEOTEVÍRÁ;
  H* = argmax čistého ×1 ve vývoji (shoda ⇒ kratší H);
- závěr (t ≥ 2024-01-01), jen H*: brány a)–g) dodatku 2.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.k9_round_number.audit import DEV_END
from research.k9_round_number.events import LOOKBACK, PLACEBO_OFFSETS, ROUND_OFFSETS, detect_touches
from research.k9_round_number.phase_a import to_minute_grid
from tools.research.deflated_sharpe import dsr_from_returns

HORIZONS = (15, 60)
COST_RT = 0.0014            # 2 × (0,05 % taker + 0,02 % skluz)
FUNDING_PER_CROSS = 0.0003  # 3× základní sazba, vždy nepříznivě
MULTS = (1, 2, 3)
PREGATE_GROSS = 0.0042      # 3 × náklad ×1
REPS = 10_000
SEED = 20261117
N_RANDOM = 20              # oprava 2: až 20 párovaných replik na signál (místo 5 náhodných)
MATCH_WINDOW = 60          # oprava 2: párovací proměnné z minut i−60..i−1 (jen PIT minulost)
MATCH_CALIPER = float(np.log(2.0))  # |ln poměru| RV i likvidity ≤ ln 2
MAX_MISSING_FRAC = 0.01
MAX_INVALID_REP_FRAC = 0.05
DSR_N = 225                 # oprava 1 dodatku 2: 222 (K7 při spuštění, registr) + K9 fáze A + 2 varianty H
DSR_N_GATE = 450            # oprava 2: brána e) při 2× doloženém N (225 není auditovaná horní mez); 225 jen informačně
FUNDING_MODEL = ("MODELOVANÝ nepříznivý funding 0,03 %/překročení 00/08/16 UTC (předregistrovaná citlivost), "
                 "NE historická PIT sazba ⇒ net není skutečný P/L")
DSR_VAR_ANNUAL = 0.5        # R10 předpoklad ⇒ DSR podmíněné
DSR_MIN = 0.95
POWER_MIN = 0.80
POWER_KEY = {15: "pw_mu0.0014_sd0.008_rho0.3", 60: "pw_mu0.0014_sd0.016_rho0.3"}
FINAL_YEARS = (2024, 2025, 2026)
TRADE_COLS = ["asset", "kind", "time", "level", "direction", "H", "entry_time", "exit_time", "entry", "exit",
              "gross", "funding_crossings", "net_x1", "net_x2", "net_x3"]


# ---------------------------------------------------------------- obchody
def _funding_crossings(entry_min: int, end_min: int) -> int:
    """Počet okamžiků k·480 min (00/08/16 UTC) v [entry_min, end_min)."""
    return int(-(-end_min // 480) - -(-entry_min // 480))


def _epoch_minutes(idx: pd.DatetimeIndex) -> np.ndarray:
    """Minuty od epochy nezávisle na rozlišení indexu (pandas 3 může mít us místo ns)."""
    if not len(idx):
        return np.array([], np.int64)
    return np.asarray((idx - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(minutes=1), dtype=np.int64)


def build_trades(grid: pd.DataFrame, events: pd.DataFrame, H: int, asset: str = "", kind: str = "") -> tuple[pd.DataFrame, dict]:
    """Obchody z událostí jednoho aktiva a jednoho „portfolia“ (kulaté nebo placebo). `grid` = úplná minutová mřížka."""
    stats = {"signals": int(len(events)), "blocked": 0, "taken": [], "invalid": [],
             "signal_times": sorted(pd.to_datetime(events["time"], utc=True)) if len(events) else []}
    if events.empty:
        return pd.DataFrame(columns=TRADE_COLS), stats
    idx = grid.index
    o, c = grid["open"].to_numpy(float), grid["close"].to_numpy(float)
    miss = np.concatenate([[0], np.cumsum(~np.isfinite(o) | ~np.isfinite(c) | (o <= 0) | (c <= 0))])
    ev = events.assign(time=pd.to_datetime(events["time"], utc=True)).sort_values(["time", "level"], kind="stable")
    rows, busy_until = [], None
    epoch_min = _epoch_minutes(idx)
    for t, level, d in zip(ev["time"], ev["level"], ev["direction"]):
        if busy_until is not None and t < busy_until:
            stats["blocked"] += 1
            continue
        busy_until = t + pd.Timedelta(minutes=H + 1)
        stats["taken"].append(t)
        i = idx.get_indexer([t])[0]
        if i < 0 or i + H >= len(idx) or miss[i + H + 1] - miss[i + 1] > 0:
            stats["invalid"].append(t)
            continue
        entry, exit_ = o[i + 1], c[i + H]
        gross = float(d) * (exit_ / entry - 1.0)
        fc = _funding_crossings(int(epoch_min[i + 1]), int(epoch_min[i + H]) + 1)
        r = {"asset": asset, "kind": kind, "time": t, "level": float(level), "direction": int(d), "H": H,
             "entry_time": idx[i + 1], "exit_time": idx[i + H], "entry": entry, "exit": exit_, "gross": gross,
             "funding_crossings": fc}
        for m in MULTS:
            r[f"net_x{m}"] = gross - m * (COST_RT + FUNDING_PER_CROSS * fc)
        rows.append(r)
    return pd.DataFrame(rows, columns=TRADE_COLS), stats


def asset_trades(df: pd.DataFrame, step: float, H: int, asset: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Detekce (stejná jako fáze A) + obchody kulaté a placebo. Vrací (trades, grid, stats)."""
    g = to_minute_grid(df)
    out, st = [], {}
    for kind, offs in (("round", ROUND_OFFSETS), ("placebo", PLACEBO_OFFSETS)):
        ev = pd.concat([detect_touches(g, step, off, LOOKBACK) for off in offs], ignore_index=True)
        tr, s = build_trades(g, ev, H, asset, kind)
        out.append(tr)
        st[kind] = s
    return pd.concat(out, ignore_index=True), g, st


def missing_frac(stats: dict, period: str) -> float:
    """Podíl neplatných (chybějící minuta) mezi přijatými signály v období; stats = {asset: {kind: stats}}."""
    def n(key):
        return sum(int(((pd.DatetimeIndex(s[key]) < DEV_END) if period == "dev"
                        else (pd.DatetimeIndex(s[key]) >= DEV_END)).sum())
                   for st in stats.values() for s in st.values() if len(s[key]))
    taken = n("taken")
    return n("invalid") / taken if taken else 0.0


def split(tr: pd.DataFrame, period: str) -> pd.DataFrame:
    t = pd.to_datetime(tr["time"], utc=True)
    return tr[t < DEV_END] if period == "dev" else tr[t >= DEV_END]


def match_features(grid: pd.DataFrame, window: int = MATCH_WINDOW) -> tuple[np.ndarray, np.ndarray]:
    """PIT párovací proměnné pro minutu i jen z minut i−window..i−1 (signální minuta ani budoucnost se nepoužijí):
    rv = směrodatná odchylka 1m log výnosů close, liq = součet quote objemu (volume × close). Chybějící minuta v okně ⇒ NaN."""
    c = grid["close"].to_numpy(float)
    v = grid["volume"].to_numpy(float)
    r = pd.Series(np.log(c)).diff()
    rv = r.rolling(window - 1, min_periods=window - 1).std(ddof=1).shift(1).to_numpy()
    liq = pd.Series(v * c).rolling(window, min_periods=window).sum().shift(1).to_numpy()
    return rv, liq


def random_trades(grid: pd.DataFrame, trades: pd.DataFrame, H: int, rng: np.random.Generator,
                  n: int = N_RANDOM, caliper: float = MATCH_CALIPER, exclude_times=None,
                  diag: dict | None = None) -> pd.DataFrame:
    """Benchmark d) (oprava 2): pro každý signál až n minut téhož aktiva, dne a UTC hodiny (bez signální minuty,
    jen úplné okno), PÁROVANÝCH na předchozí realizovanou volatilitu a likviditu (`match_features`, jen PIT minulost):
    |ln(rv_c/rv_s)| ≤ caliper a |ln(liq_c/liq_s)| ≤ caliper; z vyhovujících n nejbližších podle součtu |ln poměrů|,
    shody náhodně (rng). Bez vracení. Signál bez párovatelného kandidáta nemá repliku (ztráta podpory se vykazuje
    v `random_support`). Párování nezávisí na výnosu.
    Oprava 3 (dialog 0367/0369): kandidát nesmí být ŽÁDNÁ signální minuta téhož aktiva (`exclude_times` = všechny
    detekované kulaté dotyky vč. blokovaných; default = časy v `trades`), ne jen vlastní signál. Počet vyřazených
    kandidátů se přičte do `diag["excluded_signal_minutes"]`."""
    cols = ["asset", "time", "src_time", "gross", "net_x1", "match_dist"]
    if trades.empty:
        return pd.DataFrame(columns=cols)
    idx = grid.index
    o, c = grid["open"].to_numpy(float), grid["close"].to_numpy(float)
    miss = np.concatenate([[0], np.cumsum(~np.isfinite(o) | ~np.isfinite(c) | (o <= 0) | (c <= 0))])
    rv, liq = match_features(grid)
    epoch_min = _epoch_minutes(idx)
    excl_src = trades["time"] if exclude_times is None else list(exclude_times) + list(trades["time"])
    excl_pos = idx.get_indexer(pd.DatetimeIndex(pd.to_datetime(pd.Series(list(excl_src)), utc=True)))
    excl = set(int(i) for i in excl_pos if i >= 0)
    if diag is not None:
        diag.setdefault("excluded_signal_minutes", 0)
    rows = []
    for asset, t, d in zip(trades["asset"], trades["time"], trades["direction"]):
        s_i = idx.get_indexer([pd.Timestamp(t)])[0]
        h0 = pd.Timestamp(t).floor("h")
        start = idx.get_indexer([h0])[0]
        if start < 0 or s_i < 0 or not (rv[s_i] > 0 and liq[s_i] > 0):
            continue
        hour = range(start, min(start + 60, len(idx)))
        if diag is not None:
            diag["excluded_signal_minutes"] += sum(1 for i in hour if i != s_i and i in excl)
        cand = [i for i in hour
                if i != s_i and i not in excl and i + H < len(idx) and miss[i + H + 1] - miss[i + 1] == 0 and rv[i] > 0 and liq[i] > 0]
        if not cand:
            continue
        cand = np.array(cand)
        d_rv = np.abs(np.log(rv[cand] / rv[s_i]))
        d_lq = np.abs(np.log(liq[cand] / liq[s_i]))
        ok = (d_rv <= caliper) & (d_lq <= caliper)
        cand, dist = cand[ok], (d_rv + d_lq)[ok]
        if not len(cand):
            continue
        tie = rng.permutation(len(cand))
        order = np.lexsort((tie, dist))[:n]
        for i, dd in zip(cand[order], dist[order]):
            g = float(d) * (c[i + H] / o[i + 1] - 1.0)
            fc = _funding_crossings(int(epoch_min[i + 1]), int(epoch_min[i + H]) + 1)
            rows.append({"asset": asset, "time": idx[i], "src_time": t, "gross": g,
                         "net_x1": g - COST_RT - FUNDING_PER_CROSS * fc, "match_dist": float(dd)})
    return pd.DataFrame(rows, columns=cols)


def random_support(signals: pd.DataFrame, rand: pd.DataFrame, n: int = N_RANDOM,
                   excluded_signal_minutes: int | None = None) -> dict:
    """Ztráta podpory párovaného benchmarku d): kolik signálů má ≥ 1 / plných n replik (+ oprava 3: počet
    kandidátních minut vyřazených, protože byly jinou signální minutou)."""
    ns = int(len(signals))
    per = rand.groupby(["asset", "src_time"]).size() if len(rand) else pd.Series(dtype=int)
    return {"n_signals": ns, "excluded_signal_minutes": excluded_signal_minutes, "with_any": int(len(per)), "with_full": int((per >= n).sum()),
            "frac_unmatched": float(1 - len(per) / ns) if ns else float("nan"),
            "mean_reps": float(per.mean()) if len(per) else 0.0}


# ---------------------------------------------------------------- statistika
def _day_sums(df: pd.DataFrame, col: str, days: np.ndarray, time_col: str = "time") -> tuple[np.ndarray, np.ndarray]:
    d = pd.to_datetime(df[time_col], utc=True).dt.floor("D")
    g = df.assign(_d=d).groupby("_d")[col].agg(["sum", "count"]).reindex(days, fill_value=0)
    return g["sum"].to_numpy(float), g["count"].to_numpy(float)


def boot(a: pd.DataFrame, col: str, b: pd.DataFrame | None = None, col_b: str | None = None,
         reps: int = REPS, seed: int = SEED, b_time_col: str = "src_time") -> dict:
    """Průměr col v a (nebo rozdíl průměrů a − b) + 95% CI blokovým bootstrapem přes kalendářní dny.

    Den obchodu = den signálu; u náhodného benchmarku den zdrojového signálu (`src_time`), takže se převzorkují
    stejné dny pro obě řady."""
    frames = [(a, "time")] + ([(b, b_time_col)] if b is not None else [])
    days = np.array(sorted(set().union(*[set(pd.to_datetime(f[t], utc=True).dt.floor("D")) for f, t in frames])))
    if len(days) == 0 or a.empty or (b is not None and b.empty):
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan"), "valid_reps": 0, "reps": reps,
                "invalid_frac": 1.0, "n_a": int(len(a)), "n_b": int(len(b)) if b is not None else None}
    sa, ca = _day_sums(a, col, days)
    point = float(a[col].mean())
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(days), size=(reps, len(days)))
    SA, CA = sa[idx].sum(1), ca[idx].sum(1)
    ok = CA > 0
    est = np.where(ok, SA / np.where(ok, CA, 1), np.nan)
    if b is not None:
        sb, cb = _day_sums(b, col_b or col, days, b_time_col)
        point -= float(b[col_b or col].mean())
        SB, CB = sb[idx].sum(1), cb[idx].sum(1)
        okb = CB > 0
        est = est - np.where(okb, SB / np.where(okb, CB, 1), np.nan)
        ok &= okb
    lo, hi = (np.percentile(est[ok], [2.5, 97.5]) if ok.any() else (np.nan, np.nan))
    return {"point": point, "lo": float(lo), "hi": float(hi), "valid_reps": int(ok.sum()), "reps": int(reps),
            "invalid_frac": float(1 - ok.mean()), "n_a": int(len(a)), "n_b": int(len(b)) if b is not None else None}


def daily_pnl(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, col: str = "net_x1") -> pd.Series:
    """Denní PnL (součet přes aktiva, 1 jednotka notional na obchod), dny bez obchodu = 0; den = den vstupu."""
    days = pd.date_range(pd.Timestamp(start).tz_convert("UTC").floor("D"),
                         pd.Timestamp(end).tz_convert("UTC").floor("D"), freq="D")
    if trades.empty:
        return pd.Series(0.0, index=days)
    d = pd.to_datetime(trades["entry_time"], utc=True).dt.floor("D")
    return trades.groupby(d)[col].sum().reindex(days, fill_value=0.0)


def max_drawdown(pnl: pd.Series) -> float:
    eq = pnl.cumsum()
    return float((eq.cummax().clip(lower=0) - eq).max()) if len(eq) else 0.0


def dsr(pnl: pd.Series, n: int = DSR_N, var_annual: float = DSR_VAR_ANNUAL) -> dict:
    try:
        r = dsr_from_returns(pnl.to_numpy(float), n, var_annual / 365)
    except ValueError as e:  # nulový rozptyl / < 3 dny
        return {"dsr": float("nan"), "error": str(e), "n_trials": n}
    r["sharpe_annual"] = r["sharpe_per_period"] * np.sqrt(365)
    return r


# ---------------------------------------------------------------- vývoj a výběr H
def dev_selection(dev: dict[int, pd.DataFrame], missing: dict[int, float]) -> dict:
    """dev[H] = obchody vývojového období (kulaté). Ekonomická předbrána + výběr H* (před otevřením závěru)."""
    per_h = {}
    for H, tr in dev.items():
        r = tr[tr["kind"] == "round"]
        per_h[H] = {"n": int(len(r)), "gross": float(r["gross"].mean()) if len(r) else float("nan"),
                    "net_x1": float(r["net_x1"].mean()) if len(r) else float("nan"),
                    "missing_frac": float(missing.get(H, 0.0))}
    gmax = max((v["gross"] for v in per_h.values() if np.isfinite(v["gross"])), default=float("nan"))
    if any(not np.isfinite(v["missing_frac"]) or v["missing_frac"] > MAX_MISSING_FRAC for v in per_h.values()):
        return {"per_h": per_h, "gross_max": gmax, "final_open": False, "h_star": None,
                "verdict": "INCONCLUSIVE (chybějící minuty > 1 %)"}
    if not (gmax >= PREGATE_GROSS):
        return {"per_h": per_h, "gross_max": gmax, "final_open": False, "h_star": None,
                "verdict": "NO-GO (ekonomická předbrána: hrubý průměr < 0,42 %) — závěr NEOTEVŘEN"}
    h_star = sorted(per_h, key=lambda h: (-per_h[h]["net_x1"], h))[0]
    return {"per_h": per_h, "gross_max": gmax, "final_open": True, "h_star": int(h_star),
            "verdict": "předbrána splněna ⇒ závěr jen pro H*"}


# ---------------------------------------------------------------- závěr
def stability(final_round: pd.DataFrame) -> dict:
    t = pd.to_datetime(final_round["time"], utc=True)
    by_asset = final_round.groupby("asset")["net_x1"].mean()
    by_year = final_round.groupby(t.dt.year)["net_x1"].mean().reindex(FINAL_YEARS)
    return {"by_asset": {k: float(v) for k, v in by_asset.items()},
            "by_year": {int(k): (float(v) if pd.notna(v) else None) for k, v in by_year.items()},
            "assets_pos": int((by_asset > 0).sum()), "years_pos": int((by_year > 0).sum()),
            "ok": bool((by_asset > 0).sum() >= 2 and (by_year > 0).sum() >= 2)}


def evaluate_final(rnd: pd.DataFrame, plc: pd.DataFrame, rand: pd.DataFrame, pnl: pd.Series, power: float | None,
                   missing_frac: float, reps: int = REPS) -> dict:
    E = boot(rnd, "net_x1", reps=reps)
    dlt = boot(rnd, "gross", plc, "gross", reps=reps, b_time_col="time")
    rd = boot(rnd, "gross", rand, "gross", reps=reps, b_time_col="src_time")
    x2 = float(rnd["net_x2"].mean()) if len(rnd) else float("nan")
    x3 = float(rnd["net_x3"].mean()) if len(rnd) else float("nan")
    ds = dsr(pnl, DSR_N_GATE)
    ds_info = dsr(pnl, DSR_N)
    st = stability(rnd) if len(rnd) else {"ok": False}
    g = {"a": bool(E["point"] > 0 and E["lo"] > 0), "b": bool(x2 > 0), "c": bool(dlt["point"] > 0 and dlt["lo"] > 0),
         "d": bool(rd["point"] > 0 and rd["lo"] > 0), "e": bool(ds.get("dsr", float("nan")) >= DSR_MIN),
         "f": bool(st["ok"]), "g": bool(power is not None and power >= POWER_MIN)}
    inval = max(E["invalid_frac"], dlt["invalid_frac"], rd["invalid_frac"])
    # oprava 2: ekonomické NO-GO důvody se vykazují vždy samostatně, formální verdikt se jimi nemění
    econ = [k for k in ("a", "c") if not g[k]]
    if not np.isfinite(missing_frac) or missing_frac > MAX_MISSING_FRAC:
        verdict = "INCONCLUSIVE (chybějící minuty > 1 %)"
    elif inval > MAX_INVALID_REP_FRAC:
        verdict = "INCONCLUSIVE (neplatné repliky)"
    elif not g["g"]:
        verdict = "INCONCLUSIVE (nízká síla)"
    elif all(g.values()):
        verdict = "GO (jen návrh forward PAPER; samostatné schválení vlastníka)"
    else:
        verdict = "NO-GO"
    return {"verdict": verdict, "gates": g, "economic_nogo_reasons": econ, "funding_model": FUNDING_MODEL,
            "dsr_n225_info": ds_info, "E_net_x1": E, "net_x2_mean": x2, "net_x3_mean": x3,
            "delta_vs_placebo": dlt, "delta_vs_random": rd, "dsr": ds, "stability": st, "power": power,
            "missing_frac": missing_frac, "max_invalid_frac": float(inval)}


def breakdown(tr: pd.DataFrame) -> pd.DataFrame:
    """Povinný rozpad (ne brána): aktivum × rok × směr × UTC hodina."""
    t = pd.to_datetime(tr["time"], utc=True)
    g = tr.assign(year=t.dt.year, hour=t.dt.hour).groupby(["asset", "year", "direction", "hour"])
    return g.agg(n=("gross", "size"), gross=("gross", "mean"), net_x1=("net_x1", "mean"),
                 net_x2=("net_x2", "mean"), net_x3=("net_x3", "mean")).reset_index()


def benchmarks(grids: dict[str, pd.DataFrame], rnd: pd.DataFrame, start: pd.Timestamp) -> dict:
    """B&H stejně vážený (open první minuty závěru → close poslední) a long-only exposure-matched."""
    bh = {}
    for a, g in grids.items():
        s = g[g.index >= start].dropna(subset=["open", "close"])
        if len(s):
            bh[a] = float(s["close"].iloc[-1] / s["open"].iloc[0] - 1)
    long_gross = (rnd["exit"] / rnd["entry"] - 1) if len(rnd) else pd.Series(dtype=float)
    long_net = long_gross - COST_RT - FUNDING_PER_CROSS * rnd["funding_crossings"] if len(rnd) else long_gross
    return {"buy_hold_per_asset": bh, "buy_hold_equal_weight": float(np.mean(list(bh.values()))) if bh else None,
            "exposure_matched_long": {"n": int(len(long_gross)),
                                      "gross_mean": float(long_gross.mean()) if len(long_gross) else None,
                                      "net_x1_mean": float(long_net.mean()) if len(long_net) else None,
                                      "net_x1_sum": float(long_net.sum()) if len(long_net) else None}}


def exposure(grids: dict[str, pd.DataFrame], rnd: pd.DataFrame, start: pd.Timestamp) -> dict:
    out = {}
    for a, g in grids.items():
        mins = int(g[g.index >= start]["close"].notna().sum())
        held = int(rnd[rnd["asset"] == a]["H"].sum())
        out[a] = held / mins if mins else None
    return out
