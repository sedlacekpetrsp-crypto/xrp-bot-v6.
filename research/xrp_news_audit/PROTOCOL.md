# A6 krok 0 — DATOVÝ AUDIT zpráv o XRP (ne strategie)

Předregistrováno 2026-11-09 ~19:30 UTC (autopilot běh #43) PŘED stažením jakýchkoli dat. Výhradně PAPER výzkum.
Podnět vlastníka 2026-11-09 19:54 SEČ („nemůžete hlídat zprávy které jsou aktuální?“), fronta A6 ve STATE.md.

## Otázka
Existuje veřejný, zdarma dostupný historický zdroj titulků o XRP s časem, který byl prokazatelně známý v daném okamžiku
(point-in-time, PIT), v dostatečném počtu pro poctivý test „výnos XRP 15 min–4 h po titulku“ (A6-S) nebo
„zprávy jako risk filtr“ (A6-F)? Audit **nestahuje ceny a nepočítá žádné výnosy** ⇒ N v registru +0.

## Zdroje
- **Z1 GDELT 2.0 GKG** (data.gdeltproject.org, zdarma, 15min soubory od 2015). Čas = `DATE` = okamžik zpracování
  GDELTem (nezávislý crawler ⇒ PIT, pokud soubor vyšel včas). Titulek z pole Extras `<PAGE_TITLE>`.
  Vzorek (pevně): 2020-01 … 2026-10, každý měsíc dny 5, 15, 25 v 14:00 UTC (při chybějícím souboru +15 min, max 4 pokusy).
  Měří se: podíl záznamů s PAGE_TITLE; počet titulků s XRP (regex z produkce `news_signal.ASSETS["XRP"]`),
  z toho jen-XRP; skóre produkčním `_headline_score` (kopie, beze změny); domény; odhad ročního počtu =
  průměr na soubor × 35 040.
- **Z2 sitemapy vydavatelů** (cointelegraph.com, coindesk.com, decrypt.co — stejné zdroje jako NEWS bot):
  robots.txt → sitemap index → URL s `xrp|ripple` ve slugu/titulku; pole `news:publication_date`, `lastmod`,
  `news:title`; počty podle roku; přesnost času (sekundy/minuty vs. jen datum). Strop 4 000 sitemap/zdroj, 0,2 s mezi dotazy.
- **Z3 zpoždění GDELT**: URL nalezené v Z1 i Z2 ⇒ `DATE(GDELT) − publication_date`; medián a p90.
- RSS archivy nemají historii (jen posledních ~25–100 položek) ⇒ pro backtest nevhodné; jen konstatovat.
- Žádné archivy typu Wayback, žádné placené API (CryptoPanic Pro apod.).

## Brány (předem, nelze měnit po datech)
- **G1 počet**: odhad titulků jen-XRP se skóre |s| ≥ 2 (produkční práh) ≥ 300 v 2020–2024 a ≥ 100 v 2025–26
  alespoň v jednom zdroji (Z1 odhadem, Z2 přesným počtem).
- **G2 PIT čas**: zdroj má čas na minuty a buď je nezávislý crawler (Z1), nebo publisher pub_date ověřený Z3
  s mediánem |zpoždění| ≤ 60 min a p90 ≤ 6 h. Jen `lastmod` nebo jen datum ⇒ G2 nesplněno.
- **G3 kontinuita**: v žádném roce 2020–2026 nechybí > 25 % vzorkových souborů (Z1), resp. žádný kalendářní
  kvartál bez XRP článku (Z2).
- **Verdikt**: GO pro protokol A6-S/A6-F jen při G1 ∧ G2 ∧ G3 u téhož zdroje; jinak DATA NO-GO (A6 zůstane
  jen forward sběrem — produkční NEWS bot už titulky vidí; návrh ukládání titulků jen se souhlasem vlastníka).
- Omezení předem: titulky mohou být dodatečně upravené (Z2), GDELT pokrytí krypto médií je neúplné; odhad Z1
  z 246 souborů má velký rozptyl (uvést 95% interval Poisson).

## Vedlejší úkol: proč NEWS bot nemá obchody
Čtení kódu `news_paper.py` + `news_signal.py` na `v8-fly-layer-test` a stavu v DB (jen SELECT). Bez změn produkce.

## Výstupy
`gdelt_files.csv`, `gdelt_xrp_titles.csv`, `sitemap_summary.csv`, `sitemap_xrp_urls.csv.gz`, `lag.csv`, `audit.json`,
`AUDIT.md` (verdikt), nezávislý přepočet souhrnů `verify.py` z CSV.
