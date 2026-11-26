"""Souhrn PAPER výsledků:  python -m polymarket_paper.report [data_dir]"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def read(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarize(data_dir: Path) -> dict:
    snaps = read(data_dir / "snapshots.jsonl")
    sett = [s for s in read(data_dir / "settlements.jsonl") if s.get("status") == "resolved"]
    out = {"snapshots": len(snaps)}
    if snaps:
        sums = sorted(s["sum"] for s in snaps)
        out["pair_ask_sum"] = {
            "min": sums[0], "median": sums[len(sums) // 2],
            "share_below_1.00": round(sum(x < 1.0 for x in sums) / len(sums), 4),
            "share_below_0.98": round(sum(x < 0.98 for x in sums) / len(sums), 4),
        }
    by = defaultdict(lambda: {"markets": 0, "pnl": 0.0, "cost": 0.0, "wins": 0,
                              "unmatched_markets": 0, "worst": 0.0})
    for s in sett:
        b = by[s["strategy"]]
        b["markets"] += 1
        b["pnl"] += s["pnl"]
        b["cost"] += s["cost"]
        b["wins"] += s["pnl"] > 0
        b["unmatched_markets"] += s["shares_up"] != s["shares_dn"]
        b["worst"] = min(b["worst"], s["pnl"])
    for name, b in by.items():
        b["pnl"] = round(b["pnl"], 2)
        b["roi_on_cost"] = round(b["pnl"] / b["cost"], 4) if b["cost"] else 0.0
        b["worst"] = round(b["worst"], 2)
        out[name] = b
    return out


if __name__ == "__main__":
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "data/polymarket_paper")
    print(json.dumps(summarize(d), indent=2, ensure_ascii=False))
