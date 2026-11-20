"""K10 ArchivedLabel <-> Snapshot linkage (DATA ONLY, no prices, returns or orders).

Single entry point on top of the one existing ``validate_labels`` gate (dialog
0387/0388): every archived exchange label must be backed by exactly one verified
Wayback snapshot whose URL, capture time and SHA-256 equal the label's declared
provenance, and whose immutable bytes literally contain the labelled account.

Fail closed: any missing, extra, ambiguous or mismatched snapshot raises. A
verified link proves the label text was publicly archived before the sample; it
does NOT prove the exchange attribution is correct.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from research.k10_label_pit_gate import ArchivedLabel, validate_labels
from research.k10_snapshot_bytes_gate import Snapshot, verify_snapshot


def validate_linked_labels(
    labels: Sequence[ArchivedLabel],
    snapshots: Sequence[Snapshot],
    sample_start: datetime,
) -> dict[str, ArchivedLabel]:
    """Return PIT labels keyed by account only if every label has a verified snapshot.

    - ``validate_labels`` runs first (address, UTC, strict ``captured_at < sample_start``,
      no duplicate accounts).
    - Snapshots are keyed by ``source_url``; duplicates are rejected, and every
      snapshot must be referenced by at least one label (no unused evidence).
    - Each snapshot is verified with ``decision_at = sample_start`` (capture time
      from the Wayback URL, byte digest).
    - Label ``captured_at`` / ``content_sha256`` must equal the snapshot's.
    - The account address must appear verbatim in the snapshot bytes.
    """
    labels = list(labels)
    pit = validate_labels(labels, sample_start)
    by_url: dict[str, Snapshot] = {}
    for snap in snapshots:
        if not isinstance(snap, Snapshot):
            raise ValueError("invalid snapshot")
        if snap.source_url in by_url:
            raise ValueError("duplicate snapshot for source URL")
        by_url[snap.source_url] = snap
    verified: dict[str, str] = {}
    used: set[str] = set()
    for label in labels:
        snap = by_url.get(label.source_url)
        if snap is None:
            raise ValueError("label without archived snapshot")
        if label.source_url not in verified:
            if snap.decision_at != sample_start:
                raise ValueError("snapshot decision time must equal sample_start")
            verified[label.source_url] = verify_snapshot(snap)
        if snap.captured_at != label.captured_at:
            raise ValueError("label capture time differs from snapshot")
        if verified[label.source_url] != label.content_sha256:
            raise ValueError("label digest differs from verified snapshot bytes")
        if label.account.encode("ascii") not in snap.content:
            raise ValueError("labelled account not present in archived bytes")
        used.add(label.source_url)
    if set(by_url) != used:
        raise ValueError("snapshot not referenced by any label")
    return pit
