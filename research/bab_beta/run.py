"""Betting-against-beta, koš 8 USDT-M perpů (R11) — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.bab_beta.run --cache /tmp/vision-bab --outdir research/bab_beta
"""
import argparse
import csv
import hashlib
import io
import json
import math
import sys
import urllib.error
import urllib.request
import zipfile
from bisect import bisect_left, bisect_right
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ASSETS = ("BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT")
FIRST_MONTH = (2020, 1)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
GRID = [(w, h) for w in (60, 120) for h in (7, 14)]
PERIODS = {"tuning": ("2020-10-05", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
WF_YEARS = (2021, 2022, 2023, 2024)
START_EQUITY = 10_000.0
GROSS = 0.60
N_SIDE = 3
MIN_ELIGIBLE = 6
BETA_FLOOR = 0.25
LIQ_MULT = 2.0
DSR_N, DSR_VAR_ANNUAL = 166, 0.5
DAY_MS = 86_400_000
EPOCH = date(1970, 1, 1)


def vt(w, h):
    return f"W{w}_H{h}"


def day_ms(d):
    return (d - EPOCH).days * DAY_MS


def ms_day(ms):
    return EPOCH + timedelta(days=ms // DAY_MS)


# ------------------------------------------------------------------ data
def months():
    y, m = FIRST_MONTH
    while (y, m) <= LAST_MONTH:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def _csv_rows(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    return [r for r in csv.reader(io.StringIO(text)) if r and r[0].strip().isdigit()]


def _ms(ts):
    return ts // 1000 if ts > 10 ** 14 else ts


def parse_klines(payload):
    """→ {date: (open, high, low, close)}"""
    out = {}
    for r in _csv_rows(payload):
        out[ms_day(_ms(int(r[0])))] = (float(r[1]), float(r[2]), float(r[3]), float(r[4]))
    return out


def parse_funding(payload):
    """fundingRate: calc_time, funding_interval_hours, last_funding_rate → [(ms, sazba)]"""
    return [(_ms(int(r[0])), float(r[2])) for r in _csv_rows(payload)]


def urls(asset):
    base = "https://data.binance.vision/data/futures/um/monthly"
    for y, m in months():
        tag = f"{y}-{m:02d}"
        yield "kl", (y, m), f"{base}/klines/{asset}/1d/{asset}-1d-{tag}.zip"
        yield "fr", (y, m), f"{base}/fundingRate/{asset}/{asset}-fundingRate-{tag}.zip"


def load(cache, fetcher=fetch):
    market, funding, manifest, missing, fatal = {}, {}, [], [], []
    for a in ASSETS:
        bars, fund = {}, {}
        present, miss = {"kl": [], "fr": []}, {"kl": [], "fr": []}
        for kind, ym, url in urls(a):
            p = Path(cache) / kind / url.rsplit("/", 1)[1]
            if not p.exists():
                try:
                    payload = fetcher(url)
                except urllib.error.HTTPError as e:
                    missing.append({"url": url, "http": e.code})
                    miss[kind].append(ym)
                    continue
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(payload)
            payload = p.read_bytes()
            present[kind].append(ym)
            if kind == "kl":
                rows = parse_klines(payload)
                bars.update(rows)
            else:
                rows = parse_funding(payload)
                for ts, rate in rows:
                    if ts in fund and fund[ts] != rate:
                        raise ValueError(f"konfliktní duplicitní funding {a} {ts}")
                    fund[ts] = rate
            manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)})
        for kind in ("kl", "fr"):
            if present[kind]:
                first = min(present[kind])
                fatal += [{"asset": a, "kind": kind, "month": f"{y}-{m:02d}"} for (y, m) in miss[kind] if (y, m) > first]
            else:
                fatal.append({"asset": a, "kind": kind, "month": "all"})
        market[a] = bars
        funding[a] = sorted(fund.items())
    if fatal:
        raise SystemExit(f"FATAL: chybějící archivy po začátku obchodování: {fatal}")
    return market, funding, manifest, missing


def data_gaps(market):
    """Chybějící dny mezi první a poslední svíčkou aktiva (informačně do results.json)."""
    out = {}
    for a, bars in market.items():
        ds = sorted(bars)
        gaps, d = [], ds[0]
        while d <= ds[-1]:
            if d not in bars:
                gaps.append(d.isoformat())
            d += timedelta(days=1)
        out[a] = gaps
    return out


# ------------------------------------------------------------------ signál
class Ctx:
    """Předpočítané denní výnosy a tržní výnos m_t."""

    def __init__(self, market, funding):
        self.market, self.funding = market, funding
        self.fund_ts = {a: [t for t, _ in funding.get(a, [])] for a in market}
        self.ret = {}
        for a, bars in market.items():
            r = {}
            for d, b in bars.items():
                p = bars.get(d - timedelta(days=1))
                if p is not None and p[3] > 0:
                    r[d] = b[3] / p[3] - 1
            self.ret[a] = r
        days = set()
        for r in self.ret.values():
            days |= set(r)
        self.mkt = {}
        for d in days:
            xs = [self.ret[a][d] for a in market if d in self.ret[a]]
            self.mkt[d] = sum(xs) / len(xs)

    def last_close(self, a, d):
        """Close dne d, nebo poslední známá close před d."""
        bars = self.market[a]
        x = d
        for _ in range(60):
            if x in bars:
                return bars[x][3]
            x -= timedelta(days=1)
        raise ValueError(f"chybí cena {a} kolem {d}")


def betas(ctx, decision, w):
    """β_i z W denních výnosů končících D − 2. Jen způsobilá aktiva (celé okno + svíčka dne D)."""
    end = decision - timedelta(days=2)
    window = [end - timedelta(days=k) for k in range(w)]
    out = {}
    for a in ctx.market:
        if decision not in ctx.market[a]:
            continue
        if any(d not in ctx.ret[a] for d in window):
            continue
        xs = [ctx.ret[a][d] for d in window]
        ms = [ctx.mkt[d] for d in window]
        mx, mm = sum(xs) / w, sum(ms) / w
        cov = sum((x - mx) * (m - mm) for x, m in zip(xs, ms)) / (w - 1)
        var = sum((m - mm) ** 2 for m in ms) / (w - 1)
        if var > 0:
            out[a] = cov / var
    return out


def select(beta, reverse=False):
    """→ [(asset, side, weight, beta)] nebo [] (hotovost)."""
    if len(beta) < MIN_ELIGIBLE:
        return []
    order = sorted(beta, key=lambda a: (beta[a], a))
    low, high = order[:N_SIDE], order[-N_SIDE:]
    longs, shorts = (high, low) if reverse else (low, high)
    bl = max(BETA_FLOOR, sum(beta[a] for a in longs) / N_SIDE)
    bs = max(BETA_FLOOR, sum(beta[a] for a in shorts) / N_SIDE)
    L, S = 1 / bl, 1 / bs
    k = GROSS / (L + S)
    L, S = L * k, S * k
    return [(a, 1, L / N_SIDE, beta[a]) for a in longs] + [(a, -1, S / N_SIDE, beta[a]) for a in shorts]


# ------------------------------------------------------------------ simulace
class Leg:
    def __init__(self, ctx, asset, side, weight, beta, entry_day, exit_day, equity, mult):
        self.ctx, self.a, self.side, self.weight, self.beta = ctx, asset, side, weight, beta
        self.entry_day, self.exit_day, self.mult = entry_day, exit_day, mult
        o = ctx.market[asset][entry_day][0]
        self.entry_open = o
        self.entry_fill = o * (1 + side * SLIP * mult)
        self.notional = equity * weight
        self.qty = self.notional / self.entry_fill
        self.fee_in = self.notional * FEE * mult
        self.liq_day = None
        self.missing_liq_days = 0
        if side < 0:
            d = entry_day
            while d < exit_day:
                b = ctx.market[asset].get(d)
                if b is None:
                    self.missing_liq_days += 1
                elif b[1] >= LIQ_MULT * self.entry_fill:
                    self.liq_day = d
                    break
                d += timedelta(days=1)

    def funding_until(self, end_ms):
        """Funding cash flow pro události vstup < t < end_ms (a t < výstup)."""
        lo = day_ms(self.entry_day)
        hi = min(end_ms, day_ms(self.exit_day))
        ts = self.ctx.fund_ts.get(self.a, [])
        i, j = bisect_right(ts, lo), bisect_left(ts, hi)
        tot = 0.0
        for t, rate in self.ctx.funding[self.a][i:j]:
            d = ms_day(t)
            b = self.ctx.market[self.a].get(d)
            px = b[0] if b else self.ctx.last_close(self.a, d)
            tot += -self.side * rate * self.qty * px
        return tot

    def _liq_end_ms(self):
        return day_ms(self.liq_day + timedelta(days=1))

    def mtm(self, d):
        """Hodnota nohy (P/L) na konci dne d."""
        if self.liq_day is not None and d >= self.liq_day:
            return -self.notional - self.fee_in + self.funding_until(self._liq_end_ms())
        px = self.ctx.last_close(self.a, d)
        return (self.side * self.qty * (px - self.entry_fill) - self.fee_in
                + self.funding_until(day_ms(d + timedelta(days=1))))

    def close(self):
        if self.liq_day is not None:
            fund = self.funding_until(self._liq_end_ms())
            net = -self.notional - self.fee_in + fund
            exit_px, exit_fill, fee_out, shifted = None, None, 0.0, 0
            gross = -self.notional + fund
        else:
            b = self.ctx.market[self.a].get(self.exit_day)
            shifted = 0 if b else 1
            exit_px = b[0] if b else self.ctx.last_close(self.a, self.exit_day - timedelta(days=1))
            exit_fill = exit_px * (1 - self.side * SLIP * self.mult)
            fee_out = self.qty * exit_fill * FEE * self.mult
            fund = self.funding_until(day_ms(self.exit_day))
            net = self.side * self.qty * (exit_fill - self.entry_fill) + fund - self.fee_in - fee_out
            gross = self.side * self.qty * (exit_px - self.entry_open) + fund
        return {"asset": self.a, "side": "LONG" if self.side > 0 else "SHORT", "beta": round(self.beta, 6),
                "weight": round(self.weight, 6), "entry_day": self.entry_day.isoformat(),
                "exit_day": self.exit_day.isoformat(), "entry_fill": self.entry_fill,
                "exit_fill": exit_fill, "qty": self.qty, "notional": self.notional, "funding": fund,
                "costs": gross - net, "gross_pnl": gross, "net_pnl": net,
                "liquidated": int(self.liq_day is not None), "exit_shifted": shifted,
                "missing_liq_days": self.missing_liq_days}


def first_monday(d):
    return d + timedelta(days=(7 - d.weekday()) % 7)


def simulate(ctx, start, end, w, h, mult, reverse=False):
    realized = START_EQUITY
    legs, rows, curve, decisions = [], [], {}, []
    nxt = first_monday(start)
    d = start
    while d <= end:
        if nxt is not None and d == nxt:
            for leg in legs:
                r = leg.close()
                r["decision_day"] = leg.entry_day.isoformat()
                rows.append(r)
                realized += r["net_pnl"]
            legs = []
            if d + timedelta(days=h) <= end:
                pick = select(betas(ctx, d, w), reverse)
                ex = d + timedelta(days=h)
                legs = [Leg(ctx, a, s, wt, b, d, ex, realized, mult) for a, s, wt, b in pick]
                decisions.append({"day": d.isoformat(), "legs": len(pick)})
                nxt = ex
            else:
                nxt = None
        curve[d] = realized + sum(leg.mtm(d) for leg in legs)
        d += timedelta(days=1)
    assert not legs, "otevřené nohy po konci bloku"
    return rows, curve, decisions


def buy_hold(ctx, start, end, mult, assets=ASSETS):
    fee, slip = FEE * mult, SLIP * mult
    alloc = START_EQUITY / len(assets)
    pos, cash = {}, 0.0
    for a in assets:
        b = ctx.market[a].get(start)
        if b is None:
            cash += alloc
            continue
        fill = b[0] * (1 + slip)
        pos[a] = (alloc / fill, fill, alloc * fee)
    curve, d = {}, start
    while d <= end:
        v = cash
        for a, (q, fill, fin) in pos.items():
            px = ctx.last_close(a, d)
            if d == end:
                px_f = px * (1 - slip)
                v += alloc + q * (px_f - fill) - fin - q * px_f * fee
            else:
                v += alloc + q * (px - fill) - fin
        curve[d] = v
        d += timedelta(days=1)
    return curve


# ------------------------------------------------------------------ metriky
def daily_returns(curve, start_equity=START_EQUITY):
    vals = [curve[d] for d in sorted(curve)]
    return [vals[0] / start_equity - 1] + [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]


def metrics(curve, rows, start_equity=START_EQUITY):
    vals = [curve[d] for d in sorted(curve)]
    rets = daily_returns(curve, start_equity)
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
    peak, mdd = start_equity, 0.0
    for v in vals:
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak)
    tr = sorted((r["net_pnl"] for r in rows), reverse=True)
    gw = sum(x for x in tr if x > 0)
    gl = -sum(x for x in tr if x <= 0)
    net = vals[-1] - start_equity
    lsum = sum(tr)
    return {"final_equity": vals[-1], "net_pnl": net, "return_pct": 100 * (vals[-1] / start_equity - 1),
            "sharpe": (mu / sd * math.sqrt(365)) if sd > 0 else 0.0, "max_drawdown_pct": 100 * mdd,
            "trades": len(tr), "ledger_sum_net_pnl": lsum,
            "profit_factor": (gw / gl) if gl > 0 else (math.inf if gw > 0 else 0.0),
            "win_rate_pct": 100 * sum(1 for x in tr if x > 0) / len(tr) if tr else 0.0,
            "net_without_top3": net - sum(x for x in tr[:3] if x > 0),
            "funding": sum(r["funding"] for r in rows), "costs": sum(r["costs"] for r in rows),
            "liquidations": sum(r["liquidated"] for r in rows),
            "exit_shifted": sum(r["exit_shifted"] for r in rows),
            "missing_liq_days": sum(r["missing_liq_days"] for r in rows)}


