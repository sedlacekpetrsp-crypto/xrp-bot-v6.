"""Nezávislý přepočet souhrnů a bran G1–G3 z CSV výstupů auditu (PROTOCOL.md). Píše audit.json."""
import csv, gzip, json, math, re, statistics, sys
from collections import defaultdict
from urllib.parse import urlsplit

sys.path.insert(0, ".")
from research.xrp_news_audit.audit import classify  # noqa: E402

FILES_PER_YEAR = 35040


def poisson_ci(k):
    # přibližný 95% interval (Wilson-Hilferty)
    lo = 0.0 if k == 0 else k * (1 - 1 / (9 * k) - 1.96 / (3 * math.sqrt(k))) ** 3
    k1 = k + 1
    hi = k1 * (1 - 1 / (9 * k1) + 1.96 / (3 * math.sqrt(k1))) ** 3
    return lo, hi


def slug_title(loc):
    seg = [s for s in urlsplit(loc).path.split("/") if s]
    return seg[-1].replace("-", " ") if seg else ""


def main(d):
    files = list(csv.DictReader(open(f"{d}/gdelt_files.csv")))
    titles = list(csv.DictReader(open(f"{d}/gdelt_xrp_titles.csv")))
    # Z1 přepočet z titulků (ne z počtů v gdelt_files.csv)
    per_file = defaultdict(int)
    for t in titles:
        xrp, only, score = classify(t["title"])
        if only and abs(score) >= 2:
            per_file[t["file"]] += 1
    by_year = defaultdict(lambda: dict(slots=0, ok=0, records=0, titled=0, s2=0))
    mismatch = 0
    for f in files:
        y = int(f["slot"][:4]); b = by_year[y]; b["slots"] += 1
        if f["status"] == "ok":
            b["ok"] += 1; b["records"] += int(f["records"]); b["titled"] += int(f["titled"])
            b["s2"] += per_file.get(f["file"], 0)
            mismatch += int(per_file.get(f["file"], 0) != int(f["xrp_only_s2"] or 0))
    z1 = {}
    for y, b in sorted(by_year.items()):
        days_frac = 10 / 12 if y == 2026 else 1.0
        scale = FILES_PER_YEAR * days_frac / max(b["ok"], 1)
        lo, hi = poisson_ci(b["s2"])
        z1[y] = dict(b, missing_share=round(1 - b["ok"] / b["slots"], 3),
                     title_share=round(b["titled"] / max(b["records"], 1), 3),
                     est_s2=round(b["s2"] * scale), est_lo=round(lo * scale), est_hi=round(hi * scale))
    est_is = sum(z1[y]["est_s2"] for y in z1 if 2020 <= y <= 2024)
    est_oos = sum(z1[y]["est_s2"] for y in z1 if y >= 2025)
    est_is_lo = sum(z1[y]["est_lo"] for y in z1 if 2020 <= y <= 2024)
    g1_z1 = est_is >= 300 and est_oos >= 100
    g3_z1 = all(z1[y]["missing_share"] <= 0.25 for y in z1)
    domains = defaultdict(int)
    for t in titles:
        domains[t["domain"]] += 1
    # Z2
    rows = list(csv.DictReader(gzip.open(f"{d}/sitemap_xrp_urls.csv.gz", "rt")))
    z2 = {}
    for site in sorted({r["site"] for r in rows}):
        rs = [r for r in rows if r["site"] == site]
        yc, qs, s2y, prec = defaultdict(int), set(), defaultdict(int), defaultdict(int)
        for r in rs:
            y, m = int(r["year"]), int(r["month"])
            yc[y] += 1
            if y:
                qs.add((y, (m - 1) // 3 + 1))
            title = r["title"] or slug_title(r["loc"])
            _, only, score = classify(title)
            if only and abs(score) >= 2:
                s2y[y] += 1
            p = r["pub"]
            prec["pub_minute" if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", p) else
                 ("pub_date" if p else "no_pub")] += 1
        want = [(y, q) for y in range(2020, 2027) for q in range(1, 5) if (y, q) <= (2026, 3)]
        missing_q = [f"{y}Q{q}" for y, q in want if (y, q) not in qs]
        is_n = sum(v for y, v in s2y.items() if 2020 <= y <= 2024)
        oos_n = sum(v for y, v in s2y.items() if y >= 2025)
        z2[site] = dict(n_xrp=len(rs), by_year=dict(sorted(yc.items())), s2_by_year=dict(sorted(s2y.items())),
                        s2_is=is_n, s2_oos=oos_n, precision=dict(prec), missing_quarters=missing_q,
                        g1=is_n >= 300 and oos_n >= 100, g3=not missing_q)
    # Z3
    lags = [float(r["lag_min"]) for r in csv.DictReader(open(f"{d}/lag.csv"))]
    lag = dict(n=len(lags))
    if lags:
        al = sorted(abs(x) for x in lags)
        lag.update(median_abs_min=statistics.median(al), p90_abs_min=al[int(0.9 * (len(al) - 1))],
                   median_signed_min=statistics.median(lags))
    g2_z2_lag = bool(lags) and lag["median_abs_min"] <= 60 and lag["p90_abs_min"] <= 360
    for site, v in z2.items():
        v["g2"] = v["precision"].get("pub_minute", 0) >= 0.9 * max(v["n_xrp"], 1) and g2_z2_lag
        v["verdict"] = "GO" if v["g1"] and v["g2"] and v["g3"] else "NO-GO"
    g2_z1 = sum(b["titled"] for b in by_year.values()) > 0
    res = dict(
        z1=dict(by_year=z1, est_is=est_is, est_is_lo=est_is_lo, est_oos=est_oos, g1=g1_z1, g2=g2_z1, g3=g3_z1,
                verdict="GO" if g1_z1 and g2_z1 and g3_z1 else "NO-GO", recount_mismatch_files=mismatch,
                n_titles=len(titles), top_domains=sorted(domains.items(), key=lambda x: -x[1])[:15]),
        z2=z2, z3=lag)
    res["verdict"] = "GO" if res["z1"]["verdict"] == "GO" or any(v["verdict"] == "GO" for v in z2.values()) else "DATA NO-GO"
    json.dump(res, open(f"{d}/audit.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    print("VERIFY", "MATCH" if mismatch == 0 else f"MISMATCH {mismatch}")


if __name__ == "__main__":
    main(sys.argv[1])
