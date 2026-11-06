"""Forward PAPER — RSI(2) pullback (výjimka schválená vlastníkem 2026-11-06, post-hoc, B6 nesplněno).

Výhradně PAPER výzkum: žádné objednávky, žádné klíče, žádný Render. Pravidla PŘESNĚ jako PR #13:
close > SMA200 a RSI(2, Wilder) < 10 ⇒ nákup za open t+1; close > SMA5 ⇒ prodej za open t+1;
bez stopu. Poplatek 0,095 % + skluz 0,02 % na stranu; účtuje se ×1 i ×2. Každé aktivum = sleeve 10 000 USD.

Forward začíná první denní svíčkou po START (signály z dřívějších dnů se nepoužijí). Otevřená pozice se
na konci NEuzavírá, jen se ocení. Celé se to přepočítá z dat při každém spuštění (deterministicky).

    python research/forward/rsi2_pullback/run.py --cache /tmp/vision --outdir research/forward/rsi2_pullback
"""
import argparse
import csv
import hashlib
import io
import json
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

START = date(2026, 11, 7)            # první svíčka po schválení 2026-11-06
INTERIM_REVIEW = date(2026, 12, 16)  # 40 dní: kontrola shody s backtestem
MIN_EVAL = date(2027, 1, 5)          # 60 dní
FEE, SLIP = 0.00095, 0.0002
RSI_N, RSI_ENTRY, SMA_TREND, SMA_EXIT = 2, 10.0, 200, 5
SLEEVE = 10_000.0
HISTORY_FROM = (2025, 9)             # dost na SMA200 před startem
BASE = "https://data.binance.vision/data/spot"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def parse(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    out = []
    for row in csv.reader(io.StringIO(text)):
        if not row or not row[0].strip().isdigit():
            continue
        ts = int(row[0])
        if ts > 10 ** 14:
            ts //= 1000
        out.append({"ts": ts, "open": float(row[1]), "high": float(row[2]), "low": float(row[3]), "close": float(row[4])})
    return out


def day(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc).date()


def get(cache, url, fetcher, allow_404=True):
    p = Path(cache) / url.rsplit("/", 1)[1]
    if p.exists():
        return p.read_bytes()
    try:
        data = fetcher(url)
    except urllib.error.HTTPError as e:
        if allow_404 and e.code == 404:
            return None
        raise
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return data


def load(symbol, cache, today, fetcher=fetch):
    """Měsíční archivy do minulého měsíce + denní archivy aktuálního (a případně minulého) měsíce."""
    bars, manifest = {}, []
    y, m = HISTORY_FROM
    last_full = (today.replace(day=1) - timedelta(days=1))
    while (y, m) <= (last_full.year, last_full.month):
        url = f"{BASE}/monthly/klines/{symbol}/1d/{symbol}-1d-{y}-{m:02d}.zip"
        data = get(cache, url, fetcher)
        if data is None:  # měsíční archiv ještě není ⇒ denní soubory
            d = date(y, m, 1)
            while d.month == m and d < today:
                durl = f"{BASE}/daily/klines/{symbol}/1d/{symbol}-1d-{d.isoformat()}.zip"
                dd = get(cache, durl, fetcher)
                if dd is not None:
                    manifest.append({"url": durl, "sha256": hashlib.sha256(dd).hexdigest()})
                    for b in parse(dd):
                        bars[b["ts"]] = b
                d += timedelta(days=1)
        else:
            manifest.append({"url": url, "sha256": hashlib.sha256(data).hexdigest()})
            for b in parse(data):
                bars[b["ts"]] = b
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    d = today.replace(day=1)
    while d < today:  # jen uzavřené dny
        durl = f"{BASE}/daily/klines/{symbol}/1d/{symbol}-1d-{d.isoformat()}.zip"
        dd = get(cache, durl, fetcher)
        if dd is not None:
            manifest.append({"url": durl, "sha256": hashlib.sha256(dd).hexdigest()})
            for b in parse(dd):
                bars[b["ts"]] = b
        d += timedelta(days=1)
    return [bars[t] for t in sorted(bars)], manifest


def rsi_wilder(closes, n=RSI_N):
    out = [None] * len(closes)
    if len(closes) <= n:
        return out
    g = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    l = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]
    ag, al = sum(g[:n]) / n, sum(l[:n]) / n
    for i in range(n, len(closes)):
        if i > n:
            ag = (ag * (n - 1) + g[i - 1]) / n
            al = (al * (n - 1) + l[i - 1]) / n
        out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1 + ag / al)
    return out