def regress_beta(xs, ms):
    n = len(xs)
    mx, mm = sum(xs) / n, sum(ms) / n
    cov = sum((x - mx) * (m - mm) for x, m in zip(xs, ms))
    var = sum((m - mm) ** 2 for m in ms)
    vx = sum((x - mx) ** 2 for x in xs)
    return cov / var if var else 0.0, cov / math.sqrt(var * vx) if var and vx else 0.0


def exposure(ctx, curve):
    ds = sorted(curve)
    xs, ms, bs = [], [], []
    for i in range(1, len(ds)):
        d = ds[i]
        if d in ctx.mkt and d in ctx.ret["BTCUSDT"]:
            xs.append(curve[d] / curve[ds[i - 1]] - 1)
            ms.append(ctx.mkt[d])
            bs.append(ctx.ret["BTCUSDT"][d])
    beta_m, corr_m = regress_beta(xs, ms)
    _, corr_btc = regress_beta(xs, bs)
    return {"beta_to_basket": beta_m, "corr_to_basket": corr_m, "corr_to_btc": corr_btc, "days": len(xs)}


def span(period):
    return tuple(date.fromisoformat(x) for x in PERIODS[period])


def evaluate(market, funding):
    ctx = Ctx(market, funding)
    res = {"grid_tuning_x1": {}, "strategy": {}, "buy_hold": {}, "neighbors_validation_x2": {},
           "walk_forward_x2": {}, "info": {}, "blocks": {}}
    ledger = []

    def run(s, e, w, h, mult, period, mode="BAB"):
        rows, cv, dec = simulate(ctx, s, e, w, h, mult, reverse=(mode == "REVERSE"))
        tag = {"variant": vt(w, h), "mode": mode, "period": period, "cost_multiplier": mult}
        ledger.extend({**tag, **r} for r in rows)
        m = metrics(cv, rows)
        m["decisions"] = len(dec)
        m["cash_decisions"] = sum(1 for x in dec if x["legs"] == 0)
        key = f"{vt(w, h)}|{mode}|{period}|x{mult}"
        res["blocks"][key] = {"trades": m["trades"], "net_pnl": m["net_pnl"], "ledger_sum_net_pnl": m["ledger_sum_net_pnl"]}
        if abs(m["net_pnl"] - m["ledger_sum_net_pnl"]) > 1e-6:
            raise AssertionError(f"equity ≠ ledger v bloku {key}")
        return m, cv

    s, e = span("tuning")
    for w, h in GRID:
        m, _ = run(s, e, w, h, 1, "grid_tuning")
        res["grid_tuning_x1"][vt(w, h)] = m
    best = max(GRID, key=lambda g: (res["grid_tuning_x1"][vt(*g)]["net_pnl"], -GRID.index(g)))
    res["chosen_variant"] = vt(*best)
    W, H = best
    val_curve = None
    for period in PERIODS:
        s, e = span(period)
        for mult in COST_MULTIPLIERS:
            bh = metrics(buy_hold(ctx, s, e, mult), [])
            res["buy_hold"][f"{period}/x{mult}"] = bh
            m, cv = run(s, e, W, H, mult, period)
            m["excess_vs_bh_pnl"] = m["net_pnl"] - bh["net_pnl"]
            res["strategy"][f"{period}/x{mult}"] = m
            if mult == 1:
                res["info"][f"exposure/{period}"] = exposure(ctx, cv)
                if period == "validation":
                    val_curve = cv
        if period != "tuning":
            pm, _ = run(s, e, W, H, 1, period, mode="REVERSE")
            res["info"][f"placebo_reverse/{period}/x1"] = pm
    s, e = span("validation")
    for w, h in GRID:
        if (w, h) != best and (w == W or h == H):
            m, _ = run(s, e, w, h, 2, "neighbor_validation")
            res["neighbors_validation_x2"][vt(w, h)] = m
    for y in WF_YEARS:
        ys, ye = date(y, 1, 1), date(y, 12, 31)
        m, _ = run(ys, ye, W, H, 2, f"wf_{y}")
        m["bh"] = metrics(buy_hold(ctx, ys, ye, 2), [])
        res["walk_forward_x2"][str(y)] = m
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.research.deflated_sharpe import dsr_from_returns
    res["dsr_validation_x1"] = dsr_from_returns(daily_returns(val_curve), DSR_N, DSR_VAR_ANNUAL / 365)
    res["verdict"] = verdict(res)
    return res, ledger


