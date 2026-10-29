"""Reproducible official-source feasibility audit; no performance evaluation."""
import datetime as dt
import hashlib
import json
import pathlib
import sys
import urllib.request

from research.polymarket_xrp_source import UTC, coverage_decision, validate_events, validate_market, validate_series, validate_trades

SLUG = "xrp-updown-5m-1776494100"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "xrp-research/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def manifest(name, url, payload):
    return {"name": name, "url": url, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def main():
    destination = pathlib.Path(sys.argv[1]); destination.mkdir(parents=True, exist_ok=True)
    urls = {
        "series": "https://gamma-api.polymarket.com/series?slug=xrp-up-or-down-5m",
        "first_events": "https://gamma-api.polymarket.com/events?series_id=10685&closed=true&limit=100&offset=0&order=startTime&ascending=true",
        "probe_market": f"https://gamma-api.polymarket.com/markets/slug/{SLUG}",
    }
    payloads = {name: fetch(url) for name, url in urls.items()}
    series = validate_series(payloads["series"].decode())
    starts = validate_events(payloads["first_events"].decode())
    market = validate_market(payloads["probe_market"].decode())
    dynamic_urls = {
        "legacy_price_history": f"https://clob.polymarket.com/prices-history?market={market['up_token']}&interval=max&fidelity=1",
        "v2_price_history": f"https://data-api.polymarket.com/v2/prices-history?token_id={market['up_token']}&interval=max&fidelity=60",
        "probe_trades": f"https://data-api.polymarket.com/trades?market={market['condition_id']}&limit=10000",
    }
    payloads.update({name: fetch(url) for name, url in dynamic_urls.items()})
    urls.update(dynamic_urls)
    trades = validate_trades(payloads["probe_trades"].decode(), market)
    legacy_history = json.loads(payloads["legacy_price_history"])["history"]
    v2_history = json.loads(payloads["v2_price_history"])["data"]
    coverage = coverage_decision(series, starts[0], dt.datetime(2026, 10, 29, tzinfo=UTC))
    gates = {
        **coverage["gates"],
        "official_trade_probe_nonempty": len(trades) > 0,
        "price_history_probe_nonempty": bool(legacy_history or v2_history),
        "daily_95pct_completeness": False,
        "one_thousand_eligible_markets": False,
    }
    result = {
        "strategy": "POLYMARKET_XRP_SIGNAL_V1",
        "status": "TEST NEDOKONCEN: official five-minute XRP series has less than two years of history and price-history probes are empty",
        "performance_evaluated": False,
        "as_of": "2026-10-29T00:00:00Z",
        "series": {"id": series["id"], "created_at": series["created_at"].isoformat(), "active": series["active"]},
        "first_page": {"events": len(starts), "first_start": starts[0].isoformat(), "last_start": starts[-1].isoformat(), "ordered_five_minute_events": True},
        "probe_market": {"slug": SLUG, "start": market["start"].isoformat(), "end": market["end"].isoformat(), "reported_volume": market["volume"], "trade_records": len(trades), "legacy_price_points": len(legacy_history), "v2_price_points": len(v2_history)},
        "coverage": coverage,
        "gates": gates,
        "source_pass": False,
        "manifest": [manifest(name, urls[name], payloads[name]) for name in urls],
        "limitations": [
            "The official series creation time is 2025-11-21 and the earliest ordered closed event page begins 2025-12-18, less than the frozen two-year requirement.",
            "Both official price-history probes returned zero points for a resolved market with reported volume and nonempty public trades; trades can reconstruct matched prices but not historical best bid/ask or unfilled liquidity.",
            "A complete event/trade crawl and Binance join were deliberately not treated as a backtest because the frozen multi-year source gate already fails.",
            "No Binance proxy, resolved outcome, webpage odds or missing Polymarket price was fabricated.",
        ],
        "next_step": "Accumulate immutable forward snapshots and trade records until the unchanged two-year source gate is met, or obtain a complete official archive; only then run the preregistered chronological performance test.",
    }
    (destination / "source_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "trade_records": len(trades), "coverage": coverage, "gates": gates}, indent=2))


if __name__ == "__main__":
    main()
