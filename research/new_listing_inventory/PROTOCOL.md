# A1 krok 1 — PIT inventura listingů a delistingů USDT-M perpů (bez výkonnosti)

Stav: protokol commitnutý PŘED stažením dat (autopilot běh #36, 2026-11-08 ~15:20 UTC).
Kontext: vlastník uvolnil bod A (STATE.md, rozhodnutí 2026-11-08 13:38 SEČ). ChatGPT 0211 bod 1/4:
„A1 data feasibility → první bezpečný krok: PIT inventura všech historických listingů a delistingů + úplnost dat; bez backtestu.“
Výhradně PAPER, jen veřejná data Binance Vision, žádné klíče, žádný Render, žádné objednávky.

## Cíl
Zjistit, zda veřejný archiv umožní test A1 (NEW-LISTING DRIFT, short perpu 30–180 dní po listingu) **bez survivorship bias**:
kolik USDT-M perpetual kontraktů bylo kdy listováno, kolik delistováno, kdy přesně začaly obchodovat a zda mají
úplná denní data a funding. **Žádné výnosy, žádné P/L, žádné signály** — výstup neobsahuje ceny ani výnosy po listingu.
N v registru: +0 (není to test hypotézy).

## Data (pevně předem)
- Seznam symbolů: S3 listing bucketu `data.binance.vision`, prefix `data/futures/um/monthly/klines/` (všechny symboly,
  které kdy měly archiv, vč. delistovaných). Doplňkově prefix `data/futures/um/daily/klines/` (symboly jen s denními archivy).
- Vesmír: symboly končící `USDT` bez `_` (perpetual; čtvrtletní kontrakty `_YYMMDD` vyřazeny). USDC/BUSD vyřazeny.
- Na symbol: všechny měsíční archivy `1d` klines (2019-09 … 2026-10) + soubor `.CHECKSUM` (SHA-256 ověřen, neshoda = chyba);
  seznam měsíčních archivů `fundingRate` (jen výpis, bez stažení); denní archiv `1m` prvního obchodního dne (přesný čas
  první svíčky). SHA-256 všech stažených souborů do `data_source.json`.
- Nezávislá kontrola (best effort): veřejné `fapi.binance.com/fapi/v1/exchangeInfo` → `onboardDate`, `status`,
  `deliveryDate` u aktuálně známých symbolů. Nedostupnost (např. HTTP 451) se jen zapíše, není chybou.

## Definice
- first_trade_utc = open time první 1m svíčky prvního dne s 1d svíčkou (fallback: 00:00 prvního dne, příznak).
- last_day = poslední den s 1d svíčkou v archivu do 2026-10-31.
- status: `active` (last_day = 2026-10-31), jinak `delisted_or_halted` (pokud exchangeInfo potvrzuje SETTLING/CLOSE nebo
  symbol chybí v exchangeInfo ⇒ `delisted`; jinak `halted_unconfirmed`).
- missing_days = dny mezi first_day a last_day bez 1d svíčky; gap_segments = počet souvislých úseků oddělených mezerou > 30 dní
  (znovulistování / recyklace tickeru ⇒ příznak `reused_ticker`).
- funding_ok = funding archiv existuje pro každý měsíc s klines (od prvního měsíce) — jen výpis, bez obsahu.

## Brány proveditelnosti A1 (rozhodnuto předem; výsledek = GO / NO-GO pro psaní protokolu backtestu A1)
Způsobilý listing = first_day v 2020-01-01 … 2026-04-30, ≥ 180 dní po first_day v archivu NEBO delisting dříve
(delisting je součást výsledku, ne vyřazení), missing_days v prvních 180 dnech ≤ 2, funding_ok, ne `reused_ticker`.
- G1: způsobilých listingů ≥ 100.
- G2: mezi způsobilými aspoň 10 delistovaných (jinak nelze měřit survivorship).
- G3: ve všech kalendářních letech 2021–2025 aspoň 10 způsobilých listingů (rozložení v čase, ne jedna vlna).
- G4: shoda first_trade_utc s exchangeInfo `onboardDate` (± 24 h) u ≥ 90 % symbolů, kde je onboardDate k dispozici;
  bez exchangeInfo ⇒ G4 „neověřeno“ (není NO-GO, jen poznámka).
- G5: všechny stažené archivy prošly ověřením `.CHECKSUM`; chybějící checksum se počítá a hlásí.
GO = G1 ∧ G2 ∧ G3 ∧ G5. Při NO-GO se A1 neprovádí a důvod jde do registru.

## Výstupy (`research/new_listing_inventory/`)
`listings.csv` (1 řádek/symbol: symbol, first_trade_utc, first_trade_source, first_day, last_day, status, n_days,
missing_days, missing_days_first180, gap_segments, reused_ticker, kline_months, funding_months, funding_ok,
onboard_date_utc, exchangeinfo_status, eligible_a1, ineligible_reason), `inventory.json` (souhrn + brány),
`data_source.json` (URL, SHA-256, výsledek checksum), `INVENTORY.md` (lidsky čitelný souhrn). Žádné ceny ani výnosy.

## Co se NEDĚLÁ
Žádný výpočet výnosu, driftu, fundingu v USD ani signálu; žádné ladění. Parametry A1 (okno 30–180 dní, velikost pozice,
náklady ×1/×2/×3, chronologické dělení, srovnání s B&H, DSR s N) se zapíší až do samostatného protokolu A1 po GO,
commitnutého před stažením cen.
