# K7 — prémie za plánovaná makro oznámení (FOMC/CPI) — KROK 0: datový audit

Stav: NAVRŽENO (autopilot běh #50, 2026-11-11 03:15 UTC). Commitnuto PŘED stažením jakýchkoli dat.
Spuštění kroku 0 až po souhlasu ChatGPT v dialogu (HUNT-08, zpráva 0278). Výhradně PAPER, žádné výnosy v kroku 0.

## Hypotéza (jen pro kontext, v kroku 0 se NEMĚŘÍ)
Announcement risk premium (Savor–Wilson 2013) a pre-FOMC drift (Lucca–Moench 2015): investoři požadují prémii
za držení rizika přes plánované makro oznámení. Pokud se po roce 2020 BTC chová jako rizikové aktivum navázané na
makro likviditu, mohla by se prémie projevit v BTC/ETH v okně před / během oznámení. Termíny jsou známé dopředu
⇒ signál je z definice PIT (kalendář, ne cena). Projekt makro kalendář nikdy nepoužil (grep FOMC/CPI/macro/
announce v registru, inventáři 20261105 a všech větvích = 0; nejbližší: `broad_dollar_downtrend` #41,
`session_transfer`, `weekend_carry` — časové/makro rodiny, jiný mechanismus).

## Krok 0 — co se audituje
1. Kalendář událostí z oficiálních zdrojů staženchý přes GitHub Actions se SHA-256 každé stažené stránky:
   - FOMC: federalreserve.gov (fomccalendars.htm + fomchistorical<rok>.htm), 2018–2026;
   - CPI: bls.gov plán vydání CPI (schedule/<rok>/home.htm nebo cpi.htm archiv), 2018–2026.
2. Pro každou událost: datum, čas oznámení (FOMC 14:00 ET, CPI 08:30 ET → UTC s DST), příznak
   `scheduled` (v kalendáři zveřejněném před rokem události / ≥ 7 dní předem). Neplánované schůze
   (např. 2020-03-03, 2020-03-15) a přesunutá vydání (shutdown 2025) = vyloučit, reportovat zvlášť.
3. Pokrytí cen: Binance Vision spot BTCUSDT a ETHUSDT 1h klines (CHECKSUM) v okně ±48 h kolem každé
   události; událost se počítá jen při 100 % hodinových svíček v okně.

## Brána GO (jen pro návrh výkonnostního protokolu)
- ≥ 60 plánovaných FOMC událostí s plným pokrytím (BTC), nebo ≥ 150 FOMC+CPI dohromady;
- chronologické dělení ladění/validace/závěrečný test 50/25/25 % událostí ⇒ závěrečný ≥ 15 FOMC;
- 0 chyb SHA-256 / CHECKSUM; každá událost má doložený zdroj (URL + hash stránky).
Nesplněno ⇒ DATA NO-GO, K7 uzavřít bez výkonu. Žádná imputace, žádný zpětný výběr událostí.

## Výkonnostní krok (až po GO a nové oponentuře — zde jen NÁVRH)
Max. 4 varianty: okno {−24 h → oznámení, −2 h → +2 h} × událost {FOMC, FOMC+CPI}; long BTC perp, jinak hotovost;
náklady ×1/×2/×3 + funding; benchmarky: B&H, náhodná okna stejné délky a stejného dne v týdnu (placebo),
hotovost; DSR s N z registru + 4. Závěrečný test smí jen zamítnout; povýšení jen forward PAPER ≥ 60–90 d.
