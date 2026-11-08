"""Nezávislý přepočet souhrnů zvolených buněk z trades.csv.gz (porovnání s results.json)."""
import csv
import gzip
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
res = json.loads((d / "results.json").read_text())
agg = {}
with gzip.open(d / "trades.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        k = (r["tf"], r["period"])
        a = agg.setdefault(k, {"n": 0, "w": 0, "f1": 0.0, "cell": r["cell"]})
        a["n"] += 1
        a["w"] += int(r["win"])
        if r["perp_ret"]:
            a["f1"] += 10_000.0 * (float(r["perp_ret"]) - 0.00115)
bad = 0
for (tf, p), a in sorted(agg.items()):
    s = res["cells"][a["cell"]][p]
    ok = s["signals"] == a["n"] and s["wins"] == a["w"] and abs(s["trackF"]["x1"]["net"] - a["f1"]) < 1e-3
    bad += not ok
    print("VERIFY", tf, p, a["n"], a["w"], round(a["f1"], 2), "OK" if ok else "MISMATCH")
print("VERIFY_MISMATCHES", bad)
sys.exit(1 if bad else 0)
