"""Kolo 10, část 2 (oprava a rozšíření části 1; PAPER, jen čtení veřejných dat, bez výkonnosti).
A. Point-in-time univerzum USDT-M perpů (oprava: v části 1 regex bral jen poslední měsíc).
B. 2026-10-28: které datové sady Binance Vision pro tento den existují (klines/aggTrades/markPrice/funding).
C. Exekuce spot-led: XRPUSDT, předem určené dny = 15. každého měsíce 2023-01…2024-12; přesná podmínka signálu
   i širší podmínka |spot 5m| ≥ 0,2 % (kvůli velikosti vzorku), adverse selection z aggTrades, spread z bookTicker.
"""
import bisect, json, re, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import investigate as I

M5 = I.M5


def universe():
    pre = "data/futures/um/monthly/fundingRate/"
    syms, st = I.bucket_symbols(pre)
    out = {}
    for s in syms:
        if not s.endswith("USDT"):
            continue
        mm = sorted({m for k in I.bucket_files(pre + s + "/") for m in re.findall(r"-(\d{4}-\d{2})\.zip$", k)})
        if mm:
            out[s] = {"first": mm[0], "last": mm[-1], "months": len(mm)}
    return {"status": st, "symbols": out}


def day_20261028():
    d, res = "2026-10-28", {}
    for sym in ("BTCUSDT", "XRPUSDT"):
        for name, url in (
                ("klines_1m", f"{I.V}/data/futures/um/daily/klines/{sym}/1m/{sym}-1m-{d}.zip"),
                ("aggTrades", f"{I.V}/data/futures/um/daily/aggTrades/{sym}/{sym}-aggTrades-{d}.zip"),
                ("trades", f"{I.V}/data/futures/um/daily/trades/{sym}/{sym}-trades-{d}.zip"),
                ("markPrice_1h", f"{I.V}/data/futures/um/daily/markPriceKlines/{sym}/1h/{sym}-1h-{d}.zip"),
                ("indexPrice_1h", f"{I.V}/data/futures/um/daily/indexPriceKlines/{sym}/1h/{sym}-1h-{d}.zip"),
                ("klines_1h_27", f"{I.V}/data/futures/um/daily/klines/{sym}/1h/{sym}-1h-2026-10-27.zip"),
                ("klines_1h_29", f"{I.V}/data/futures/um/daily/klines/{sym}/1h/{sym}-1h-2026-10-29.zip"),
                ("spot_5m", f"{I.V}/data/spot/daily/klines/{sym}/5m/{sym}-5m-{d}.zip")):
            st, b = I.get(url, timeout=120)
            rec = {"status": st}
            if st == 200:
                rec["rows"] = len(I.rows(b)[0])
            res[f"{sym}:{name}"] = rec
    st, b = I.get(f"{I.V}/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2026-10.zip")
    if st == 200:
        ev = [I.iso(I.ms(r[0])) for r in I.rows(b)[0] if I.iso(I.ms(r[0])).startswith(d)]
        res["BTCUSDT:funding_events_on_day"] = ev
    return res


