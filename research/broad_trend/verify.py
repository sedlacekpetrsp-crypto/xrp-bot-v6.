"""Nezávislý přepočet souhrnů A2 z trades.csv.gz (jen csv + json, bez kódu run.py)."""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

d = Path(sys.argv[1] if len(sys.argv) > 1 else "research/broad_trend")
res = json.loads((d / "results.json").read_text())
agg = defaultdict(list)
with gzip.open(d / "trades.csv.gz", "rt", newline="") as f:
    for r in csv.DictReader(f):
        agg[(r["variant"], r["block"], r["mult"], r["book"])].append(float(r["net_pnl"]))
bad, n = [], 0
for (v, b, m, k), pnl in agg.items():
    s = res["variants"][v][f"{b}_x{m}"][k]
    pos, neg = sum(x for x in pnl if x > 0), -sum(x for x in pnl if x < 0)
    pf = round(pos / neg, 4) if neg > 0 else None
    n += 1
    # součet epizod musí sedět s P/L z equity křivky (tolerance zaokrouhlení CSV)
    if (len(pnl) != s["trades"] or abs(sum(pnl) - s["net_pnl"]) > 0.05
            or (pf is not None and s["pf"] is not None and abs(pf - s["pf"]) > 1e-3)):
        bad.append((v, b, m, k, len(pnl), round(sum(pnl), 4), s["trades"], s["net_pnl"]))
print(f"A2_VERIFY groups={n} mismatches={len(bad)} {bad[:5]}")
sys.exit(1 if bad or n == 0 else 0)