def sma(closes, n):
    out, acc = [None] * len(closes), 0.0
    for i, c in enumerate(closes):
        acc += c
        if i >= n:
            acc -= closes[i - n]
        if i >= n - 1:
            out[i] = acc / n
    return out


def forward(bars, mult, symbol):
    """Stejná logika jako PR #13 simulate(), jen bez nuceného uzavření na konci."""
    fee, slip = FEE * mult, SLIP * mult
    closes = [b["close"] for b in bars]
    rsi, s200, s5 = rsi_wilder(closes), sma(closes, SMA_TREND), sma(closes, SMA_EXIT)
    trades, curve, cash, pos, pending = [], [], SLEEVE, None, None
    for i, bar in enumerate(bars):
        d = day(bar["ts"])
        if d < START:
            continue
        if pending == "buy" and pos is None:
            px = bar["open"] * (1 + slip)
            qty = cash / (px * (1 + fee))
            pos = {"entry_day": d, "entry_px": px, "qty": qty, "entry_fee": qty * px * fee}
            cash -= qty * px + pos["entry_fee"]
        elif pending == "sell" and pos is not None:
            px = bar["open"] * (1 - slip)
            proceeds = pos["qty"] * px
            xfee = proceeds * fee
            gross = (px - pos["entry_px"]) * pos["qty"]
            trades.append({"symbol": symbol, "cost_multiplier": mult, "entry_day": pos["entry_day"].isoformat(),
                           "exit_day": d.isoformat(), "entry_px": pos["entry_px"], "exit_px": px, "qty": pos["qty"],
                           "gross_pnl": gross, "fees": pos["entry_fee"] + xfee, "net_pnl": gross - pos["entry_fee"] - xfee})
            cash += proceeds - xfee
            pos = None
        pending = None
        if pos is not None and s5[i] is not None and bar["close"] > s5[i]:
            pending = "sell"
        elif pos is None and rsi[i] is not None and rsi[i] < RSI_ENTRY and s200[i] is not None and bar["close"] > s200[i]:
            pending = "buy"
        curve.append({"symbol": symbol, "cost_multiplier": mult, "day": d.isoformat(),
                      "equity": cash + (pos["qty"] * bar["close"] if pos else 0.0),
                      "bh_equity": SLEEVE * bar["close"] / _first_open(bars)})
    open_pos = None if pos is None else {"symbol": symbol, "entry_day": pos["entry_day"].isoformat(),
                                         "entry_px": pos["entry_px"], "mark": bars[-1]["close"]}
    return trades, curve, open_pos, pending


def _first_open(bars):
    for b in bars:
        if day(b["ts"]) >= START:
            return b["open"]
    return float("nan")


def max_dd(values):
    peak, dd = None, 0.0
    for v in values:
        peak = v if peak is None else max(peak, v)
        dd = max(dd, 1 - v / peak)
    return 100 * dd


