#!/usr/bin/env python3
"""Bezeztrátová kontrola kompakce automation/STATE.md (CONTEXT-EFFICIENCY-01, dialog 0331 bod 5).

Kontroluje stav v okamžiku commitu kompakce (STATE.md se poté přepisuje běhy autopilota, proto
pro pozdější ověření použij `--rev <commit kompakce>`):
  1. archiv má SHA-256 uvedenou v manifestu (= původní STATE.md),
  2. segmenty manifestu pokrývají řádky 1..N archivu souvisle, bez překryvu,
  3. každý segment `state` je v novém STATE.md mezi značkami `<!-- orig:A-B -->` a `<!-- /orig -->` doslovně,
  4. rekonstrukce v původním pořadí (segmenty `state` z nového STATE.md, `archive` z archivu) má SHA-256 originálu,
  5. vypíše řádky jen v archivu, které obsahují klíčová slova rozhodnutí/stavu (pro sémantické review).
Výstup: JSON na stdout, exit 0 = OK, 1 = chyba.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

KEYWORDS = ("SCHVÁLENO", "NESCHVÁLENO", "ZAMÍTNUTO", "ČEKÁ", "STOP", "BLOK", "NO-GO", "UZAVŘENO",
            "POZASTAVENO", "NESPOUŠTĚT", "NESLUČOVAT", "NEMAZAT")
MARK_RE = re.compile(r"^<!-- orig:(\d+)-(\d+) -->\n$")
END_MARK = "<!-- /orig -->\n"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_kept(state_text: str) -> dict[tuple[int, int], str]:
    kept: dict[tuple[int, int], str] = {}
    lines = state_text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        m = MARK_RE.match(lines[i])
        if m:
            key = (int(m.group(1)), int(m.group(2)))
            j = i + 1
            while j < len(lines) and lines[j] != END_MARK:
                j += 1
            if j == len(lines):
                raise ValueError(f"neuzavřená značka orig:{key[0]}-{key[1]}")
            if key in kept:
                raise ValueError(f"duplicitní segment {key}")
            kept[key] = "".join(lines[i + 1:j])
            i = j
        i += 1
    return kept


def check(state_text: str, archive_text: str, manifest: dict) -> dict:
    errors: list[str] = []
    arch_lines = archive_text.splitlines(keepends=True)
    if sha256(archive_text) != manifest["source_sha256"]:
        errors.append("SHA-256 archivu ≠ manifest")
    expected = 1
    for seg in manifest["segments"]:
        a, b = seg["lines"]
        if a != expected or b < a:
            errors.append(f"mezera/překryv u segmentu {a}-{b} (čekáno od {expected})")
        expected = b + 1
        if seg["where"] not in ("state", "archive"):
            errors.append(f"neznámé umístění {seg['where']}")
    if expected - 1 != len(arch_lines):
        errors.append(f"segmenty končí na {expected - 1}, archiv má {len(arch_lines)} řádků")
    try:
        kept = extract_kept(state_text)
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)]}
    state_keys = {tuple(s["lines"]) for s in manifest["segments"] if s["where"] == "state"}
    if set(kept) != state_keys:
        errors.append(f"značky v STATE.md {sorted(kept)} ≠ manifest {sorted(state_keys)}")
    parts: list[str] = []
    archive_only_hits: list[dict] = []
    for seg in manifest["segments"]:
        a, b = seg["lines"]
        original = "".join(arch_lines[a - 1:b])
        if seg["where"] == "state":
            got = kept.get((a, b), "")
            if got != original:
                errors.append(f"segment {a}-{b} v STATE.md není doslovný")
            parts.append(got)
        else:
            parts.append(original)
            for n in range(a, min(b, len(arch_lines)) + 1):
                hits = [k for k in KEYWORDS if k in arch_lines[n - 1]]
                if hits:
                    archive_only_hits.append({"line": n, "keywords": hits})
    rebuilt = "".join(parts)
    rebuilt_sha = sha256(rebuilt)
    if rebuilt_sha != manifest["source_sha256"]:
        errors.append("SHA-256 rekonstrukce ≠ originál")
    return {
        "ok": not errors,
        "errors": errors,
        "source_sha256": manifest["source_sha256"],
        "rebuilt_sha256": rebuilt_sha,
        "bytes_original": len(archive_text.encode("utf-8")),
        "bytes_state": len(state_text.encode("utf-8")),
        "archive_only_keyword_lines": archive_only_hits,
    }


def _read(path: str, rev: str | None) -> str:
    if rev:
        return subprocess.run(["git", "show", f"{rev}:{path}"], check=True, capture_output=True,
                              text=True, encoding="utf-8").stdout
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", default="automation/STATE.md")
    ap.add_argument("--archive", default="automation/archive/STATE-do-20261115.md")
    ap.add_argument("--manifest", default="automation/archive/STATE-compaction-manifest.json")
    ap.add_argument("--rev", help="ověřit soubory z daného commitu (git show)")
    args = ap.parse_args(argv)
    manifest = json.loads(_read(args.manifest, args.rev))
    result = check(_read(args.state, args.rev), _read(args.archive, args.rev), manifest)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
