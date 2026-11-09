"""PIT brána pro OI (HUNT-04, odpověď na 0242). Jen mechanika dostupnosti — žádné ceny ani výkonnost.

Princip FAIL CLOSED: hodnota smí vstoupit do rozhodnutí v čase t jen tehdy, když existuje
*přijatelný důkaz* o okamžiku první dostupnosti (first_available_at) a o absenci revizí.
S3 LastModified po hromadném přepisu není důkaz první publikace (AUDIT.md, publication_delay.csv).
"""
from __future__ import annotations

import dataclasses as dc
import datetime as dt

# Přijatelné typy důkazu first_available_at. Vše ostatní => FAIL CLOSED.
#  captured_live: vlastní neměnný snapshot (captured_at, SHA-256, čas odpovědi API, offset hodin serveru)
ACCEPTED_EVIDENCE = frozenset({"captured_live"})
# Explicitně odmítnuté (zdokumentované, aby se nepřidaly omylem):
REJECTED_EVIDENCE = {
    "s3_lastmodified": "přepisováno měsíce až roky po události; horní mez přepisu, ne první publikace",
    "event_time": "čas měření, ne čas zveřejnění",
    "assumed_d_plus_1": "konvence bez provenance (0242 bod 2)",
    None: "chybí provenance",
}
MAX_CLOCK_OFFSET = dt.timedelta(seconds=5)


class PITError(ValueError):
    """Bod nelze použít — chybí nebo nevyhovuje provenance (fail closed)."""


@dc.dataclass(frozen=True)
class OIPoint:
    source: str
    event_time: dt.datetime
    evidence: str | None = None
    first_available_at: dt.datetime | None = None
    captured_sha256: str | None = None
    api_response_time: dt.datetime | None = None
    clock_offset: dt.timedelta | None = None
    revisions_checked: bool = False


def usable_at(p: OIPoint) -> dt.datetime:
    """Nejdřívější okamžik, kdy smí bod vstoupit do rozhodnutí; jinak PITError."""
    if p.evidence not in ACCEPTED_EVIDENCE:
        raise PITError(f"{p.source}: evidence={p.evidence!r} — {REJECTED_EVIDENCE.get(p.evidence, 'neznámý typ')}")
    if p.first_available_at is None or p.api_response_time is None:
        raise PITError(f"{p.source}: chybí first_available_at / api_response_time")
    if not p.captured_sha256 or len(p.captured_sha256) != 64:
        raise PITError(f"{p.source}: chybí SHA-256 snapshotu")
    if p.clock_offset is None or abs(p.clock_offset) > MAX_CLOCK_OFFSET:
        raise PITError(f"{p.source}: offset hodin neznámý nebo > {MAX_CLOCK_OFFSET}")
    if not p.revisions_checked:
        raise PITError(f"{p.source}: revize neověřeny")
    if p.first_available_at < p.event_time:
        raise PITError(f"{p.source}: first_available_at před event_time")
    # konzervativně: pozdější z (zachyceno, odpověď API) + nejistota hodin
    return max(p.first_available_at, p.api_response_time) + abs(p.clock_offset)


def allowed_for_decision(p: OIPoint, decision_time: dt.datetime) -> bool:
    """True jen pokud bod byl prokazatelně dostupný nejpozději v decision_time. Chybějící provenance => False."""
    try:
        return usable_at(p) <= decision_time
    except PITError:
        return False


def data_gate(points: list[OIPoint]) -> str:
    """DATA GO jen když každý bod má přijatelnou provenance; jinak NO-GO (žádné částečné GO)."""
    if not points:
        return "NO-GO"
    for p in points:
        try:
            usable_at(p)
        except PITError:
            return "NO-GO"
    return "GO"
