"""A6 krok 0: datový audit zdrojů titulků o XRP (PROTOCOL.md). Žádné ceny, žádné výnosy."""
import argparse, csv, gzip, io, json, math, re, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
import urllib.request
import xml.etree.ElementTree as ET

UA = "xrp-bot-research-audit/1.0 (public data, low rate)"
XRP_RE = re.compile(r"\b(XRP|Ripple|XRPL)\b", re.I)          # = news_signal.ASSETS["XRP"]
OTHER_RE = [re.compile(p, re.I) for p in (r"\b(BTC|Bitcoin)\b", r"\b(ETH|Ethereum|Ether)\b", r"\b(SOL|Solana)\b")]
POSITIVE = {
    "etf approved": 5, "approves xrp": 5, "approval": 2, "approved": 3,
    "sec drops": 5, "sec dismisses": 5, "appeal dismissed": 5,
    "lawsuit dismissed": 5, "legal victory": 4, "wins lawsuit": 4,
    "license granted": 4, "wins license": 4, "regulatory approval": 4,
    "partnership": 2, "partners with": 2, "adoption": 2, "adopts xrp": 3,
    "integrates xrp": 3, "launches xrp": 2, "xrp launch": 2,
    "institutional": 1, "expands": 1, "record inflows": 4, "inflows": 2,
    "listing": 2, "lists xrp": 3,
}
NEGATIVE = {
    "etf rejected": -5, "rejects xrp": -5, "rejection": -3,
    "sec sues": -5, "lawsuit": -2, "investigation": -3, "probe": -2,
    "charged": -4, "charges": -4, "ban": -4, "bans": -4,
    "delist": -4, "delisting": -4, "hack": -5, "hacked": -5,
    "exploit": -5, "outage": -3, "breach": -4, "fraud": -4,
    "scam": -4, "liquidation": -2, "selloff": -3,
}


def headline_score(title):
    """Kopie news_signal._headline_score (v8-fly-layer-test), beze změny logiky."""
    title = re.sub(r"\s+", " ", title.lower()).strip()
    if re.search(r"\b(could|might|may|rumou?r|predict\w*|forecast\w*|if|not|denies|denied)\b|\?", title):
        return 0
    matches = []
    for phrase, value in sorted({**POSITIVE, **NEGATIVE}.items(), key=lambda p: -len(p[0])):
        for m in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", title):
            if not any(m.start() < b and m.end() > a for a, b, _ in matches):
                matches.append((m.start(), m.end(), value))
    return max(-6, min(6, sum(v for _, _, v in matches)))


def classify(title):
    xrp = bool(XRP_RE.search(title or ""))
    only = xrp and not any(r.search(title) for r in OTHER_RE)
    return xrp, only, (headline_score(title) if only else 0)


def get(url, timeout=60, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 403, 410):
                return e.code, b""
            last = e
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(2 * (i + 1))
    return -1, repr(last).encode()


# ---------------- Z1 GDELT ----------------
def sample_slots(start=(2020, 1), end=(2026, 10)):
    y, m = start
    while (y, m) <= end:
        for d in (5, 15, 25):
            yield datetime(y, m, d, 14, 0, tzinfo=timezone.utc)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def parse_gkg(raw):
    """Vrátí (n_records, n_with_title, rows) z obsahu .gkg.csv (bytes)."""
    n = nt = 0
    rows = []
    for line in raw.decode("utf-8", "replace").splitlines():
        f = line.split("\t")
        if len(f) < 27:
            continue
        n += 1
        mt = re.search(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", f[26])
        if not mt:
            continue
        nt += 1
        title = mt.group(1).strip()
        xrp, only, score = classify(title)
        if xrp:
            rows.append(dict(gdelt_date=f[1], domain=f[3], url=f[4], title=title, xrp_only=int(only), score=score))
    return n, nt, rows


def gdelt_one(slot, cache):
    for k in range(4):
        ts = (slot + timedelta(minutes=15 * k)).strftime("%Y%m%d%H%M%S")
        url = f"http://data.gdeltproject.org/gdeltv2/{ts}.gkg.csv.zip"
        st, body = get(url)
        if st == 200 and body:
            try:
                z = zipfile.ZipFile(io.BytesIO(body))
                raw = z.read(z.namelist()[0])
            except Exception as e:  # noqa: BLE001
                return dict(slot=slot.isoformat(), file=ts, status=f"badzip:{e}", records=0, titled=0), []
            n, nt, rows = parse_gkg(raw)
            for r in rows:
                r["file"] = ts
            return dict(slot=slot.isoformat(), file=ts, status="ok", records=n, titled=nt,
                        xrp=len(rows), xrp_only=sum(r["xrp_only"] for r in rows),
                        xrp_only_s2=sum(1 for r in rows if r["xrp_only"] and abs(r["score"]) >= 2)), rows
    return dict(slot=slot.isoformat(), file="", status="missing", records=0, titled=0, xrp=0, xrp_only=0, xrp_only_s2=0), []


# ---------------- Z2 sitemaps ----------------
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
      "news": "http://www.google.com/schemas/sitemap-news/0.9"}


def parse_sitemap(body):
    """Vrátí ('index', [loc]) nebo ('urlset', [dict])."""
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    root = ET.fromstring(body)
    tag = root.tag.split("}")[-1]
    if tag == "sitemapindex":
        return "index", [e.text.strip() for e in root.iter() if e.tag.endswith("loc") and e.text]
    out = []
    for u in root:
        if not u.tag.endswith("url"):
            continue
        d = {"loc": "", "lastmod": "", "pub": "", "title": ""}
        for e in u.iter():
            t = e.tag.split("}")[-1]
            if t == "loc" and not d["loc"] and e.text:
                d["loc"] = e.text.strip()
            elif t == "lastmod" and e.text:
                d["lastmod"] = e.text.strip()
            elif t == "publication_date" and e.text:
                d["pub"] = e.text.strip()
            elif t == "title" and e.text and e.tag.startswith("{" + NS["news"]):
                d["title"] = e.text.strip()
        out.append(d)
    return "urlset", out


