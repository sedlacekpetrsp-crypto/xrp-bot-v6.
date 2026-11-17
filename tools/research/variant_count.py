"""R10: rekonstrukce počtu zkoušených variant (N) a rozptylu Sharpe pokusů z gitu.

Jen čtení gitu (git show na origin/* větvích), žádná data z burzy, nic se neladí.
Použití: python tools/research/variant_count.py OUT.json
Pravidla počítání (předem dána, viz reports/variant-count-reconstruction-20261107.md):
  A) historie 110 hypotéz (reports/hypothesis-inventory-20261105.json):
     - JSON s klíčem `candidates` => N = len(candidates) + len(challenge_candidates)
     - jinak `variants` => len(variants); jinak `config` (dict) => 1
     - jinak results.json s `runs` (období × náklady jednoho pravidla) => 1 pravidlo
       (u vícero aktiv v klíčích runs navíc „na aktivum“ = horní varianta)
     - jinak NEDOLOŽENO (nezapočteno, vypsáno jménem)
     - duplicitní soubor (stejný SHA-256 obsahu) se počítá jen jednou
  B) R-série (PR #11–#32): počet hodnot sloupce `variant` v trades.csv bez placeb a benchmarků.
  C) V[SR]: rozptyl ročního Sharpe validace ×1 všech strategických variant R-série (bez per-aktivum a B&H).
"""
import csv, hashlib, io, json, re, statistics, subprocess, sys

INV = "reports/hypothesis-inventory-20261105.json"
R_TESTS = {  # větev -> adresář
    "donchian-trend-20261105": "donchian_trend", "turn-of-month-20261105": "turn_of_month",
    "rsi2-pullback-20261105": "rsi2_pullback", "sma200-overlay-20261105": "sma200_overlay",
    "vol-breakout-20261105": "vol_breakout", "ts-momentum-vote-20261105": "ts_momentum_vote",
    "ethbtc-switch-20261105": "ethbtc_switch", "rsi2-cross-asset-20261106": "rsi2_cross_asset",
    "funding-carry-20261106": "funding_carry", "ethbtc-meanrev-20261106": "ethbtc_meanrev",
    "rebalance-band-20261106": "rebalance_band", "xrpbtc-switch-20261106": "xrpbtc_switch",
    "vol-target-20261106": "vol_target", "near-high-20261106": "near_high",
    "contrarian-ladder-20261106": "contrarian_ladder", "bab-beta-20261107": "bab_beta",
}
NOT_TRIAL = re.compile(r"placebo|static|eqw|bottom|bench|buy_?hold", re.I)
ASSET = re.compile(r"[A-Z]{3,}USDT")


def show(branches, path):
    for b in branches:
        r = subprocess.run(["git", "show", f"{b.strip()}:{path}"], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
    return None


def historical():
    inv = json.load(open(INV))
    seen, rows = {}, []
    for h in inv:
        files = [f for f in dict.fromkeys(h["files_with_sha256"] + h["files"]) if f.endswith(".json")]
        best = None
        for f in files:
            s = show(h["branches"], f)
            try:
                o = json.loads(s) if s else None
            except ValueError:
                o = None
            if not isinstance(o, dict):
                continue
            dig = hashlib.sha256(s.encode()).hexdigest()
            if isinstance(o.get("candidates"), (list, dict)):
                c = (0, "candidates", len(o["candidates"]) + len(o.get("challenge_candidates") or []), 1)
            elif isinstance(o.get("variants"), (list, dict)):
                c = (1, "variants", len(o["variants"]), 1)
            elif isinstance(o.get("config"), dict):
                c = (2, "config", 1, 1)
            elif isinstance(o.get("runs"), dict):
                assets = {m for k in o["runs"] for m in ASSET.findall(k)}
                c = (3, "runs", 1, max(1, len(assets)))
            else:
                continue
            if best is None or c[0] < best[0][0] or (c[0] == best[0][0] and c[2] > best[0][2]):
                best = (c, f, dig)
        if best is None:
            rows.append({"hypothesis": h["hypothesis"], "class": h["class"], "rule": "NEDOLOŽENO", "n": 0, "n_upper": 0, "file": None, "dup_of": None})
            continue
        (rank, rule, n, n_up), f, dig = best
        dup = seen.get(dig)
        if not dup:
            seen[dig] = h["hypothesis"]
        rows.append({"hypothesis": h["hypothesis"], "class": h["class"], "rule": rule,
                     "n": 0 if dup else n, "n_upper": 0 if dup else max(n, n_up), "file": f, "dup_of": dup})
    return rows


def r_series():
    rows = []
    for b, d in R_TESTS.items():
        s = show([f"origin/research/{b}"], f"research/{d}/trades.csv")
        rd = csv.DictReader(io.StringIO(s))
        vs = sorted({r["variant"] for r in rd}) if "variant" in (rd.fieldnames or []) else []
        trials = [v for v in vs if not NOT_TRIAL.search(v)] or ["(jediná)"]
        rows.append({"test": d, "branch": b, "variants_all": vs, "trials": trials, "n": len(trials)})
    return rows


def vsr():
    vals = []
    for b, d in R_TESTS.items():
        o = json.loads(show([f"origin/research/{b}"], f"research/{d}/results.json"))

        def w(x, p):
            if isinstance(x, dict):
                for k, v in x.items():
                    q = p + "/" + k
                    if k.lower() == "sharpe" and isinstance(v, (int, float)):
                        if (re.search(r"valid", q, re.I) and re.search(r"x1", q)
                                and not re.search(r"per_symbol|per_asset|/bh/|_bh/|/BH_|EQW|static|buy_?hold|bench|placebo|tuning|final", q, re.I)):
                            vals.append({"test": d, "path": q, "sharpe": v})
                    else:
                        w(v, q)
            elif isinstance(x, list):
                for i, v in enumerate(x):
                    w(v, f"{p}[{i}]")
        w(o, "")
    a = [v["sharpe"] for v in vals]
    b = [v["sharpe"] for v in vals if v["test"] != "funding_carry"]
    return {"values": vals, "n": len(a), "var_all": statistics.variance(a), "mean_all": statistics.mean(a),
            "n_directional": len(b), "var_directional": statistics.variance(b), "mean_directional": statistics.mean(b)}


def main(out):
    h, r, v = historical(), r_series(), vsr()
    summary = {
        "hist_hypotheses": len(h),
        "hist_documented_hypotheses": sum(1 for x in h if x["rule"] != "NEDOLOŽENO"),
        "hist_by_rule": {k: sum(1 for x in h if x["rule"] == k) for k in ("candidates", "variants", "config", "runs", "NEDOLOŽENO")},
        "hist_n_lower": sum(x["n"] for x in h), "hist_n_upper": sum(x["n_upper"] for x in h),
        "hist_undocumented": [x["hypothesis"] for x in h if x["rule"] == "NEDOLOŽENO"],
        "r_tests": len(r), "r_n": sum(x["n"] for x in r),
    }
    summary["N_documented_lower"] = summary["hist_n_lower"] + summary["r_n"]
    summary["N_documented_upper"] = summary["hist_n_upper"] + summary["r_n"]
    summary["vsr"] = {k: v[k] for k in v if k != "values"}
    json.dump({"summary": summary, "historical": h, "r_series": r, "vsr_values": v["values"]}, open(out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