def verdict(res):
    g = lambda p, m: res["strategy"][f"{p}/x{m}"]
    bh = lambda p, m: res["buy_hold"][f"{p}/x{m}"]
    v1, v2, f1, f2, t1 = g("validation", 1), g("validation", 2), g("final_test", 1), g("final_test", 2), g("tuning", 1)
    a = {"A1_validation_sharpe_and_dd_beat_bh_x1": v1["sharpe"] > bh("validation", 1)["sharpe"]
         and v1["max_drawdown_pct"] < bh("validation", 1)["max_drawdown_pct"],
         "A2_validation_trades_ge_30": v1["trades"] >= 30,
         "A3_validation_x2_pf_gt_1_2_and_net_gt_0": v2["profit_factor"] > 1.2 and v2["net_pnl"] > 0,
         "A4_validation_x1_net_without_top3_gt_0": v1["net_without_top3"] > 0,
         "A5_final_x2_net_gt_0_sharpe_and_dd_beat_bh": f2["net_pnl"] > 0 and f2["sharpe"] > bh("final_test", 2)["sharpe"]
         and f2["max_drawdown_pct"] < bh("final_test", 2)["max_drawdown_pct"]}
    b = {"B1_val_x2_profit_pf": v2["net_pnl"] > 0 and v2["profit_factor"] > 1.2,
         "B2_dd_le_0_6_bh": v1["max_drawdown_pct"] <= 0.6 * bh("validation", 1)["max_drawdown_pct"]
         and f1["max_drawdown_pct"] <= 0.6 * bh("final_test", 1)["max_drawdown_pct"],
         "B3_final_x2_profit": f2["net_pnl"] > 0,
         "B4_val_wo_top3": v1["net_without_top3"] > 0,
         "B5_trades_ge_20": v1["trades"] + f1["trades"] >= 20,
         "B6_tuning_x1_profit": t1["net_pnl"] > 0}
    wf_pos = sum(1 for y in res["walk_forward_x2"].values() if y["net_pnl"] > 0)
    robust = {"dsr_ge_0_95": res["dsr_validation_x1"]["dsr"] >= 0.95,
              "neighbors_val_x2_profit": all(m["net_pnl"] > 0 for m in res["neighbors_validation_x2"].values()),
              "walk_forward_ge_3_of_4": wf_pos >= 3}
    pa, pb = all(a.values()), all(b.values())
    status = "KANDIDÁT NA FORWARD PAPER" if (pa or pb) and all(robust.values()) else "ZAMÍTNUTO"
    return {"track_a": a, "track_b": b, "passed_a": pa, "passed_b": pb, "robustness": robust,
            "walk_forward_positive_years": wf_pos, "status": status}


