"""Kolo 10, část 4: lze 2026-10-28 (chybí klines/aggTrades/1m/mark ve všech datových sadách) rekonstruovat
z oficiálních surových obchodů (`trades`, k dispozici)? Metoda se nejdřív ověří na sousedních dnech 2026-10-27 a 10-29:
agregace trades → 1h a 5m klines musí PŘESNĚ souhlasit s oficiálními klines. PAPER, jen čtení, bez výkonnosti."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import investigate as I

ASSETS = ("BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT")


def agg(trows, step):
    out = {}
    for r in trows:  # id, price, qty, quote_qty, time, is_buyer_maker
        t, p, q = I.ms(r[4]), r[1], float(r[2])
        b = t - t % step
        x = out.get(b)
        if x is None:
            out[b] = [t, p, p, p, t, p, q, 0.0 if r[5].strip().lower() == "true" else q]
            continue
        if t < x[0]:
            x[0], x[1] = t, p
        if t >= x[4]:
            x[4], x[5] = t, p
        if float(p) > float(x[2]):
            x[2] = p
        if float(p) < float(x[3]):
            x[3] = p
        x[6] += q
        x[7] += 0.0 if r[5].strip().lower() == "true" else q
    return {b: (float(x[1]), float(x[2]), float(x[3]), float(x[5]), round(x[6], 6), round(x[7], 6)) for b, x in out.items()}


def official(rows):
    return {I.ms(r[0]): (float(r[1]), float(r[2]), float(r[3]), float(r[4]), round(float(r[5]), 6), round(float(r[9]), 6))
            for r in rows}


def main():
    outdir = Path(sys.argv[1])
    rep = {}
    for sym in ASSETS:
        res = {}
        for d in ("2026-10-27", "2026-10-29", "2026-10-28"):
            st, bt = I.get(f"{I.V}/data/futures/um/daily/trades/{sym}/{sym}-trades-{d}.zip", timeout=600)
            rec = {"trades": st}
            if st != 200:
                res[d] = rec
                continue
            tr = I.rows(bt)[0]
            rec["trade_rows"] = len(tr)
            for iv, step in (("1h", I.H), ("5m", I.M5)):
                mine = agg(tr, step)
                st_k, bk = I.get(I.kline_url("perp", sym, iv, d, daily=True), timeout=120)
                r2 = {"official": st_k, "rebuilt_bars": len(mine)}
                if st_k == 200:
                    off = official(I.rows(bk)[0])
                    common = set(off) & set(mine)
                    price_eq = sum(1 for t in common if off[t][:4] == mine[t][:4])
                    vol_eq = sum(1 for t in common if abs(off[t][4] - mine[t][4]) <= 1e-6 * max(1, off[t][4]))
                    r2.update({"official_bars": len(off), "common": len(common), "ohlc_equal": price_eq, "volume_equal": vol_eq})
                    bad = [t for t in sorted(common) if off[t][:4] != mine[t][:4]][:3]
                    r2["ohlc_mismatch_examples"] = [{"utc": I.iso(t), "official": off[t], "rebuilt": mine[t]} for t in bad]
                rec[iv] = r2
            res[d] = rec
        rep[sym] = res
        (Path(outdir)).mkdir(parents=True, exist_ok=True)
        (Path(outdir) / "report4.json").write_text(json.dumps(rep, indent=1, default=str))
    print("DONE")


if __name__ == "__main__":
    main()
