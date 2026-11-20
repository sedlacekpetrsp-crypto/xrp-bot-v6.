"""R10b: úplný ledger pokusů N (rozšíření R10 o PR #33–#65 a produkční/forward PAPER boty).

Pravidla jsou zmrazena v research/trial_ledger/PROTOCOL.md (commit před tímto skriptem). Jen čtení gitu + snapshot JSON.
Použití: python tools/research/trial_ledger.py OUT.json
"""
import csv, gzip, io, json, re, subprocess, sys

R10_REF = "origin/research/variant-count-20261107"
R10_JSON = "reports/variant-count-reconstruction-20261107.json"
INV = "reports/hypothesis-inventory-20261105.json"
PROD = "research/trial_ledger/prod_trade_tables_20261117.json"
NOT_TRIAL = re.compile(r"placebo|static|eqw|bottom|bench|buy_?hold", re.I)
R10_RTEST_DIRS = {"donchian_trend", "turn_of_month", "rsi2_pullback", "sma200_overlay", "vol_breakout",
                  "ts_momentum_vote", "ethbtc_switch", "rsi2_cross_asset", "funding_carry", "ethbtc_meanrev",
                  "rebalance_band", "xrpbtc_switch", "vol_target", "near_high", "contrarian_ladder", "bab_beta"}
EXCLUDE_B = re.compile(r"^(forward(/|$)|combined_selection_replay)")
# C: předregistrované mřížky bez vypočteného výnosu (registr, automation/STRATEGY_REGISTRY.md)
C_ITEMS = [  # (id, PR, n, do_lo, zdroj)
    ("R8 FUNDING_DISPERSION", 29, 4, False, "registr ř. 'N +4 (průběžně 155)'"),
    ("R9 SPOT_LED", 30, 4, False, "registr ř. 'N +4 (průběžně 159)'"),
    ("A5 SPOT_LISTING_DRIFT", 43, 4, False, "registr: K∈{1,3}×T∈{10,30}, DATA NO-GO, výnos nepočítán"),
    ("K7 FOMC", 48, 4, False, "registr: 4 okna (návrh), dodatek 1 = 1 primární endpoint; výnos nepočítán"),
    ("K9 fáze A", 63, 1, True, "PROTOCOL K9 opr. 1 bod 1: fáze A +1"),
    ("K9 fáze B", 65, 2, True, "PROTOCOL K9 opr. 1 bod 1: 2 varianty H"),
]
D_MAPPED = {"tv_consensus_trades": "research/tv", "bestof_trades": "research/best",
            "candle_v8_trades": "research/candle", "candle_v8_fixed_trades": "research/candle"}
D_NOT_TRADES = {"fly_trade_exclusions"}


