"""Přehodnocení hotových backtestů stopou B (rámec v2, automation/RESEARCH_FRAMEWORK.md bod 1).

Jen čte results.json (žádný nový backtest). Výsledky jsou post-hoc ⇒ případné „prošlo“ smí jít
nanejvýš do forward PAPER. Výhradně PAPER.

Použití: python tools/research/track_b_rescore.py <název>=<cesta/results.json> ... [--json out.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DD_RATIO = 0.6
PF_MIN = 1.2
MIN_TRADES = 20


def _blocks(results: dict) -> tuple[dict, dict]:
    """Vrátí (strategie, buy&hold) slovníky 'období/xN' -> metriky."""
    bh = results["buy_hold"]
    # páry/koše: primární měřítko protokolu je B&H koš 50/50 bez rebalance
    bh = {k: (v["basket_50_50"] if "basket_50_50" in v else v) for k, v in bh.items()}
    if "strategy" in results:
        return results["strategy"], bh
    # mřížka (Donchian): vybraná varianta z ladění
    chosen = results.get("verdict", {}).get("chosen") or results["tuning_selection"]["chosen"]
    prefix = f"{chosen}/"
    strat = {k[len(prefix):]: v for k, v in results["grid"].items() if k.startswith(prefix)}
    return strat, bh


def score(results: dict) -> dict:
    s, bh = _blocks(results)
    v1, v2 = s["validation/x1"], s["validation/x2"]
    f2 = s["final_test/x2"]
    t1 = s["tuning/x1"]
    dd_lim_val = DD_RATIO * bh["validation/x1"]["max_drawdown_pct"]
    dd_lim_fin = DD_RATIO * bh["final_test/x1"]["max_drawdown_pct"]
    checks = {
        "B1_val_x2_net_gt0_pf_gt_1_2": v2["net_pnl"] > 0 and v2["profit_factor"] > PF_MIN,
        "B2_dd_le_0_6_bh_val_and_final": (
            v1["max_drawdown_pct"] <= dd_lim_val and s["final_test/x1"]["max_drawdown_pct"] <= dd_lim_fin
        ),
        "B3_final_x2_net_gt0": f2["net_pnl"] > 0,
        "B4_val_x1_without_top3_gt0": v1["net_without_top3"] > 0,
        "B5_trades_val_plus_final_ge_20": v1["trades"] + s["final_test/x1"]["trades"] >= MIN_TRADES,
        "B6_tuning_x1_net_gt0": t1["net_pnl"] > 0,
    }
    failed = [k.split("_")[0] for k, ok in checks.items() if not ok]
    return {
        "checks": checks,
        "failed": failed,
        "passed": not failed,
        "metrics": {
            "tuning_x1_net": t1["net_pnl"],
            "val_x1_ret_pct": v1["return_pct"],
            "val_x1_dd_pct": v1["max_drawdown_pct"],
            "val_bh_dd_pct": bh["validation/x1"]["max_drawdown_pct"],
            "val_x2_net": v2["net_pnl"],
            "val_x2_pf": v2["profit_factor"],
            "val_x1_wo_top3": v1["net_without_top3"],
            "final_x1_dd_pct": s["final_test/x1"]["max_drawdown_pct"],
            "final_bh_dd_pct": bh["final_test/x1"]["max_drawdown_pct"],
            "final_x2_ret_pct": f2["return_pct"],
            "final_bh_x2_ret_pct": bh["final_test/x2"]["return_pct"],
            "trades_val_final": v1["trades"] + s["final_test/x1"]["trades"],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+", help="název=cesta/results.json")
    ap.add_argument("--json")
    a = ap.parse_args()
    out = {}
    for item in a.items:
        name, path = item.split("=", 1)
        out[name] = score(json.loads(Path(path).read_text()))
        r = out[name]
        print(f"{name:18s} {'PROŠLO (post-hoc)' if r['passed'] else 'neprošlo: ' + ','.join(r['failed'])}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
