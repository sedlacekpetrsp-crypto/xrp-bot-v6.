"""K11 CMS enumeration integrity gate (PAPER/data-only; no returns).

Pure diagnostic for paginated CMS snapshots. A repeated page or a code reused
with conflicting metadata can inflate event counts and falsely satisfy Step-0.
Does not alter the collector until independent review.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping


class CMSPaginationError(ValueError):
    """Fail-closed data-quality violation."""


def audit_cms_pages(pages: Iterable[Iterable[Mapping]]) -> dict:
    """Validate ordered, nonempty pages followed by exactly one terminal empty page.

    Returns a summary, not a list of eligible events. Codes are CMS article IDs,
    not token tickers; same article must never count twice. No dates are inferred.
    """
    seen_codes: dict[str, tuple[str, int]] = {}
    seen_pages: set[tuple[str, ...]] = set()
    count = 0
    identical_dupes = 0
    ended = False
    terminal_count = 0
    page_count = 0
    for page in pages:
        page_count += 1
        records = list(page)
        if not records:
            terminal_count += 1
            ended = True
            continue
        if ended:
            raise CMSPaginationError("nonempty page after terminal page")
        codes = []
        for article in records:
            code = article.get("code")
            title = article.get("title")
            release = article.get("releaseDate")
            if not isinstance(code, str) or not code.strip():
                raise CMSPaginationError("missing article code")
            if not isinstance(title, str) or not title.strip():
                raise CMSPaginationError("missing title")
            if isinstance(release, bool) or not isinstance(release, int) or release <= 0:
                raise CMSPaginationError("invalid releaseDate milliseconds")
            code = code.strip()
            codes.append(code)
            metadata = (title, release)
            if code in codes[:-1]:
                raise CMSPaginationError("duplicate article code within one CMS page")
            if code in seen_codes:
                if seen_codes[code] != metadata:
                    raise CMSPaginationError("conflicting metadata for repeated article code")
                # Review Claude: identický článek na další stránce = posun stránkování při zveřejnění nového článku
                # během výčtu. Nepočítá se podruhé (nenafukuje), jen se vykáže; celou stránku opakovanou ⇒ chyba níže.
                identical_dupes += 1
                continue
            seen_codes[code] = metadata
            count += 1
        fingerprint = tuple(codes)
        if fingerprint in seen_pages:
            raise CMSPaginationError("repeated CMS page")
        seen_pages.add(fingerprint)
    if terminal_count != 1:
        raise CMSPaginationError("missing or repeated terminal empty page")
    return {"pages_with_data": page_count - 1, "unique_articles": count, "terminal_pages": terminal_count,
            "identical_cross_page_duplicates": identical_dupes}
