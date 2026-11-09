# HUNT-04 — PIT provenance OI (odpověď na dialog 0242, 2026-11-09)

Jen datová brána. Žádné ceny, žádná výkonnost, žádný backtest. Kód brány: `pit_gate.py` (FAIL CLOSED), testy
`tests/test_oi_pit_gate.py`. Podklady: `AUDIT.md`, `publication_delay.csv` (běh 42582439134, `1928ac2`).

| Zdroj / typ OI | event_time | captured_at | first_available_at — důkaz | Revize | PIT verdikt |
|---|---|---|---|---|---|
| Vision `metrics` denní ZIP: `sum_open_interest`, `sum_open_interest_value` (5 min) | `create_time` | — (naše stažení 2026-11, roky po události) | jen S3 `LastModified`; přepisy: medián 299–16 503 h, ≤ 1 h = 0 % | neověřitelné (přepis mohl měnit hodnoty; `.CHECKSUM` je jen z doby přepisu) | **FAIL CLOSED** |
| Vision `metrics`: poměry top-trader / taker L/S | `create_time` | — | totéž | neověřitelné | **FAIL CLOSED** |
| Vision `metrics` s pravidlem „D−1 použitelné v D“ | konec D−1 | — | konvence bez provenance (0242 bod 2) | neověřitelné | **FAIL CLOSED** |
| REST `/futures/data/openInterestHist` (historie ~30 dní) | `timestamp` | jen pokud sami zachytíme | jen od okamžiku vlastního sběru | jen srovnáním opakovaných snapshotů | historie: **FAIL CLOSED**; forward: nedostupné z Actions (PR #38: fapi z US runnerů blokováno) |
| REST `/fapi/v1/openInterest` (okamžitý) | `time` | jen vlastní sběr | jen forward | — | stejné jako výše — nový datový projekt |

Přijatelný důkaz (`ACCEPTED_EVIDENCE`): pouze vlastní neměnný snapshot s `captured_at`, SHA-256, časem odpovědi API,
offsetem hodin ≤ 5 s a kontrolou revizí. Takový důkaz z historie neexistuje.

## Rozhodnutí
**DATA NO-GO** pro jakýkoli historický test A3 (1h i denní A3-D) na archivu Vision. A3-D se tím uzavírá jako
neověřitelná na tomto datasetu. Forward sběr OI = samostatný nový datový projekt (vyžaduje runner mimo US bez Renderu
a bez placených služeb — momentálně není k dispozici ⇒ nenavrhuje se).

Omezení: 77/79 je výběr podle pokrytí v rámci zmrazeného univerza listovaného do 2020-12-31, ne nezávislý historický
vzorek; delistingy zachyceny (G3), přežití do 2020-12-31 ale je selekce.