def execution(cache):
    days = [date(y, m, 15).isoformat() for y in (2023, 2024) for m in range(1, 13)]
    out = {"days": {}, "events_exact": [], "events_broad": []}
    spreads = []
    for d in days:
        st_s, bs = I.cached(cache, I.kline_url("spot", "XRPUSDT", "5m", d, daily=True))
        st_p, bp = I.cached(cache, I.kline_url("perp", "XRPUSDT", "5m", d, daily=True))
        st_a, ba = I.get(f"{I.V}/data/futures/um/daily/aggTrades/XRPUSDT/XRPUSDT-aggTrades-{d}.zip", timeout=300)
        st_b, bb = I.get(f"{I.V}/data/futures/um/daily/bookTicker/XRPUSDT/XRPUSDT-bookTicker-{d}.zip", timeout=300)
        out["days"][d] = {"spot": st_s, "perp": st_p, "aggTrades": st_a, "bookTicker": st_b}
        if not (st_s == st_p == st_a == 200):
            continue
        spot = {I.ms(r[0]): (float(r[4]), float(r[5]), float(r[9])) for r in I.rows(bs)[0]}
        perp = {I.ms(r[0]): (float(r[1]), float(r[4])) for r in I.rows(bp)[0]}
        tr = sorted((I.ms(r[5]), float(r[1]), float(r[2])) for r in I.rows(ba)[0])
        tt = [x[0] for x in tr]
        book = None
        if st_b == 200:
            bk = sorted((I.ms(r[5]), float(r[1]), float(r[3])) for r in I.rows(bb)[0])
            book = ([x[0] for x in bk], bk)
        n_bars = 0
        for T in sorted(spot):
            sp, pp, p = spot.get(T - M5), perp.get(T - M5), perp.get(T)
            if not (sp and pp and p) or spot[T][1] <= 0 or (T + M5) not in perp:
                continue
            n_bars += 1
            rs, rp, share = spot[T][0] / sp[0] - 1, p[1] / pp[1] - 1, spot[T][2] / spot[T][1]
            exact = 1 if (share > 0.65 and rs > 0.002 and rp < 0.001) else -1 if (share < 0.35 and rs < -0.002 and rp > -0.001) else 0
            broad = 1 if rs >= 0.002 else -1 if rs <= -0.002 else 0
            if not broad:
                continue
            t0, op = T + M5, perp[T + M5][0]
            i = bisect.bisect_left(tt, t0)
            rec = {"day": d, "signal_utc": I.iso(T), "side": broad, "exact": exact, "rp_bp": rp * 1e4,
                   "first_trade_delay_ms": (tt[i] - t0) if i < len(tt) else None,
                   "first_trade_vs_open_bp": (broad * (tr[i][1] / op - 1) * 1e4) if i < len(tr) else None}
            for w in (1_000, 5_000, 30_000, 60_000, 300_000):
                j = bisect.bisect_left(tt, t0 + w)
                q = sum(x[2] for x in tr[i:j])
                if q > 0:
                    rec[f"adverse_bp_{w // 1000}s"] = broad * (sum(x[1] * x[2] for x in tr[i:j]) / q / op - 1) * 1e4
            if book:
                k = bisect.bisect_left(book[0], t0)
                if k < len(book[1]):
                    _, bid, ask = book[1][k]
                    mid = (bid + ask) / 2
                    rec["half_spread_bp"] = (ask - bid) / 2 / mid * 1e4
                    rec["cross_cost_vs_open_bp"] = broad * (((ask if broad == 1 else bid) / op) - 1) * 1e4
            (out["events_exact"] if exact else out["events_broad"]).append(rec)
        out["days"][d]["bars"] = n_bars
        if book:
            for k in range(0, len(book[1]), max(1, len(book[1]) // 500)):
                _, bid, ask = book[1][k]
                if bid > 0 and ask > bid:
                    spreads.append((ask - bid) / 2 / ((ask + bid) / 2) * 1e4)
    def summ(ev):
        res = {"n": len(ev)}
        for key in ("first_trade_vs_open_bp", "adverse_bp_1s", "adverse_bp_5s", "adverse_bp_30s", "adverse_bp_60s",
                    "adverse_bp_300s", "half_spread_bp", "cross_cost_vs_open_bp", "first_trade_delay_ms"):
            v = sorted(e[key] for e in ev if e.get(key) is not None)
            if v:
                res[key] = {"n": len(v), "mean": sum(v) / len(v), "median": v[len(v) // 2], "p90": v[int(0.9 * (len(v) - 1))]}
        return res
    out["summary_exact"] = summ(out["events_exact"])
    out["summary_broad"] = summ(out["events_broad"])
    sp = sorted(spreads)
    out["unconditional_half_spread_bp"] = {"n": len(sp), "median": sp[len(sp) // 2], "p90": sp[int(0.9 * (len(sp) - 1))]} if sp else None
    return out


def main():
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    rep = {}
    for name, fn in (("day_20261028", day_20261028), ("universe", universe), ("execution", lambda: execution("/tmp/inv2"))):
        try:
            rep[name] = fn()
        except Exception as e:
            rep[name] = {"error": f"{type(e).__name__}: {e}"}
        (outdir / "report2.json").write_text(json.dumps(rep, indent=1, default=str))
    print("DONE")


if __name__ == "__main__":
    main()
