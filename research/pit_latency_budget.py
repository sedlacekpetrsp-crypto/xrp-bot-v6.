"""Fail-closed point-in-time availability gate for event-driven PAPER research.

No performance evaluation or trading signals are produced.
"""
from datetime import datetime, timezone
from math import isfinite


def _utc(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be a nonempty ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def assess_event_availability(published_at, captured_at, decision_at,
                              ingest_latency_seconds, execution_latency_seconds):
    """Return a diagnostic, not a trading recommendation.

    Conservative rule: both publication and verifiable capture must precede
    decision by the full ingest budget. Execution budget is checked separately
    to prevent negative/nonfinite timing assumptions.
    """
    for name, value in (("ingest_latency_seconds", ingest_latency_seconds),
                        ("execution_latency_seconds", execution_latency_seconds)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
            raise ValueError(name + " must be finite and nonnegative")
    published = _utc(published_at)
    captured = _utc(captured_at)
    decision = _utc(decision_at)
    if captured < published:
        return {"eligible": False, "reason": "capture_precedes_publication"}
    available = max(published, captured)
    lead_seconds = (decision - available).total_seconds()
    if lead_seconds <= ingest_latency_seconds:
        return {"eligible": False, "reason": "insufficient_ingest_lead"}
    return {"eligible": True, "reason": "timing_preflight_only",
            "lead_seconds": lead_seconds,
            "earliest_execution_at": (decision.timestamp() + execution_latency_seconds)}
