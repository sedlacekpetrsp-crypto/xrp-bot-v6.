"""PAPER G1 source-manifest readiness gate (metadata only; no archive I/O).

This is deliberately narrower than data QA: passing it does NOT prove raw
archive integrity, trade continuity, timestamp ordering, or PIT feature safety.
"""
from __future__ import annotations

from typing import Mapping

from .source_manifest import validate_manifest


def g1_manifest_readiness_issues(record: Mapping[str, object]) -> list[str]:
    """Fail closed unless metadata is valid, independently QA-verified and PIT-capable.

    This pure function must not be used as a substitute for verifying the
    archived trade data or for the eventual runner's full preflight receipt.
    """
    issues = validate_manifest(record)
    if issues:
        return issues
    if record["qa_status"] != "verified":
        issues.append("source_not_verified")
    if record["point_in_time_supported"] is not True:
        issues.append("pit_not_supported")
    return issues
