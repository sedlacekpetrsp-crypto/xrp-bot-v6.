"""Build a read-only inventory of research hypotheses across all remote branches.

Reads with `git show` only. Groups files by research directory / protocol stem,
extracts the decision line, dates, ledger / manifest / hash evidence, and the
first branch + commit that contains each file. Output: JSON + Markdown.
"""
import collections, json, re, subprocess, sys

REPO = sys.argv[1]; OUT = sys.argv[2]

def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout

branches = [b.strip() for b in git("branch", "-r").splitlines() if "HEAD" not in b]
files = collections.defaultdict(dict)          # path -> {branch: blob}
for b in branches:
    for line in git("ls-tree", "-r", b).splitlines():
        meta, path = line.split("\t", 1)
        blob = meta.split()[2]
        files[path][b] = blob

def key_of(path):
    p = path.split("/")
    if p[0] == "elite":
        m = re.search(r"V(\d+)", path.upper().replace("V8_V11","V8"))
        if not m:
            return None
        v = int(m.group(1))
        return f"elite/V{v}"
    if p[0] != "research" or len(p) < 2:
        return None
    name = p[1]
    name = re.sub(r"\.(md|json|py|gz)$", "", name)
    name = re.sub(r"^(run_|audit_|test_|download_)", "", name)
    name = re.sub(r"(_\d{8})$", "", name)
    name = re.sub(r"_(protocol|results|decision|validation|source|source_check|source_feasibility|source_audit|ingestion_amendment|methodology_amendment|dedup_amendment|boundary_amendment|percentile_note|amendment|history|v\d+)$", "", name)
    name = re.sub(r"_(protocol|validation|source|v\d+)$", "", name)
    return "research/" + name

def is_decision_file(path):
    return bool(re.search(r"(validation_\d{8}/README\.md|/README\.md$|REPORT|_decision|decision_|results.*\.json$|RESULTS|summary\.json$|research_decision)", path)) and "PROTOCOL" not in path and "_protocol" not in path

DECISION = re.compile(r"(Decision:[^\n]{0,160}|Rozhodnutí:[^\n]{0,160}|Final decision[^\n]{0,160}|NEPRO[ŠS]EL|NEPROŠLA|NEPROŠLY|TEST NEDOKONČEN|REJECT\w*|zamítnut\w*|passes_historical_gate\"?\s*:\s*(true|false)|status\"?\s*:\s*\"(EVALUATED|ABORTED\w*)\")", re.I)

groups = collections.defaultdict(list)
for path, per in files.items():
    k = key_of(path)
    if k and re.search(r"\.(md|json|gz|py)$", path):
        groups[k].append(path)

rows = []
for k, paths in sorted(groups.items()):
    if not any(re.search(r"(protocol|PROTOCOL|README|REPORT|results|decision|summary|RESULTS)", p) for p in paths):
        continue
    bset = sorted({b for p in paths for b in files[p]})
    first_branch = None; first_date = None; first_commit = None
    for p in paths:
        c = git("log", "--all", "--diff-filter=A", "--format=%h %cs", "--reverse", "--", p).split()
        if c and (first_date is None or c[1] < first_date):
            first_commit, first_date = c[0], c[1]
    if first_commit:
        containing = [b.strip().replace("remotes/","") for b in git("branch", "-r", "--contains", first_commit).splitlines() if "HEAD" not in b]
        first_branch = ", ".join(sorted(containing)[:3]) + (f" (+{len(containing)-3})" if len(containing) > 3 else "")
    decision = None
    for p in sorted(paths, key=lambda x: (not re.search("README|REPORT|decision|RESULTS", x), x)):
        if p.endswith(".gz") or not is_decision_file(p):
            continue
        b = next(iter(files[p]))
        txt = git("show", f"{b}:{p}")[:200000]
        m = DECISION.search(txt)
        if m:
            decision = re.sub(r"\s+", " ", m.group(0))[:160]; break
    ledger = [p for p in paths if re.search(r"(trades\.json(\.gz)?|evidence\.tar\.gz|trade_log|ledger)", p)]
    manifest = []
    for p in paths:
        if p.endswith(".json"):
            b = next(iter(files[p]))
            txt = git("show", f"{b}:{p}")
            if '"sha256"' in txt or "SHA256" in txt or "sha256" in txt:
                manifest.append(p)
    rows.append(dict(hypothesis=k, first_seen=first_date, first_commit=first_commit,
                     first_branch=first_branch, branches=bset, decision=decision,
                     ledger_files=ledger, files_with_sha256=manifest, files=sorted(paths)))

json.dump(rows, open(OUT + ".json", "w"), indent=1, ensure_ascii=False)

def cls(d):
    if not d: return "NEZNÁMÉ / NEDOKONČENO"
    u = d.upper()
    if "NEDOKON" in u: return "NEDOKONČENO"
    if "NEPRO" in u or "REJECT" in u or "ZAMÍT" in u or "FALSE" in u or "NO CANDIDATE" in u or "ŽÁDNÁ" in u or "ŽÁDNÝ" in u or "NOT ELIGIBLE" in u or "NO TESTED" in u or "NO PRODUCTION" in u: return "NEPROŠEL"
    if "ABORT" in u: return "PŘERUŠENO"
    if "EVALUATED" in u: return "VYHODNOCENO"
    return "VIZ ROZHODNUTÍ"

with open(OUT + ".md", "w") as f:
    f.write("| # | Hypotéza / adresář | Poprvé | Commit | Větev (první) | Rozhodnutí (výňatek) | Třída | Ledger | SHA-256 |\n")
    f.write("|---:|---|---|---|---|---|---|---|---|\n")
    for i, r in enumerate(rows, 1):
        f.write(f"| {i} | `{r['hypothesis']}` | {r['first_seen'] or '—'} | `{r['first_commit'] or '—'}` | "
                f"`{(r['first_branch'] or '').replace('origin/','')}` | {(r['decision'] or '—').replace('|','/')} | "
                f"{cls(r['decision'])} | {'ano' if r['ledger_files'] else '**chybí**'} | "
                f"{'ano' if r['files_with_sha256'] else '**chybí**'} |\n")
print(len(rows), "hypotheses;", collections.Counter(cls(r["decision"]) for r in rows))
