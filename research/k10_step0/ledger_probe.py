"""K10 step 0 §6.3: XRPL full-history ledger source feasibility probe (DATA ONLY, Actions only).

Measures only availability, exact ledger counts of the four 90-day ranking windows (PROTOCOL §1) and
cost of fetching them (bytes, tx count, latency). No prices, no labels, no Wayback/CDX, no returns.
Preregistered verdict (frozen 2026-11-18 before the probe ran):
  FEASIBLE_DIRECT   <=> estimated sequential fetch time of all 4 windows <= 5 h AND est. bytes <= 50 GB
  INFEASIBLE_DIRECT otherwise -> no fallback chosen here; any change of cohort source/definition is a
                    protocol amendment that needs ChatGPT review (dialog), never an ad-hoc switch.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone

RIPPLE_EPOCH = 946684800
HOSTS = ["https://s2.ripple.com:51234/", "https://xrplcluster.com/"]
YEARS = (2020, 2021, 2022, 2023)
WINDOW_DAYS = 90
SAMPLE_LEDGERS = 20
MAX_HOURS = 5.0
MAX_GB = 50.0
FIRST_LEDGER = 32570


def make_rpc(host: str, timeout: float = 30.0, pause: float = 0.2):
    def rpc(method: str, params: dict) -> tuple[dict, int, float]:
        body = json.dumps({"method": method, "params": [params]}).encode()
        req = urllib.request.Request(host, data=body, headers={"content-type": "application/json"})
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
        dt = time.monotonic() - t0
        time.sleep(pause)
        res = json.loads(raw)["result"]
        if res.get("status") != "success":
            raise RuntimeError(f"{method}: {res.get('error', 'not success')}")
        return res, len(raw), dt
    return rpc


def close_unix(rpc, idx: int) -> int:
    res, _, _ = rpc("ledger", {"ledger_index": idx, "transactions": False})
    led = res["ledger"]
    if not res.get("validated", led.get("validated", True)):
        raise RuntimeError(f"ledger {idx} not validated")
    return int(led["close_time"]) + RIPPLE_EPOCH


def first_at_or_after(rpc, t_unix: int, lo: int, hi: int) -> int:
    """Smallest ledger index in [lo, hi] with close_time >= t_unix (close_time is non-decreasing)."""
    if close_unix(rpc, hi) < t_unix:
        raise RuntimeError("target after validated range")
    while lo < hi:
        mid = (lo + hi) // 2
        if close_unix(rpc, mid) >= t_unix:
            hi = mid
        else:
            lo = mid + 1
    return lo


def sample_cost(rpc, start: int, n: int) -> dict:
    nbytes = ntx = npay = 0
    secs = 0.0
    for idx in range(start, start + n):
        res, b, dt = rpc("ledger", {"ledger_index": idx, "transactions": True, "expand": True})
        txs = res["ledger"].get("transactions", [])
        nbytes += b
        secs += dt
        ntx += len(txs)
        npay += sum(1 for t in txs if isinstance(t, dict) and t.get("TransactionType") == "Payment")
    return {"ledgers": n, "bytes": nbytes, "seconds": round(secs, 3), "tx": ntx, "payments": npay}


def verdict(windows: list[dict]) -> dict:
    if not windows or any(w["count"] <= 0 or w["sample"]["ledgers"] <= 0 for w in windows):
        return {"verdict": "INVALID_SAMPLE", "reason": "empty windows or zero sample ledgers"}
    hours = sum(w["count"] * w["sample"]["seconds"] / w["sample"]["ledgers"] for w in windows) / 3600
    gb = sum(w["count"] * w["sample"]["bytes"] / w["sample"]["ledgers"] for w in windows) / 1e9
    ok = hours <= MAX_HOURS and gb <= MAX_GB
    return {"est_hours_sequential": round(hours, 2), "est_gb": round(gb, 2),
            "thresholds": {"max_hours": MAX_HOURS, "max_gb": MAX_GB},
            "verdict": "FEASIBLE_DIRECT" if ok else "INFEASIBLE_DIRECT"}


def probe(rpc_for_host, hosts=HOSTS, years=YEARS, n_sample=SAMPLE_LEDGERS) -> dict:
    out: dict = {"hosts": [], "windows": [], "result": None}
    chosen = None
    for h in hosts:
        rec = {"host": h}
        try:
            rpc = rpc_for_host(h)
            info, _, _ = rpc("server_info", {})
            si = info["info"]
            rec.update(complete_ledgers=si.get("complete_ledgers"), build_version=si.get("build_version"),
                       validated=si.get("validated_ledger", {}).get("seq"))
            # full history check: earliest ledger must be fetchable
            close_unix(rpc, FIRST_LEDGER)
            rec["full_history"] = True
            if chosen is None:
                chosen = (h, rpc, int(rec["validated"]))
        except Exception as e:  # noqa: BLE001 - record and continue, fail closed below
            rec["error"] = f"{type(e).__name__}: {e}"[:300]
            rec.setdefault("full_history", False)
        out["hosts"].append(rec)
    if chosen is None:
        out["result"] = {"verdict": "DATA_SOURCE_UNAVAILABLE"}
        return out
    host, rpc, top = chosen
    out["chosen_host"] = host
    for y in years:
        start = datetime(y, 1, 1, tzinfo=timezone.utc)
        w0 = int((start - timedelta(days=WINDOW_DAYS)).timestamp())
        a = first_at_or_after(rpc, w0, FIRST_LEDGER, top)
        b = first_at_or_after(rpc, int(start.timestamp()), a, top)
        if b <= a:
            raise RuntimeError(f"empty ranking window {y}: {a}..{b}")
        # Never sample ledgers outside the preregistered ranking window.
        actual_sample = min(n_sample, b - a)
        if actual_sample <= 0:
            raise RuntimeError(f"invalid sample size for {y}: {actual_sample}")
        out["windows"].append({"year": y, "first_ledger": a, "end_exclusive": b, "count": b - a,
                               "sample": sample_cost(rpc, a, actual_sample)})
    out["result"] = verdict(out["windows"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="research/k10_step0/ledger_probe.json")
    args = ap.parse_args()
    res = probe(make_rpc)
    res["generated_at"] = datetime.now(timezone.utc).isoformat()
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    print(json.dumps(res["result"]), "windows:", [(w["year"], w["count"]) for w in res["windows"]])


if __name__ == "__main__":
    main()
