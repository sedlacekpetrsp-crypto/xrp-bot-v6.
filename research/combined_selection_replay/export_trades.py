"""Per-trade ledger export for the Combined selection replay (PAPER research only).

Adds NO new rule, parameter or block: it re-runs exactly the frozen replay
(`run.BLOCKS`, `run.CONTAMINATED_ALL`, `run.FORWARD_START`, `run.COST_MULTIPLIERS`,
`run.combined_weights`, `run.scaled(Config(), m)`) on the same SHA-256-checked
Binance Vision data and writes every leg to CSV/JSON.

Consistency gate: metrics recomputed from the exported legs must equal the stored
summary `results.json` (tolerance 1e-6) — otherwise exit code 2 and nothing is
declared valid. This is an audit trail, not new evidence of profitability.

Usage (public data only, no keys, no orders):
    python -m research.combined_selection_replay.export_trades --cache /tmp/vision-1h \
        --end 2026-11-01 --results research/combined_selection_replay/results.json \
        --outdir research/combined_selection_replay/trades
"""
import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from research.combined_selection_replay import run
from research.volatility_managed_momentum_v1 import Config, backtest

FIELDS = ("cost_multiplier", "block", "role", "leg", "symbol", "entry_time_utc", "exit_time_utc",
          "entry_ts", "exit_ts", "entry", "exit", "stop", "reason", "gross_pnl", "fees",
          "net_pnl", "return_on_equity")
COMPARED = ("trades", "net_pnl", "profit_factor", "max_drawdown", "fees")


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def block_specs(end_exclusive):
    """Exactly the blocks evaluated by run.evaluate, in the same order."""
    specs = [(name, start, end, role) for name, start, end, role in run.BLOCKS]
    specs.append(("CONTAMINATED_2023_2026SEP_CONTINUOUS", *run.CONTAMINATED_ALL, "contaminated_check"))
    if run.ts(end_exclusive) > run.ts(run.FORWARD_START):
        specs.append(("FORWARD_UNUSED", run.FORWARD_START, end_exclusive, "clean_forward"))
    return specs


def ledger(market, end_exclusive):
    """Return (rows, metrics_by_cost_and_block) from the unchanged replay."""
    rows, summary = [], {}
    for mult in run.COST_MULTIPLIERS:
        cfg = run.scaled(Config(), mult)
        key = f"cost_x{mult:g}"
        summary[key] = {}
        for name, start, end, role in block_specs(end_exclusive):
            result = backtest(market, run.ts(start), run.ts(end), cfg, run.combined_weights)
            summary[key][name] = run.metrics(result)
            for n, t in enumerate(result["trades"], 1):
                rows.append({"cost_multiplier": mult, "block": name, "role": role, "leg": n,
                             "symbol": t["symbol"], "entry_time_utc": iso(t["entry_ts"]),
                             "exit_time_utc": iso(t["exit_ts"]), **{k: t[k] for k in (
                                 "entry_ts", "exit_ts", "entry", "exit", "stop", "reason",
                                 "gross_pnl", "fees", "net_pnl", "return_on_equity")}})
    return rows, summary


def compare(summary, stored, tolerance=1e-6):
    """Differences between recomputed metrics and the stored results.json summary."""
    diffs = []
    for cost, blocks in summary.items():
        for name, got in blocks.items():
            want = stored.get(cost, {}).get(name)
            if want is None:
                diffs.append((cost, name, "missing_in_stored", None, None))
                continue
            for field in COMPARED:
                a, b = want.get(field), got.get(field)
                if a is None or b is None or (isinstance(b, float) and math.isinf(b)):
                    if str(a) != str(b):
                        diffs.append((cost, name, field, a, b))
                elif abs(float(a) - float(b)) > tolerance:
                    diffs.append((cost, name, field, a, b))
    return diffs


def per_block_totals(rows):
    out = {}
    for r in rows:
        k = (f"cost_x{r['cost_multiplier']:g}", r["block"])
        out.setdefault(k, {"legs": 0, "net_pnl": 0.0})
        out[k]["legs"] += 1
        out[k]["net_pnl"] += r["net_pnl"]
    return out


def write(rows, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with (outdir / "trades.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in r.items()})
    (outdir / "trades.json").write_text(json.dumps(rows, indent=0) + "\n")
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (outdir / "trades.csv", outdir / "trades.json")}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--results", required=True, help="stored summary results.json")
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args(argv)
    reference = json.loads((run.HERE / "reference_vmm_20261022.json").read_text())
    stored = json.loads(Path(args.results).read_text())
    market, manifest = run.load_market(args.cache, args.end, reference["manifest"])
    control = run.control_check(market, reference["reference_results"])
    rows, summary = ledger(market, args.end)
    diffs = compare(summary, stored.get("results", {}))
    hashes = write(rows, args.outdir)
    stored_manifest = {m["url"]: m["sha256"] for m in stored.get("manifest", [])}
    manifest_diffs = [m["url"] for m in manifest if stored_manifest.get(m["url"]) != m["sha256"]]
    report = {"strategy": stored.get("strategy"), "end_exclusive": args.end,
              "rules_changed": False, "control_mismatches": control,
              "summary_mismatches": diffs, "manifest_mismatches_vs_results_json": manifest_diffs,
              "legs_total": len(rows), "files_sha256": hashes,
              "per_block": {f"{c}/{b}": v for (c, b), v in per_block_totals(rows).items()},
              "status": "CONSISTENT" if not (control or diffs or manifest_diffs) else "MISMATCH"}
    (Path(args.outdir) / "export_report.json").write_text(json.dumps(report, indent=1, default=str) + "\n")
    (Path(args.outdir) / "data_source.json").write_text(json.dumps(
        {"source": "https://data.binance.vision spot monthly 1h klines (public, no keys)",
         "symbols": sorted({m["url"].split("/")[-3] for m in manifest}),
         "end_exclusive": args.end, "archives": manifest}, indent=0) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "per_block"}, indent=1, default=str))
    return 0 if report["status"] == "CONSISTENT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