def run(symbols, cache, outdir, today=None, fetcher=fetch):
    today = today or datetime.now(timezone.utc).date()
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    all_tr, all_curve, opens, pend, manifest = [], [], [], {}, []
    for s in symbols:
        bars, man = load(s, cache, today, fetcher)
        manifest += man
        for mult in (1, 2):
            tr, cv, op, pe = forward(bars, mult, s)
            all_tr += tr
            all_curve += cv
            if mult == 1:
                if op:
                    opens.append(op)
                if pe:
                    pend[s] = pe
    with (out / "trades.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "cost_multiplier", "entry_day", "exit_day", "entry_px", "exit_px",
                                          "qty", "gross_pnl", "fees", "net_pnl"], lineterminator="\n")
        w.writeheader()
        w.writerows(all_tr)
    with (out / "equity.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "cost_multiplier", "day", "equity", "bh_equity"], lineterminator="\n")
        w.writeheader()
        w.writerows(all_curve)
    status = summarize(symbols, all_tr, all_curve, opens, pend, today)
    (out / "status.json").write_text(json.dumps(status, indent=1) + "\n")
    (out / "data_source.json").write_text(json.dumps({"archives": manifest}, indent=0) + "\n")
    (out / "STATUS.md").write_text(status_md(status))
    return status


def summarize(symbols, trades, curve, opens, pend, today):
    days = sorted({c["day"] for c in curve})
    st = {"strategy": "RSI(2) pullback (post-hoc výjimka, B6 nesplněno)", "start": START.isoformat(),
          "updated_for": days[-1] if days else None, "days": len(days), "symbols": list(symbols),
          "interim_review": INTERIM_REVIEW.isoformat(), "min_evaluation": MIN_EVAL.isoformat(),
          "open_positions": opens, "pending_next_open": pend, "by_cost": {}, "alerts": []}
    for mult in (1, 2):
        tr = [t for t in trades if t["cost_multiplier"] == mult]
        eq_by_day, bh_by_day = {}, {}
        for c in curve:
            if c["cost_multiplier"] == mult:
                eq_by_day[c["day"]] = eq_by_day.get(c["day"], 0.0) + c["equity"]
                bh_by_day[c["day"]] = bh_by_day.get(c["day"], 0.0) + c["bh_equity"]
        eq = [eq_by_day[d] for d in sorted(eq_by_day)]
        bh = [bh_by_day[d] for d in sorted(bh_by_day)]
        start_cap = SLEEVE * len(symbols)
        st["by_cost"][f"x{mult}"] = {
            "closed_trades": len(tr), "wins": sum(1 for t in tr if t["net_pnl"] > 0),
            "net_pnl_closed": sum(t["net_pnl"] for t in tr),
            "return_pct": 100 * (eq[-1] / start_cap - 1) if eq else 0.0,
            "bh_return_pct": 100 * (bh[-1] / start_cap - 1) if bh else 0.0,
            "max_dd_pct": max_dd(eq) if eq else 0.0, "bh_max_dd_pct": max_dd(bh) if bh else 0.0}
    x2 = st["by_cost"]["x2"]
    tr2 = sorted((t for t in trades if t["cost_multiplier"] == 2), key=lambda t: t["exit_day"])
    streak = 0
    for t in reversed(tr2):
        if t["net_pnl"] > 0:
            break
        streak += 1
    if x2["return_pct"] < -10:
        st["alerts"].append(f"forward ×2 {x2['return_pct']:.1f} % < −10 %")
    if streak >= 5:
        st["alerts"].append(f"{streak} ztrát po sobě")
    return st


def status_md(st):
    L = [f"# Forward PAPER — {st['strategy']}", "",
         f"Start {st['start']}, data do {st['updated_for']} ({st['days']} dní). Aktiva: {', '.join(st['symbols'])}.",
         f"Průběžná kontrola {st['interim_review']}, hlavní vyhodnocení po ≥ 30 obchodech a nejdřív {st['min_evaluation']}.", "",
         "| náklady | uzavřené obchody | výhry | výnos % (vč. otevřených) | B&H % | max DD % | B&H DD % |",
         "|---|---|---|---|---|---|---|"]
    for k, v in st["by_cost"].items():
        L.append(f"| {k} | {v['closed_trades']} | {v['wins']} | {v['return_pct']:.2f} | {v['bh_return_pct']:.2f} | "
                 f"{v['max_dd_pct']:.2f} | {v['bh_max_dd_pct']:.2f} |")
    L += ["", "Otevřené pozice: " + (", ".join(f"{o['symbol']} od {o['entry_day']}" for o in st["open_positions"]) or "žádné"),
          "Signál na příští open: " + (", ".join(f"{s}: {a}" for s, a in st["pending_next_open"].items()) or "žádný"),
          "Upozornění: " + ("; ".join(st["alerts"]) or "žádná"), "",
          "Výhradně PAPER výzkum. Post-hoc výjimka (podmínka stability B6 nesplněna). Není to zisková strategie.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args(argv)
    symbols = json.loads((Path(a.outdir) / "assets.json").read_text())["symbols"]
    print(json.dumps(run(symbols, a.cache, a.outdir), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
