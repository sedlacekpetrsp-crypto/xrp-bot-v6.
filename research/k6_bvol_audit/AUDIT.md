# K6 krok 0 — výsledek: **DATA NO-GO** (run 42907353584, commit c0101e5)

Protokol `PROTOCOL.md` (0b6491e, commitnut před daty). Prahy se nemění. Žádný výkon, žádné výnosy.

| | BTCBVOLUSDT | ETHBVOLUSDT |
|---|---|---|
| soubory / první / poslední | 1213 / 2023-06-20 / 2026-11-09 | 1213 / 2023-06-20 / 2026-11-09 |
| CHECKSUM nesoulad | 0 | 0 |
| kadence (modální Δ calc_time) | 1 s (povolená) | 1 s |
| PIT lag LastModified − konec dne: medián / max | 0,26 d / 2,36 d (0 dnů > 3 d) | 0,26 d / 2,36 d |
| řádky mimo datum / duplicity / hodnoty mimo (0,500) | 0 / 0 / 0 | 0 / 0 / 0 |
| čerstvý souvislý běh | 2026-01-05 → 2026-11-09 = **309 d** | 309 d |
| pokrytí běhu / min. kvartál | 99,80 % / 99,38 % | 99,76 % / 99,27 % |
| **brána ≥ 548 d** | **NE** | **NE** |

Chybějící denní soubory (obě řady shodně): 2023-09-25, 2023-10-24, 2024-06-11..12, 2024-06-30,
**2025-12-15..2026-01-04 (21 dní)**; max. mezera v datech ≈ 22,3 d. Nejdelší starší běh 2024-07-01..2025-12-14 = 532 d (< 548).
Revize objektů: S3 `?versions` = HTTP 403 AccessDenied ⇒ historii revizí nelze ověřit; LastModified ≤ 2,4 d u všech
2426 souborů nenaznačuje pozdější přepis. EOHSummary: 1090 souborů (jen existence).
Sémantika: hlavička `calc_time|symbol|base_asset|quote_asset|index_value`, index 27,6–88,98 (BTC), 29,8–102,1 (ETH).

Verdikt: podmínka 1 (≥ 548 souvislých PIT dnů) neprojde u obou ⇒ **DATA NO-GO, K6 uzavřít bez výkonu.**
Překlenutí 21denního výpadku by byla změna protokolu po zobrazení dat ⇒ nepřípustné.
