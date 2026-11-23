# A1 krok 1 — PIT inventura USDT-M perpů: výsledek (bez výkonnosti)

Protokol `afb7812` (před daty) + dodatek 1 `7ee7130` (definice obchodního dne). Data: Binance Vision, 24 067 archivů 1d/1m,
všechny SHA-256 shodné s `.CHECKSUM` (`data_source.json`). Run [42497005254](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/42497005254), výsledek `1bba792`.
Žádné ceny ani výnosy; N v registru +0. Výhradně PAPER výzkum.

## Souhrn
- Archiv: 1 080 symbolů UM, z toho **923 USDT perpetual** (čtvrtletní `_YYMMDD`, USDC/BUSD vyřazeny).
- Stav k 2026-10-31 (podle posledního dne s objemem): **756 aktivních, 167 delistovaných/zastavených**.
- **156 symbolů má po delistingu „mrtvé“ svíčky s nulovým objemem** (např. FTTUSDT 1 446 dní, RAYUSDT 1 445, OMGUSDT 637) —
  archiv 1d klines tedy NEoznačuje konec obchodování. Každý budoucí test na širokém koši musí brát obchodní den = objem > 0.
- Recyklované tickery (mezera > 30 dní, 2+ úseky): 10 (CVC, CTK, LIT, ICP, TLM, CVX, MDT, SLP, MAVIA, AIA) — vyřazeny.
- Neúplný funding: 3 (QTUM, BNX, JUP); > 2 chybějící dny v prvních 180 dnech: 5.

## Brány proveditelnosti (protokol)
| Brána | Hodnota | Výsledek |
|---|---|---|
| G1 způsobilých listingů 2020-01…2026-04 ≥ 100 | 682 | ✔ |
| G2 z toho delistovaných ≥ 10 | 166 | ✔ |
| G3 každý rok 2021–2025 ≥ 10 | 54 / 22 / 97 / 129 / 240 | ✔ |
| G4 shoda s exchangeInfo onboardDate | exchangeInfo HTTP 451 z GitHub runneru | neověřeno (poznámka) |
| G5 checksumy | 24 067 ok, 0 neshod | ✔ |
| **GO** | | **ANO** — lze psát protokol backtestu A1 |

Způsobilé podle roku listingu: 2020 78, 2021 54, 2022 22, 2023 97, 2024 129, 2025 240, 2026 (do 04) 62.
Delistované mezi způsobilými: 2020 23, 2021 24, 2022 8, 2023 32, 2024 37, 2025 42.

## 1. běh vs dodatek 1
1. běh (`1984db2`, poslední den = poslední svíčka): 31 delistingů, 558 způsobilých, 138 „funding_incomplete“ — chybně
(mrtvé svíčky po delistingu). Dodatek 1 (objem > 0): 167 delistingů, 682 způsobilých, 3 funding_incomplete.

## Omezení
- first_trade_utc = první 1m svíčka s objemem; bez nezávislé kontroly (G4). Listing v 1. den může začít kdykoli během dne ⇒
  protokol A1 musí vstupovat nejdřív za open dne first_day + 30.
- Delisting z archivu = poslední den s objemem; nevíme oznámení delistingu (obvykle ~1 týden předem) — v A1 modelovat
  nucené uzavření short pozice za poslední close s objemem, bez možnosti dřívějšího výstupu.
- Výpůjčka/margin limity a likvidační bariéra nejsou v archivu ⇒ A1 musí mít konzervativní páku a likvidační pravidlo.
