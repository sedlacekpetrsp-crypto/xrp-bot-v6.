# Errata k `reports/hypothesis-inventory-20261105.md` (snapshot `e9f3917`)

Původní soubor se NEMĚNÍ. Shoda Claude ↔ ChatGPT, dialog 0107/0108 (téma E). Výhradně PAPER; žádný běh.

| # | Položka | Oprava | Důkaz | Kategorie |
|---|---|---|---|---|
| 106 | `xrp_bank_credit_expansion` | NEZAMÍTNUTO → **NEPROŠEL** | `54ca03c:research/xrp_bank_credit_expansion_validation_20261105/README.md` ř. 3, 15, 17: 22 obchodů, PF 0,3348 / 0,2984 stress, net −260,26 USD; selhaly brány sample, net, PF, stabilita, final-year | NEPROŠEL dle zmrazených bran (ne jen nedostatek důkazů) |
| 20 | `elite/V5` | NEDOHLEDÁNO → **NEPROŠEL** | `2acc1ac:elite/RESEARCH_REPORT_20261013.md` ř. 69, 78, 87: development −184,84, validation 23 obchodů PF 0,176 net −630,94; „V5 and V6 fail validation and the predeclared minimum of 30 trades“. Holdout 25 obchodů +3 260,99 je podle reportu (ř. 96–97, 128) jen explorativní a neruší selhání development/validation | NEPROŠEL (záporný development i validation); navíc INSUFFICIENT_EVIDENCE dle min. 30 obchodů |
| 29 | `elite/V60` | **BLOCKED – archivace** | CI run `39103132749`, artefakt `12126944048`, expirace 2027-01-16; nerunovat, max. diagnostika | BLOCKED |
| 67 | `hourly_retest` `9eec861` | **BLOCKED – chybí manifest** 2025-10-18 → 2026-04-11 | `candle_validation_20261019/data_manifest.json` | BLOCKED |
| 76, 77, 79 | polymarket ×2, prospective evidence | **BLOCKED** (data/účet/produkční DB) | dialog 0107 | BLOCKED |
