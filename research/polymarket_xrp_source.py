"""Pure validation helpers for official Polymarket XRP source coverage."""
import datetime as dt
import json

UTC = dt.timezone.utc


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def validate_series(payload):
    rows = json.loads(payload)
    if len(rows) != 1:
        raise ValueError("series cardinality")
    row = rows[0]
    if row.get("slug") != "xrp-up-or-down-5m" or row.get("recurrence") != "5m":
        raise ValueError("series identity")
    return {"id": str(row["id"]), "created_at": parse_time(row["createdAt"]), "active": bool(row["active"])}


def validate_events(payload):
    rows = json.loads(payload)
    starts = []
    for row in rows:
        if not row["slug"].startswith("xrp-updown-5m-") or not row.get("closed"):
            raise ValueError("event identity")
        start, end = parse_time(row["startTime"]), parse_time(row["endDate"])
        if (end - start).total_seconds() != 300:
            raise ValueError("event duration")
        starts.append(start)
    if any(b <= a for a, b in zip(starts, starts[1:])):
        raise ValueError("event order")
    return starts


def validate_market(payload):
    row = json.loads(payload)
    outcomes = json.loads(row["outcomes"])
    token_ids = json.loads(row["clobTokenIds"])
    if outcomes != ["Up", "Down"] or len(token_ids) != 2:
        raise ValueError("token mapping")
    event = row["events"][0]
    if event.get("seriesSlug") != "xrp-up-or-down-5m" or event.get("resolutionSource") != "https://data.chain.link/streams/xrp-usd":
        raise ValueError("market provenance")
    return {"condition_id": row["conditionId"], "up_token": token_ids[0], "down_token": token_ids[1], "volume": float(row["volume"]), "start": parse_time(event["startTime"]), "end": parse_time(event["endDate"])}


def validate_trades(payload, market):
    rows = json.loads(payload)
    previous = None
    for row in rows:
        if row["conditionId"] != market["condition_id"]:
            raise ValueError("trade market")
        if row["asset"] not in (market["up_token"], market["down_token"]):
            raise ValueError("trade token")
        if not 0 < float(row["price"]) < 1 or float(row["size"]) <= 0:
            raise ValueError("trade values")
        timestamp = int(row["timestamp"])
        if previous is not None and timestamp > previous:
            raise ValueError("trade order")
        previous = timestamp
    return rows


def coverage_decision(series, first_event, as_of, minimum_days=730):
    available_days = (as_of - first_event).days
    series_age_days = (as_of - series["created_at"]).days
    gates = {"two_calendar_years": available_days >= minimum_days, "series_age_730_days": series_age_days >= minimum_days}
    return {"available_days": available_days, "series_age_days": series_age_days, "gates": gates, "source_pass": all(gates.values())}
