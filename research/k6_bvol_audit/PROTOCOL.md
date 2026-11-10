# K6 krok 0 — datový audit Binance Vision BVOLIndex (PROTOKOL, commitnut PŘED daty)

PAPER, veřejná data, bez secrets, bez výnosů/výkonu. Dialog 0271 (návrh), 0276 (podmíněný souhlas ChatGPT jen pro datový audit).
Výstup auditu = GO / DATA NO-GO pouze pro *možnost navrhnout* výkonnostní protokol. Výkonnostní test se nespouští.

## Zdroj
- Výpis S3 `data.binance.vision`, prefix `data/option/daily/BVOLIndex/` (podsložky = tickery), ListObjects v1 s paginací.
- Každý `*.zip` + `*.zip.CHECKSUM` stažen z `https://data.binance.vision/<key>`; SHA-256 spočítán a porovnán s CHECKSUM.
- Pokus o `?versions` (historie revizí objektů) — výsledek reportovat (očekáváno AccessDenied ⇒ revize neověřitelné).
- Existence `data/option/daily/EOHSummary/` jen reportovat (počet souborů), nestahovat.

## Sémantika indexu (reportuje se, nehodnotí výkon)
- Hlavička CSV, názvy sloupců, ticker, base/quote; časový sloupec = `calc_time` (ms UTC, čas výpočtu indexu).
- Sanity hodnot: jen min/max/podíl hodnot mimo (0, 500) — žádné výnosy, žádné propojení s cenou.

## Očekávané intervaly (explicitně)
Kadence = modální rozdíl po sobě jdoucích `calc_time` přes celou řadu, zaokrouhlený na 1 s.
Povolené kadence: **1 s, 60 s, 300 s, 3600 s**. Jiná kadence ⇒ DATA NO-GO (neznámá sémantika).
Očekávaný počet bodů za den = 86400 / kadence. Řádky s `calc_time` mimo datum souboru = chyba (reportovat počet).
Duplicitní `calc_time` se počítají jednou.

## PIT (dostupnost v čase)
- Publikační čas = S3 `LastModified` objektu. Lag = LastModified − (datum souboru + 1 den).
- Den je **PIT doložený**, pokud lag ≤ 3 dny. Pozdější nahrání (backfill / revize) ⇒ den není PIT doložený.
- Samotné datum v názvu souboru se za důkaz nepovažuje.

## Brána GO (musí projít BTC i ETH ticker)
Nejdelší souvislý běh kalendářních dnů, jehož poslední den je nejvýš 7 dní před dnem auditu, kde každý den má soubor,
CHECKSUM shodu a je PIT doložený, a zároveň:
1. délka běhu ≥ **548 dní**;
2. body/očekávané přes celý běh ≥ **95 %**;
3. každý kalendářní kvartál v běhu ≥ **90 %**;
4. 0 řádků mimo datum souboru v běhu; kadence povolená.
Reportovat i: max. mezera v datech (s), počet dnů < 95 %, rozdělení lagů, počet souborů s nesouhlasem CHECKSUM.
Selhání kterékoli podmínky ⇒ **DATA NO-GO**, K6 uzavřít bez výkonu. Prahy se po zobrazení dat nemění.
