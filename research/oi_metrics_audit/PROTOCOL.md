# A3 OI DELEVERAGING PROXY — krok 0: datový audit Binance Vision `metrics` — předem registrovaný protokol (2026-11-09)

Fronta A (STATE.md, rozhodnutí 2026-11-08 13:38), dohoda HUNT-03 (dialog 0231 ↔ 0232 ↔ 0238, potvrzeno 0239).
Výhradně PAPER výzkum. **Jen datový audit: žádné ceny, výnosy, signály ani výkonnost.** Zapsáno a commitnuto před
kódem i před stažením jakýchkoli `metrics` dat. Po prvním spuštění se pravidla nemění (jen dodatky s datem a důvodem).

## Univerzum (zmrazené předem, PIT, bez výběru podle dat metrics)
- Zdroj: `listings_frozen.csv` = kopie `research/new_listing_inventory/listings.csv` z PR #38
  (commit `bb7f4b5`, SHA-256 `c3489dbbf00e2113a642d0aca2c24ed3830c2a9b22d5a6dfd16ee57f9f698c80`).
- Zahrnuto: **všech 81 symbolů s `first_day` ≤ 2020-12-31** (vč. 23 delistovaných/pozastavených). Kritérium je jen
  datum listingu (známé před obdobím auditu) ⇒ žádný výběr podle přežití ani podle kvality OI dat.
- Živé období aktiva: od `max(first_day, 2022-01-01)` do `min(last_bar_day − zero_volume_tail_days, 2026-10-31)`
  (mrtvé svíčky po delistingu se nepočítají; zjištění PR #38). Aktivum s prázdným živým obdobím = „mimo okno“
  (reportuje se, do jmenovatele brány se nepočítá — kritérium určeno předem z `listings_frozen.csv`).

## Data
- `https://data.binance.vision/data/futures/um/daily/metrics/<SYM>/<SYM>-metrics-YYYY-MM-DD.zip` (+ `.CHECKSUM`),
  každý stažený soubor ověřen SHA-256 proti `.CHECKSUM`; neshoda = soubor chybí (žádné opravy).
- Seznam souborů a `LastModified` přes veřejný S3 listing (`s3-ap-northeast-1…/data.binance.vision`).
- Stahuje GitHub Actions (`.github/workflows/oi-metrics-audit.yml`), žádné klíče, žádné secrets.

## Měření
- Bod = řádek s časem `create_time` zarovnaným na 5 min, v rámci dne souboru, `sum_open_interest` číselné a > 0.
  Duplicitní časy se počítají jednou; nezarovnané/mimo den/NaN/≤ 0 = neplatné (počet reportován).
- Očekávané body = 288 × počet dní živého období (v daném aktivu/kvartálu). Žádná imputace.
- Pokrytí aktiva = platné body / očekávané body. Pokrytí kvartálu = totéž v kalendářním kvartálu; hodnotí se jen
  kvartály s ≥ 30 živými dny aktiva (kratší se reportují).
- Výpadky: souvislé úseky ≥ 1 h bez platného bodu (počet, nejdelší, celkem hodin) na aktivum.
- Publikační zpoždění: `event_time` = konec dne souboru (00:00 UTC následujícího dne), `first_available_at` =
  S3 `LastModified` (horní mez — přepsaný soubor má pozdější čas ⇒ konzervativní). Zpoždění = rozdíl; medián,
  p90, p99, max podle roku. Soubor bez `LastModified` = dostupnost neznámá.

## Brána GO (jen pro návrh protokolu A3; NE pro výkonnost) — vše musí platit
1. ≥ 15 aktiv univerza (v okně) splní současně: pokrytí aktiva ≥ 95 % **a** každý hodnocený kvartál ≥ 90 %.
2. V každém kalendářním kvartálu 2022Q1–2026Q3 je aspoň 15 aktiv s pokrytím kvartálu ≥ 90 % (jinak by test A3 měl
   období s příliš úzkým košem).
3. Podíl delistovaných mezi aktivy splňujícími bod 1 se od podílu v celém univerzu (v okně) neliší o víc než
   15 procentních bodů (kontrola selekčního biasu, že data zůstávají hlavně u přeživších).
- Při splnění: **GO pouze pro návrh protokolu A3** s konzervativní dostupností: hodnota z denního souboru je
  použitelná až od `first_available_at` (prakticky D+1 nebo později) ⇒ v backtestu z Vision **žádné intradenní
  rozhodování na OI** (dohoda 0239: bez prokázaného `first_available_at` < 1 h nelze). 1h varianta A3 by
  vyžadovala vlastní forward sběr OI v reálném čase — jen jako budoucí návrh.
- Při nesplnění: **NO-GO ⇒ A3 uzavřít bez protokolu**, žádné ladění okna/univerza/prahů, vybrat novou hypotézu proti
  registru (filtr hrana ≥ 3× náklad).

## Výstupy
`audit.json` (souhrn, brána), `coverage_assets.csv`, `coverage_quarters.csv`, `publication_delay.csv`,
`data_source.json` (URL, SHA-256, LastModified), `summary.txt`, `AUDIT.md`. Nezávislý přepočet brány z CSV
(`verify.py`). Registr: řádek „A3 krok 0 – datový audit“ bez zvýšení N (není výkonnostní test).

## Omezení (předem)
- `LastModified` nemusí být první publikace (jen horní mez). Binance Vision nemá historii revizí hodnot.
- Shoda Vision vs. real-time API `openInterestHist` nejde ověřit z GitHub runnerů (Binance fapi z US IP blokováno).
- Pokles OI ≠ likvidace (zavírání pozic, přecenění notional) — týká se až návrhu A3, ne auditu.

## Dodatek 1 (2026-11-09 08:00 UTC, po pádu běhu 42577455591 — oprava parseru, pravidla beze změny)
- Běh spadl na souboru s nestandardním názvem (`…-metrics-…1993`), ne na pravidle. Den souboru se nově bere jen z
  názvu `-metrics-YYYY-MM-DD.zip`; jiné klíče se nepočítají jako data, jen se reportují (`nonstandard_keys`).
- Chyba stahování/zpracování jednoho aktiva = pokrytí 0 % a poznámka (konzervativně, aktivum se nevyřazuje).
- Brána, univerzum, okno ani prahy se nemění. Z prvního běhu je vidět jen pokrytí prvních 45 aktiv (vše ≥ 99,7 %),
  žádné ceny ani výkonnost.