def time_precision(s):
    if not s:
        return "none"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return "date"
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", s):
        return "minute"
    return "other"


def year_of(d):
    for k in ("pub", "lastmod"):
        m = re.match(r"^(\d{4})-(\d{2})", d.get(k) or "")
        if m:
            return int(m.group(1)), int(m.group(2))
    m = re.search(r"/(20\d{2})/(\d{2})/", d.get("loc", ""))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def crawl_site(domain, max_maps=4000, delay=0.2):
    st, body = get(f"https://{domain}/robots.txt", timeout=30)
    roots = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", body.decode("utf-8", "replace")) if st == 200 else []
    if not roots:
        roots = [f"https://{domain}/sitemap.xml"]
    seen, queue, urls, errors, n_maps = set(), list(roots), [], [], 0
    while queue and n_maps < max_maps:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        n_maps += 1
        st, body = get(sm, timeout=60)
        time.sleep(delay)
        if st != 200:
            errors.append(f"{st} {sm}")
            continue
        try:
            kind, items = parse_sitemap(body)
        except Exception as e:  # noqa: BLE001
            errors.append(f"parse {sm} {e}")
            continue
        if kind == "index":
            queue.extend(i for i in items if i not in seen)
        else:
            urls.extend(items)
    return dict(domain=domain, robots_status=st, roots=roots, sitemaps_read=n_maps, queue_left=len(queue),
                errors=errors[:50], n_errors=len(errors)), urls


def xrp_url(d):
    slug = urlsplit(d["loc"]).path.lower()
    return bool(re.search(r"(?<![a-z])(xrp|ripple|xrpl)(?![a-z])", slug)) or bool(XRP_RE.search(d.get("title", "")))


def to_utc(s):
    try:
        if re.match(r"^\d{14}$", s):
            return datetime.strptime(s, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else None
    except ValueError:
        return None


def norm_url(u):
    p = urlsplit(u.strip())
    return (p.hostname or "").lower().removeprefix("www.") + p.path.rstrip("/").lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--sites", default="cointelegraph.com,coindesk.com,decrypt.co")
    a = ap.parse_args()
    out = a.outdir
    # Z1
    slots = list(sample_slots())
    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(lambda s: gdelt_one(s, None), slots))
    files = [r[0] for r in res]
    titles = [row for r in res for row in r[1]]
    with open(f"{out}/gdelt_files.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ["slot", "file", "status", "records", "titled", "xrp", "xrp_only", "xrp_only_s2"])
        w.writeheader(); [w.writerow({k: f.get(k, 0) for k in w.fieldnames}) for f in files]
    with open(f"{out}/gdelt_xrp_titles.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ["file", "gdelt_date", "domain", "url", "title", "xrp_only", "score"])
        w.writeheader(); w.writerows(titles)
    print(f"GDELT: {sum(f['status']=='ok' for f in files)}/{len(files)} files ok, {len(titles)} XRP titles", flush=True)
    # Z2
    summ, xrows = [], []
    for site in [s for s in a.sites.split(",") if s]:
        meta, urls = crawl_site(site)
        xs = [u for u in urls if xrp_url(u)]
        prec = {}
        for u in xs:
            p = time_precision(u["pub"]) if u["pub"] else "lastmod_" + time_precision(u["lastmod"])
            prec[p] = prec.get(p, 0) + 1
        meta.update(n_urls=len(urls), n_xrp=len(xs), precision=prec,
                    with_pub=sum(1 for u in urls if u["pub"]), with_lastmod=sum(1 for u in urls if u["lastmod"]))
        summ.append(meta)
        for u in xs:
            y, m = year_of(u)
            xrows.append(dict(site=site, loc=u["loc"], pub=u["pub"], lastmod=u["lastmod"], title=u["title"], year=y, month=m))
        print(f"SITEMAP {site}: maps={meta['sitemaps_read']} urls={len(urls)} xrp={len(xs)} errors={meta['n_errors']} prec={prec}", flush=True)
    with gzip.open(f"{out}/sitemap_xrp_urls.csv.gz", "wt", newline="") as fh:
        w = csv.DictWriter(fh, ["site", "loc", "pub", "lastmod", "title", "year", "month"])
        w.writeheader(); w.writerows(xrows)
    with open(f"{out}/sitemap_summary.json", "w") as fh:
        json.dump(summ, fh, indent=1)
    # Z3 lag
    pubmap = {}
    for r in xrows:
        t = to_utc(r["pub"]) if r["pub"] else None
        if t:
            pubmap[norm_url(r["loc"])] = t
    lags = []
    for t in titles:
        k = norm_url(t["url"])
        if k in pubmap:
            g = to_utc(t["gdelt_date"])
            lags.append(dict(url=t["url"], gdelt=t["gdelt_date"], pub=pubmap[k].isoformat(),
                             lag_min=round((g - pubmap[k]).total_seconds() / 60, 1)))
    with open(f"{out}/lag.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ["url", "gdelt", "pub", "lag_min"]); w.writeheader(); w.writerows(lags)
    print(f"LAG matches: {len(lags)}", flush=True)
    json.dump(dict(generated_utc=datetime.now(timezone.utc).isoformat(), n_slots=len(slots)),
              open(f"{out}/run_meta.json", "w"))


if __name__ == "__main__":
    main()
