"""Nezávislý přepočet brány A3 krok 0 z coverage_assets.csv a coverage_quarters.csv (bez importu audit.py)."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

d = Path(sys.argv[1])
A = [r for r in csv.DictReader(open(d / "coverage_assets.csv")) if int(r["live_days"] or 0) > 0]
Q = list(csv.DictReader(open(d / "coverage_quarters.csv")))
qcov = defaultdict(list)
for r in Q:
    qcov[r["symbol"]].append(r)
passing = []
for a in A:
    cov = int(a["valid"]) / int(a["expected"])
    ev = [int(r["valid"]) / int(r["expected"]) for r in qcov[a["symbol"]] if int(r["live_days"]) >= 30]
    if cov >= 0.95 and all(c >= 0.90 for c in ev):
        passing.append(a)
per_q = defaultdict(int)
qs = {r["quarter"] for r in Q if "2022Q1" <= r["quarter"] <= "2026Q3"}
for r in Q:
    if int(r["live_days"]) >= 30 and int(r["valid"]) / int(r["expected"]) >= 0.90:
        per_q[r["quarter"]] += 1
sa = 100 * sum(a["delisted"] == "True" for a in A) / len(A)
sp = 100 * sum(a["delisted"] == "True" for a in passing) / len(passing) if passing else 0.0
g = {"assets_passing": len(passing), "G1": len(passing) >= 15, "G2": bool(qs) and all(per_q[q] >= 15 for q in qs),
     "G3": abs(sp - sa) <= 15.0, "min_quarter": min(qs, key=lambda q: per_q[q]) if qs else None}
g["verdict"] = "GO" if g["G1"] and g["G2"] and g["G3"] else "NO-GO"
orig = json.loads((d / "audit.json").read_text())["gate"]
same = (orig["assets_passing"] == g["assets_passing"] and orig["G1_min_assets"] == g["G1"]
        and orig["G2_every_quarter"] == g["G2"] and orig["G3_selection_bias"] == g["G3"])
print("VERIFY", json.dumps(g), "MATCH" if same else "MISMATCH")
sys.exit(0 if same else 1)