def git(*a):
    r = subprocess.run(["git", *a], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def r10_covered_dirs():
    inv = json.load(open(INV))
    dirs = set(R10_RTEST_DIRS)
    for h in inv:
        for f in h["files_with_sha256"] + h["files"]:
            m = re.match(r"research/([^/]+)/", f)
            if m:
                dirs.add(m.group(1))
    return dirs


def count_trades(raw, gz):
    txt = (gzip.decompress(raw) if gz else raw).decode("utf-8", "replace")
    rd = csv.DictReader(io.StringIO(txt))
    if "variant" not in (rd.fieldnames or []):
        return 1, ["(jediná)"]
    trials = sorted({r["variant"] for r in rd if not NOT_TRIAL.search(r["variant"] or "")})
    return max(1, len(trials)), trials


def count_results(raw):
    try:
        o = json.loads(raw)
    except ValueError:
        return 1, "nečitelné"
    if isinstance(o, dict):
        if isinstance(o.get("candidates"), (list, dict)):
            return len(o["candidates"]) + len(o.get("challenge_candidates") or []), "candidates"
        if isinstance(o.get("variants"), (list, dict)):
            return len(o["variants"]), "variants"
    return 1, "1 pravidlo"


def part_b(covered):
    branches = [b.strip() for b in git("branch", "-r").decode().splitlines() if "->" not in b]
    found = {}
    for b in branches:
        ls = git("ls-tree", "-r", "--name-only", b)
        for path in (ls or b"").decode().splitlines():
            m = re.match(r"research/(.+)/(trades\.csv(?:\.gz)?|results\.json)$", path)
            if not m:
                continue
            d, fn = m.group(1), m.group(2)
            top = d.split("/")[0]
            if top in covered or EXCLUDE_B.match(d):
                continue
            raw = git("show", f"{b}:{path}")
            if raw is None:
                continue
            if fn.startswith("trades"):
                n, how = count_trades(raw, fn.endswith(".gz"))
                rule = "trades.variant"
            else:
                n, how = count_results(raw)
                rule = "results.json"
            cur = found.get(top)
            # trades.csv má přednost před results.json; jinak max n
            better = cur is None or (rule == "trades.variant" and cur["rule"] != "trades.variant") or \
                (rule == cur["rule"] and n > cur["n"])
            if better:
                found[top] = {"dir": top, "branch": b, "file": path, "rule": rule, "n": n, "detail": how}
    # Dodatek 1 (po 1. výpočtu, jen zvyšuje N): artefakt trades.csv může nést jen zvolené buňky (A4 vortex_chop);
    # n = max(n, počet `cells` v results.json téhož adresáře a větve).
    for x in found.values():
        raw = git("show", f"{x['branch']}:research/{x['dir']}/results.json")
        try:
            o = json.loads(raw) if raw else None
        except ValueError:
            o = None
        if isinstance(o, dict) and isinstance(o.get("cells"), (list, dict)) and len(o["cells"]) > x["n"]:
            x["n_before_amendment1"], x["n"], x["rule"] = x["n"], len(o["cells"]), x["rule"] + "+cells(dodatek 1)"
    return sorted(found.values(), key=lambda x: x["dir"])


def part_d():
    p = json.load(open(PROD))
    lo, hi = [], []
    for t, cnt in sorted(p["tables"].items()):
        if t in D_NOT_TRADES:
            continue
        if cnt == 0:
            hi.append({"table": t, "setup": None, "trades": 0})
            continue
        if t not in D_MAPPED:
            lo.append({"table": t, "trades": cnt})
        for s, c in sorted((p["setups"].get(t) or {None: cnt}).items(), key=lambda x: str(x[0])):
            hi.append({"table": t, "setup": s, "trades": c})
    return lo, hi


def main(out):
    r10 = json.loads(git("show", f"{R10_REF}:{R10_JSON}"))
    s = r10.get("summary", {})
    a_lo, a_hi = 190, 194 + 15
    covered = r10_covered_dirs()
    b = part_b(covered)
    b_n = sum(x["n"] for x in b)
    c_lo = sum(n for _, _, n, lo, _ in C_ITEMS if lo)
    c_hi = sum(n for _, _, n, _, _ in C_ITEMS)
    d_lo, d_hi = part_d()
    n_lo = a_lo + b_n + c_lo + len(d_lo)
    n_hi = a_hi + b_n + c_hi + len(d_hi)
    res = {
        "protocol": "research/trial_ledger/PROTOCOL.md",
        "r10_summary_keys": sorted(s.keys()) if isinstance(s, dict) else None,
        "A": {"lo": a_lo, "hi": a_hi},
        "B": {"n": b_n, "items": b},
        "C": {"lo": c_lo, "hi": c_hi, "items": [dict(zip(["id", "pr", "n", "in_lo", "source"], x)) for x in C_ITEMS]},
        "D": {"lo": len(d_lo), "hi": len(d_hi), "lo_items": d_lo, "hi_items": d_hi, "mapped_to_inventory": D_MAPPED},
        "N_doc_lo": n_lo, "N_doc_hi": n_hi, "N_gate_K9": max(450, n_hi), "V_SR": 0.5,
        "n_covered_dirs_r10": len(covered),
    }
    json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: res[k] for k in ("A", "N_doc_lo", "N_doc_hi", "N_gate_K9")}, ensure_ascii=False))
    print("B:", [(x["dir"], x["n"], x["rule"]) for x in b])
    print("C:", c_lo, c_hi, "D:", len(d_lo), len(d_hi))


if __name__ == "__main__":
    main(sys.argv[1])
