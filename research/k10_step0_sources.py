"""K10 step 0 §6.2: preregistered label sources + frozen attribution rules (offline, no network).

Implements sources.json parse_rules R1-R5 for already-verified snapshot bytes. Output per account:
an allowlisted exchange entity or None ("unknown", stays in the denominator). Fail closed.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

SOURCES_PATH = Path(__file__).resolve().parent / "k10_step0" / "sources.json"


def load_sources(path: Path = SOURCES_PATH) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    alias_to_entity: dict[str, str] = {}
    for entity, aliases in cfg["exchange_allowlist"].items():
        for a in aliases:
            n = normalize(a)
            if n != a:
                raise ValueError(f"allowlist alias not normalized: {a!r}")
            if n in alias_to_entity:
                raise ValueError(f"alias {a!r} maps to two entities")
            alias_to_entity[n] = entity
    cfg["_alias_to_entity"] = alias_to_entity
    return cfg


def normalize(name: str) -> str:
    """R3: lowercase, NFKC, trim, collapse whitespace. No suffix stripping."""
    return " ".join(unicodedata.normalize("NFKC", name).lower().split())


def _entity(name, alias_to_entity) -> str | None:
    """R4: exact allowlist match -> entity; otherwise a non-exchange token."""
    if not isinstance(name, str) or not name.strip():
        return None
    n = normalize(name)
    return alias_to_entity.get(n, "__other__:" + n)


def parse_s1(raw: bytes) -> list[tuple[str, str]]:
    """S1 well-known list -> [(account, name)]. R1/R2: only account+name, malformed => []."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for row in data:
        if isinstance(row, dict) and isinstance(row.get("account"), str) and isinstance(row.get("name"), str):
            out.append((row["account"], row["name"]))
    return out


def parse_s2(raw: bytes, account: str) -> list[tuple[str, str]]:
    """S2 account info -> [(account, accountName.name)] only if the object is about `account`."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    for k in ("account", "Account"):
        if k in data and data[k] != account:
            return []
    an = data.get("accountName")
    if not isinstance(an, dict) or not isinstance(an.get("name"), str):
        return []
    if "account" in an and an["account"] != account:
        return []
    return [(account, an["name"])]


def attribute(pairs: list[tuple[str, str]], cfg: dict) -> dict[str, str | None]:
    """R4-R6: account -> exchange entity, or None when unknown/conflicting/non-exchange."""
    a2e = cfg["_alias_to_entity"]
    seen: dict[str, set] = {}
    for account, name in pairs:
        ent = _entity(name, a2e)
        if ent is None:
            continue
        seen.setdefault(account, set()).add(ent)
    out: dict[str, str | None] = {}
    for account, ents in seen.items():
        if len(ents) == 1:
            (e,) = ents
            out[account] = None if e.startswith("__other__:") else e
        else:
            out[account] = None  # R5 conflict
    return out


def non_allowlisted_names(pairs: list[tuple[str, str]], cfg: dict) -> list[str]:
    """R7 diagnostic only: names that were NOT counted as exchange."""
    a2e = cfg["_alias_to_entity"]
    return sorted({normalize(n) for _, n in pairs if isinstance(n, str) and n.strip() and normalize(n) not in a2e})
