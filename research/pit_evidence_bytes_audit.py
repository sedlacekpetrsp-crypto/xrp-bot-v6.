"""Read-only SHA-256 evidence verification for PAPER research manifests.

This verifies actual file bytes, not historical availability or source authenticity.
No trading, backtest, network access, or production writes.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def verify_manifest_bytes(root: Path, entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return one result per entry; never follow symlinks or escape root.

    Each entry must contain relative POSIX path and lowercase sha256.
    Failure is fail-closed and recorded as status != OK.
    """
    root = Path(root).resolve(strict=True)
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        path = entry.get("path", "")
        digest = entry.get("sha256", "")
        record = {"path": path, "status": "INVALID"}
        parts = PurePosixPath(path)
        if (not path or "\\" in path or parts.is_absolute()
                or any(p in (".", "..") for p in path.split("/"))
                or not _SHA256.fullmatch(digest)):
            results.append(record)
            continue
        if path in seen:
            record["status"] = "DUPLICATE"
            results.append(record)
            continue
        seen.add(path)
        candidate = root.joinpath(*parts.parts)
        try:
            if candidate.is_symlink() or not candidate.is_file():
                record["status"] = "MISSING_OR_LINK"
            elif not candidate.resolve().is_relative_to(root):
                record["status"] = "ESCAPE"
            else:
                h = hashlib.sha256()
                with candidate.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(chunk)
                record["status"] = "OK" if h.hexdigest() == digest else "HASH_MISMATCH"
        except (OSError, ValueError):
            record["status"] = "READ_ERROR"
        results.append(record)
    return results
