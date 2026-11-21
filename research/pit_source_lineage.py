"""Fail-closed provenance lineage diagnostic for PAPER event research.

This checks graph consistency only; it cannot authenticate source contents or
establish point-in-time availability. No prices, trades, or performance.
"""
from collections.abc import Mapping


class LineageError(ValueError):
    """Provenance evidence is incomplete or contradictory."""


def independent_roots(records):
    """Return distinct original source IDs; reject missing links and cycles.

    records: mapping source_id -> parent_source_id or None for original.
    A mirror/republication must point to its immediate upstream source.
    """
    if not isinstance(records, Mapping) or not records:
        raise LineageError("nonempty source mapping required")
    for source, parent in records.items():
        if not isinstance(source, str) or not source.strip() or source != source.strip():
            raise LineageError("invalid source id")
        if parent is not None:
            if not isinstance(parent, str) or not parent.strip() or parent != parent.strip():
                raise LineageError("invalid parent id")
            if parent not in records:
                raise LineageError("unresolved parent")
    roots = set()
    resolved = {}
    for start in records:
        seen = set()
        current = start
        while current not in resolved:
            if current in seen:
                raise LineageError("source lineage cycle")
            seen.add(current)
            parent = records[current]
            if parent is None:
                resolved[current] = current
                break
            current = parent
        root = resolved[current]
        for source in seen:
            resolved[source] = root
        roots.add(root)
    return tuple(sorted(roots))


def minimum_independent_sources(records, minimum=2):
    """Boolean diagnostic; invalid evidence raises rather than passing."""
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise LineageError("minimum must be a positive integer")
    return len(independent_roots(records)) >= minimum
