"""Independent structural audit of the saved Polymarket source decision."""
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
result = json.loads((root / "source_audit.json").read_text())
checks, failures = 0, []


def check(value, message):
    global checks
    checks += 1
    if not value:
        failures.append(message)


check(result["strategy"] == "POLYMARKET_XRP_SIGNAL_V1", "strategy")
check(result["performance_evaluated"] is False, "no performance claim")
check(result["source_pass"] is False, "source decision")
check(result["coverage"]["available_days"] < 730, "history duration")
check(result["coverage"]["series_age_days"] < 730, "series age")
check(result["probe_market"]["trade_records"] > 0, "trade probe")
check(result["probe_market"]["legacy_price_points"] == 0, "legacy history")
check(result["probe_market"]["v2_price_points"] == 0, "v2 history")
check(result["first_page"]["events"] == 100, "event page")
check(len(result["manifest"]) == 6, "manifest count")
check(len({item["url"] for item in result["manifest"]}) == 6, "manifest urls")
check(all(item["bytes"] > 0 and len(item["sha256"]) == 64 for item in result["manifest"]), "manifest hashes")
check(not result["gates"]["two_calendar_years"], "two-year gate")
check(not result["gates"]["price_history_probe_nonempty"], "history gate")
check(result["status"].startswith("TEST NEDOKONCEN"), "status")
output = {"checks": checks, "failures": failures, "passed": not failures}
(root / "audit.json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(output)); raise SystemExit(bool(failures))