FIELDS = ["variant", "mode", "period", "cost_multiplier", "decision_day", "asset", "side", "beta", "weight",
          "entry_day", "exit_day", "entry_fill", "exit_fill", "qty", "notional", "funding", "costs", "gross_pnl",
          "net_pnl", "liquidated", "exit_shifted", "missing_liq_days"]


def write(outdir, res, ledger, manifest, missing):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "trades.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(ledger)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (out / "data_source.json").write_text(json.dumps(
        {"source": "https://data.binance.vision futures/um monthly 1d klines + fundingRate (public, no keys)",
         "missing_before_listing": missing, "archives": manifest}, indent=0) + "\n")
    (out / "RESULTS.md").write_text(report(res))


def _f(x, p=2):
    return "∞" if x == math.inf else f"{x:.{p}f}"


def report(res):
    v = res["verdict"]
    yn = lambda ok: "ano" if ok else "NE"
    L = ["# Betting-against-beta, 8 USDT-M perpů — výsledky (protokol `PROTOCOL.md`)", "",
         f"**Verdikt: {v['status']}** — zvolená varianta {res['chosen_variant']} (výběr na ladění ×1 podle čistého zisku).", "",
         "| kritérium | splněno |", "|---|---|"]
    L += [f"| {k} | {yn(ok)} |" for k, ok in {**v["track_a"], **v["track_b"], **v["robustness"]}.items()]
    L += ["", f"DSR validace ×1 (N = {DSR_N}, podmíněné — R10): {res['dsr_validation_x1']['dsr']:.3f}; "
          f"walk-forward kladných let: {v['walk_forward_positive_years']}/4.", "",
          "## Mřížka na ladění ×1", "", "| varianta | čistý P/L | Sharpe | DD % | nohy |", "|---|---|---|---|---|"]
    for k, g in res["grid_tuning_x1"].items():
        L.append(f"| {k} | {g['net_pnl']:.2f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    L += ["", "## Strategie vs. buy & hold rovnovážného koše 8 perpů", "",
          "| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | nohy | PF | bez top 3 | funding | náklady | likvid. | B&H výnos % | B&H Sharpe | B&H DD % |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for m in COST_MULTIPLIERS:
            g, b = res["strategy"][f"{p}/x{m}"], res["buy_hold"][f"{p}/x{m}"]
            L.append(f"| {p} | ×{m} | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | "
                     f"{g['trades']} | {_f(g['profit_factor'])} | {g['net_without_top3']:.2f} | {g['funding']:.2f} | {g['costs']:.2f} | "
                     f"{g['liquidations']} | {b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    L += ["", "## Robustnost", "", "| test | čistý P/L | výnos % | Sharpe | DD % | nohy |", "|---|---|---|---|---|---|"]
    for k, g in res["neighbors_validation_x2"].items():
        L.append(f"| soused {k}, validace ×2 | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    for y, g in res["walk_forward_x2"].items():
        L.append(f"| WF {y} ×2 (B&H {g['bh']['return_pct']:.1f} %) | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    L += ["", "## Informačně (NEJSOU kritériem)", ""]
    for k, x in res["info"].items():
        if k.startswith("exposure"):
            L.append(f"- {k}: beta ke koši {x['beta_to_basket']:.2f}, korelace ke koši {x['corr_to_basket']:.2f}, k BTC {x['corr_to_btc']:.2f}")
        else:
            L.append(f"- {k}: P/L {x['net_pnl']:.2f}, výnos {x['return_pct']:.1f} %, Sharpe {x['sharpe']:.2f}, DD {x['max_drawdown_pct']:.1f} %")
    L += ["", "Pozn.: `trades.csv` = každá noha; součet net_pnl bloku (variant, mode, period, cost_multiplier) = čistý P/L bloku.",
          "", "Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args(argv)
    market, funding, manifest, missing = load(a.cache)
    res, ledger = evaluate(market, funding)
    res["data_gaps_days"] = data_gaps(market)
    write(a.outdir, res, ledger, manifest, missing)
    s = {k: res["strategy"][k] for k in ("tuning/x1", "validation/x1", "validation/x2", "final_test/x2")}
    print("SUMMARY", json.dumps({"chosen": res["chosen_variant"], "verdict": res["verdict"],
                                 "dsr": res["dsr_validation_x1"]["dsr"], "strategy": s,
                                 "bh": {k: res["buy_hold"][k] for k in s}}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
