"""Kolo 10, část 3: shoda měsíčních a denních archivů 5m (spot i perp) ve dnech s mezerami + kontrolní agregace z 1m.
Spouštěcí podnět: audit run 42275871499 skončil chybou „konfliktní duplicita spot BTCUSDT 1608556500000“
(2020-12-21 13:15 UTC): měsíční a denní archiv mají pro stejnou svíčku jiné hodnoty. PAPER, jen čtení, bez výkonnosti."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import investigate as I

DAYS = ["2020-02-09", "2020-02-19", "2020-03-04", "2020-04-25", "2020-06-28", "2020-11-30", "2020-12-21", "2020-12-25",
        "2021-02-11", "2021-03-06", "2021-04-20", "2021-04-25", "2021-08-13", "2021-09-29", "2023-03-24", "2022-02-26",
        "2022-04-01"]  # dny mezer z části 1 (předem dané, nevybírané podle výsledku)
M5 = I.M5


def agg_1m(rows1m):
    out = {}
    for r in rows1m:
        t = I.ms(r[0])
        b = t - t % M5
        o, h, l, c, v, tb = float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[9])
        if b not in out:
            out[b] = [t, o, h, l, c, v, tb, t]
        x = out[b]
        if t < x[0]:
            x[0], x[1] = t, o
        if t >= x[7]:
            x[7], x[4] = t, c
        x[2], x[3], x[5], x[6] = max(x[2], h), min(x[3], l), x[5] + v, x[6] + tb
    return {b: (x[1], x[2], x[3], x[4], round(x[5], 8), round(x[6], 8)) for b, x in out.items()}


def norm(r):
    return (float(r[1]), float(r[2]), float(r[3]), float(r[4]), round(float(r[5]), 8), round(float(r[9]), 8))


def main():
    outdir = Path(sys.argv[1])
    rep = {"days": DAYS, "series": {}}
    for market in ("spot", "perp"):
        for sym in ("BTCUSDT", "ETHUSDT", "XRPUSDT"):
            res = {}
            for d in DAYS:
                y, m = int(d[:4]), int(d[5:7])
                st_m, bm = I.cached("/tmp/inv3", I.kline_url(market, sym, "5m", f"{y}-{m:02d}"))
                st_d, bd = I.cached("/tmp/inv3", I.kline_url(market, sym, "5m", d, daily=True))
                st_1, b1 = I.cached("/tmp/inv3", I.kline_url(market, sym, "1m", d, daily=True))
                rec = {"monthly": st_m, "daily": st_d, "daily_1m": st_1}
                if st_m == 200 and st_d == 200:
                    lo = int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp() * 1000)
                    hi = lo + 86_400_000
                    mon = {I.ms(r[0]): norm(r) for r in I.rows(bm)[0] if lo <= I.ms(r[0]) < hi}
                    day = {I.ms(r[0]): norm(r) for r in I.rows(bd)[0]}
                    one = agg_1m(I.rows(b1)[0]) if st_1 == 200 else {}
                    common = sorted(set(mon) & set(day))
                    diff = [t for t in common if mon[t] != day[t]]
                    rec.update({"monthly_bars": len(mon), "daily_bars": len(day), "only_monthly": len(set(mon) - set(day)),
                                "only_daily": len(set(day) - set(mon)), "common": len(common), "differ": len(diff)})
                    if diff:
                        rec["differ_first"] = [{"utc": I.iso(t), "monthly": mon[t], "daily": day[t],
                                                "agg_1m": one.get(t)} for t in diff[:5]]
                        rec["differ_last"] = I.iso(diff[-1])
                        rec["monthly_matches_1m"] = sum(1 for t in diff if one.get(t) and one[t][:4] == mon[t][:4])
                        rec["daily_matches_1m"] = sum(1 for t in diff if one.get(t) and one[t][:4] == day[t][:4])
                        rec["max_close_diff_bp"] = max(abs(mon[t][3] / day[t][3] - 1) * 1e4 for t in diff)
                res[d] = rec
            rep["series"][f"{market}:{sym}"] = res
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "report3.json").write_text(json.dumps(rep, indent=1, default=str))
    print("DONE")


if __name__ == "__main__":
    main()
