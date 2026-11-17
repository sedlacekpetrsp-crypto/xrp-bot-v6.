# R10b — výsledek úplného ledgeru pokusů N (2026-11-17, autopilot běh #73)

Protokol: `PROTOCOL.md` (commit `5718214` před výpočtem; dodatek 1 po 1. výpočtu, jen zvyšuje N). Skript
`tools/research/trial_ledger.py`, výstup `results.json`, 4 syntetické testy `tests/test_trial_ledger.py` (4 passed).
Snapshot produkce `prod_trade_tables_20261117.json` (SHA-256 prefix `1dc5b1d2b8bc1625`, read-only SQL, jen počty).

| Část | Dolní mez | Horní mez | Obsah |
|---|---|---|---|
| A R10 (PR #34) | 190 | 209 | 110 inventář + R-série #11–#32; horní = 194 + 15 nedoložených |
| B nové backtesty po R10 | 29 | 29 | R12 #33 (4), R13 #35 (4), A1 #39 (4), A4 #40 (8, dodatek 1), A2 #41 (4), A5 #43 (1), 4 hypotézy 11-05 mimo inventář (1 každá) |
| C předregistrace bez výnosu | 3 | 19 | K9 A+B (3); jen horní: R8 #29 (4), R9 #30 (4), A5 (4), K7 (4) |
| D produkční / forward PAPER | 16 | 49 | 16 tabulek s obchody mimo inventář; horní = 46 dvojic tabulka×setup + 3 tabulky s 0 obchody |
| **Celkem** | **238** | **306** | |

Nezávislý přepočet ručně: 190+29+3+16 = 238; 209+29+19+49 = 306 (shoda se skriptem).

## Závěr pro K9 (dodatek 2 opr. 2 bod 1)
Doložené N (i horní mez 306) **< 450** ⇒ brána e) DSR zůstává při **N = 450**, V[SR] = 0,5. Předregistrace K9 se nemění.
Registrová průběžná hodnota 225 byla podhodnocená (chyběly produkční boty a 4 hypotézy z 2026-11-05), ale 2× rezerva ji pokrývá.

## Omezení
- Produkční boty: verze ladění, které nezanechaly tabulku (FLY parametry, TV 9 variant mimo DB), nejsou doložitelné ⇒ 306 není
  absolutní horní mez; při rezervě 144 pokusů by změna DSR prahu byla řádu setin Sharpe (R10: DSR na N málo citlivé).
- Mapování D na inventář (TV, BEST-OF, candle) je úsudek zapsaný předem; horní mez mapování nepoužívá.
- Dvojí započtení `spot_listing_drift` a `xrp_bank_credit_expansion` ponecháno (konzervativní).
- Žádná data z burzy, žádný výnos, žádný zápis do produkce.
