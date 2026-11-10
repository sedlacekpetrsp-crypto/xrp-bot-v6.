"""K3 krok 0b: hodinová datová brána (jen časová razítka). Viz PROTOCOL_0B.md. PAPER, veřejná data, bez secrets.

  python -m research.k3_funding_audit.step0b run --outdir research/k3_funding_audit
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request

from research.k3_funding_audit.audit import DAY_MS, H_MS, HL_URL, Pacer, STATUS, http, map_symbol

MIN_DAYS = 548
MIN_COV = 0.95
MIN_ONHOUR = 0.99
MIN_SYMBOLS = 20
LOOKBACK_DAYS = 1100
MAX_LAG_DAYS = 2
BV = "https://data.binance.vision/data/futures/um/monthly/markPriceKlines"


def longest_run(ts: list[int], min_cov: float = MIN_COV) -> tuple[int, int, float]:
    """Nejdelší okno končící poslední svíčkou s pokrytím ≥ min_cov (hledá nejstarší start). Vrací (start, end, cov)."""
    ts = sorted(set(ts))
    if not ts:
        return 0, 0, 0.0
    end = ts[-1]
    best = (end, end, 1.0)
    n = len(ts)
    for i in range(n):  # okno [ts[i], end]
        expected = (end - ts[i]) // H_MS + 1
        cov = (n - i) / expected
        if cov >= min_cov:
            return ts[i], end, cov
    return best


def on_hour(ts: list[int]) -> float:
    if not ts:
        return 0.0
    return sum(1 for t in ts if min(t % H_MS, H_MS - t % H_MS) <= 60_000) / len(ts)


def month_list(start_ms: int, end_ms: int) -> list[str]:
    y, m = time.gmtime(start_ms / 1000)[:2]
    y1, m1 = time.gmtime(end_ms / 1000)[:2]
    out = []
    while (y, m) < (y1, m1):  # aktuální měsíc ještě nemá měsíční soubor
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def gate(row: dict, now_ms: int) -> bool:
    return (row["hl_days"] >= MIN_DAYS and row["hl_cov"] >= MIN_COV
            and (now_ms - row["hl_last"]) <= MAX_LAG_DAYS * DAY_MS
            and row["bn_month_share"] >= MIN_COV and row["hl_onhour"] >= MIN_ONHOUR)


def hl_candle_ts(coin: str, now_ms: int, pacer: Pacer) -> list[int]:
    start, out = now_ms - LOOKBACK_DAYS * DAY_MS, []
    for _ in range(40):
        req = {"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": start, "endTime": now_ms}}
        code, body = http(HL_URL, pacer, json.dumps(req).encode())
        if code != 200:
            break
        rows = json.loads(body or b"[]")
        if not rows:
            break
        ts = [int(r["t"]) for r in rows]
        out.extend(ts)
        nxt = max(ts) + H_MS
        if nxt <= start or nxt > now_ms - H_MS:
            break
        start = nxt
    return sorted(set(out))


def head(url: str, pacer: Pacer) -> int:
    for i in range(4):
        pacer.wait()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if e.code >= 500 or e.code == 429:
                time.sleep(2 ** i)
                continue
            return e.code
        except Exception:
            time.sleep(2 ** i)
    return -1


def cmd_run(a):
    now_ms = int(time.time() * 1000)
    with open(os.path.join(a.outdir, "pairs_overlap.csv")) as f:
        syms = [r["symbol"] for r in csv.DictReader(f) if r["pair"] == "binance-hyperliquid" and r["qualifies"] == "True"]
    if a.limit:
        syms = syms[: a.limit]
    hp, bp, rows = Pacer(2.4), Pacer(0.05), []
    for s in syms:
        coin = map_symbol(s, "hyperliquid")
        ts = hl_candle_ts(coin, now_ms, hp)
        st, en, cov = longest_run(ts)
        months = month_list(st, en) if ts else []
        ok = sum(1 for mo in months
                 if head(f"{BV}/{s}/1h/{s}-1h-{mo}.zip", bp) == 200
                 and head(f"{BV}/{s}/1h/{s}-1h-{mo}.zip.CHECKSUM", bp) == 200)
        r = {"symbol": s, "hl_coin": coin, "hl_n": len(ts), "hl_first": ts[0] if ts else 0, "hl_last": ts[-1] if ts else 0,
             "hl_days": round((en - st) / DAY_MS, 1) if ts else 0.0, "hl_cov": round(cov, 4), "hl_onhour": round(on_hour(ts), 4),
             "bn_months": len(months), "bn_months_ok": ok, "bn_month_share": round(ok / len(months), 4) if months else 0.0}
        r["passes"] = gate(r, now_ms)
        rows.append(r)
        print(s, r["hl_n"], r["hl_days"], r["passes"], flush=True)
    with open(os.path.join(a.outdir, "step0b_by_symbol.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    days = sorted(r["hl_days"] for r in rows)
    npass = sum(r["passes"] for r in rows)
    summ = {"run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ms / 1000)), "symbols": len(rows), "passing": npass,
            "verdict": "GO" if npass >= MIN_SYMBOLS else "DATA NO-GO", "hl_days_min": days[0], "hl_days_median": days[len(days) // 2],
            "hl_days_max": days[-1], "hl_n_max": max(r["hl_n"] for r in rows), "http_status": dict(STATUS)}
    with open(os.path.join(a.outdir, "step0b_summary.json"), "w") as f:
        json.dump(summ, f, indent=1)
    print(json.dumps(summ, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run")
    r.add_argument("--outdir", required=True)
    r.add_argument("--limit", type=int, default=0)
    a = p.parse_args(argv)
    cmd_run(a)


if __name__ == "__main__":
    main()
