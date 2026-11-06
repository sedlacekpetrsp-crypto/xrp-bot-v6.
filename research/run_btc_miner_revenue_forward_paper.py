"""Append-only, isolated forward PAPER recorder for BTC miner revenue recovery."""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import urllib.parse
import urllib.request

from research.btc_miner_revenue_recovery_xrp_v1 import DAY, backtest, execution_config, make_signals, validate_prices

SOURCE_URL = "https://api.blockchain.info/charts/miners-revenue?timespan=all&format=json"
STARTED_AT = 1793908737000  # 2026-11-05T19:58:57Z
FORWARD_DAY = ((STARTED_AT // DAY) + 1) * DAY
BASELINE_SOURCE_SHA256 = "1b75573b0bdbfba5c57ea7c73ffa35d19b369a6e266cf71d61b868b46e761f72"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "xrp-paper-research/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def parse_source(payload):
    return [{"timestamp": int(row["x"]) * 1000, "value": float(row["y"])} for row in json.loads(payload)["values"]]


def parse_prices(payload):
    return [{"timestamp": int(row[0]), "open": float(row[1]), "high": float(row[2]), "low": float(row[3]), "close": float(row[4])} for row in json.loads(payload)]


def price_url(now_ms):
    last_closed_open = (now_ms // DAY - 1) * DAY
    query = urllib.parse.urlencode({"symbol": "XRPUSDT", "interval": "1d", "startTime": FORWARD_DAY - 40 * DAY, "endTime": last_closed_open + DAY - 1, "limit": 1000})
    return "https://data-api.binance.vision/api/v3/klines?" + query


def _strict(rows, name):
    times = [row["timestamp"] for row in rows]
    if any(b <= a for a, b in zip(times, times[1:])): raise ValueError(name + " timestamps")


def _freeze(existing, current, key="timestamp"):
    by_time = {row[key]: row for row in current}
    for row in existing:
        if by_time.get(row[key]) != row: raise ValueError("revision at " + str(row[key]))
    cursor = existing[-1][key] if existing else -1
    return existing + [row for row in current if row[key] > cursor]


def _closed(trades):
    return [trade for trade in trades if trade["reason"] != "FOLD_END"]


def _metrics(trades):
    gains = sum(max(0, trade["pnl"]) for trade in trades); losses = -sum(min(0, trade["pnl"]) for trade in trades)
    return {"trades": len(trades), "net_pnl": sum(trade["pnl"] for trade in trades), "expectancy": (sum(trade["pnl"] for trade in trades) / len(trades)) if trades else None, "profit_factor": (gains / losses) if losses else (None if not gains else float("inf"))}


def update_state(state, source_rows, price_rows, now_ms, source_sha256, price_sha256, source_url=SOURCE_URL, prices_url="fixture"):
    _strict(source_rows, "source"); _strict(price_rows, "price"); validate_prices(price_rows)
    if not state.get("source_tail"):
        if source_sha256 != BASELINE_SOURCE_SHA256: raise ValueError("baseline source changed before forward initialization")
        state["source_tail"] = source_rows[-104:]
        state["baseline_source_timestamp"] = source_rows[-1]["timestamp"]
    else:
        overlap = [row for row in source_rows if row["timestamp"] >= state["source_tail"][0]["timestamp"] and row["timestamp"] <= state["source_tail"][-1]["timestamp"]]
        frozen_overlap = [row for row in state["source_tail"] if row["timestamp"] >= overlap[0]["timestamp"]] if overlap else []
        if overlap != frozen_overlap: raise ValueError("source history revision")
        state["source_tail"] = _freeze(state["source_tail"], source_rows)[-104:]
    warmup = [row for row in price_rows if row["timestamp"] < FORWARD_DAY][-30:]
    prospective = [row for row in price_rows if row["timestamp"] >= FORWARD_DAY and row["timestamp"] + DAY <= now_ms]
    if not state.get("price_rows"):
        state["price_rows"] = warmup
    state["price_rows"] = _freeze(state["price_rows"], warmup + prospective)
    signals = make_signals(state["source_tail"])
    rows = []
    for price in state["price_rows"]:
        signal = signals.get(price["timestamp"]); row = dict(price)
        row.update(macro_signal=bool(signal)); row.update(signal or {}); rows.append(row)
    end = (rows[-1]["timestamp"] + DAY) if rows else FORWARD_DAY
    base, base_curve = backtest(rows, FORWARD_DAY, end, execution_config(1))
    stress, stress_curve = backtest(rows, FORWARD_DAY, end, execution_config(2))
    base = _closed(base); stress = _closed(stress)
    for label, fresh in (("base_trades", base), ("stress_trades", stress)):
        previous = state.get(label, [])
        if fresh[:len(previous)] != previous or len(fresh) < len(previous): raise ValueError("non-idempotent ledger: " + label)
        state[label] = fresh
    state.setdefault("snapshots", []).append({"observed_at_utc": dt.datetime.fromtimestamp(now_ms / 1000, dt.timezone.utc).isoformat(), "source_url": source_url, "source_sha256": source_sha256, "source_rows": len(source_rows), "price_url": prices_url, "price_sha256": price_sha256, "price_rows": len(price_rows)})
    state["last_run_utc"] = state["snapshots"][-1]["observed_at_utc"]
    state["prospective_closed_trades"] = len(base)
    state["prospective_net_pnl"] = _metrics(base)["net_pnl"]
    state["prospective_stress_net_pnl"] = _metrics(stress)["net_pnl"]
    state["base_metrics"] = _metrics(base); state["stress_metrics"] = _metrics(stress)
    state["marked_min_equity_base"] = min([10000.0] + [point["equity"] for point in base_curve])
    state["marked_min_equity_stress"] = min([10000.0] + [point["equity"] for point in stress_curve])
    state["status"] = "COLLECTING_FORWARD_PAPER"
    return state


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("state"); parser.add_argument("--now-ms", type=int)
    args = parser.parse_args(); path = pathlib.Path(args.state); state = json.loads(path.read_text())
    now_ms = args.now_ms or int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    source_payload = fetch(SOURCE_URL); prices_url = price_url(now_ms); price_payload = fetch(prices_url)
    state = update_state(state, parse_source(source_payload), parse_prices(price_payload), now_ms, hashlib.sha256(source_payload).hexdigest(), hashlib.sha256(price_payload).hexdigest(), SOURCE_URL, prices_url)
    path.write_text(json.dumps(state, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": state["status"], "trades": state["prospective_closed_trades"], "source_sha256": state["snapshots"][-1]["source_sha256"], "price_sha256": state["snapshots"][-1]["price_sha256"]}))


if __name__ == "__main__": main()
