# Metodický lessons ledger (PAPER výzkum)

Dohoda dialogu 0215/0217 (AI-AGENTS-01): jen **nové chyby nebo pasti s odkazem na důkaz**, bez duplikace
`reports/hypothesis-inventory-20261105.md` a `automation/STRATEGY_REGISTRY.md` (tam jsou verdikty hypotéz).
Role: navrhovatel ≠ auditor. Auditor dostává zmrazený protokol, lineage dat, fee/fill/funding a výstupy testů,
ale **nesmí měnit prahy ani finální OOS**. Řádek = past · jak se projevila · pravidlo · důkaz.

| # | Past | Pravidlo | Důkaz |
|---|---|---|---|
| L1 | Přisuzovat selhání nákladům | Před optimalizací exekuce změřit hrubou hranu vs náklad; 0/18 R-hypotéz bylo nákladově limitovaných ⇒ chybí hrana | PR #36 (`96397b5`, `ad9ffcb`) |
| L2 | Pořadí/žebříček bez placeba | Každý průřezový výběr top-k testovat proti bottom-k placebu; R5 bottom 3 ≈ top 3 | PR #28, `research/near_high/RESULTS.md` |
| L3 | Zlepšení Sharpe/DD jen v jednom režimu | Vol-cílení hodnotit zvlášť v býčím a medvědím úseku; v 2022 a 2025–26 kopíruje B&H | PR #27, `research/vol_target/RESULTS.md` |
| L4 | Archivní 1d klines po delistingu | Binance Vision pokračuje nulovými svíčkami (156 symbolů) ⇒ obchodní den = objem > 0 | PR #38 (`1bba792`) |
| L5 | Jednotky času v trades | Binance spot trades přešly v 2025 na mikrosekundy ⇒ normalizovat podle délky timestampu | `research/top_risk_radar_v1/binance_spot_trades.py` ř. 11–15 (`91718d1`) |
| L6 | Explorativní pohled kontaminuje holdout | Období použité v explorativní analýze označit „viděné“; finální holdout jen nedotčené období | dialog 0220 bod 2 (`EXPLORATORY_RESULTS_2024.md`) |
| L7 | Maskovaný exit kód v CI | `set -o pipefail` u příkazů s `| tee`; jinak padající testy projdou zeleně | `28caf8a` (claude/ci-pipefail-20261108) |
| L8 | Test závislý na hodinách | Zmrazit čas + negativní kontrola; ne posouvat timestampy | `e5577df`, CI 42486100926 |
| L9 | Překryvné eventy jako nezávislá pozorování | Listingy/obchody s překryvem hodnotit portfoliovou equity a blokovým bootstrapem, ne průměrem obchodů | dialog 0211 bod 1, dodatek E4 `d538e29` |
| L10 | OI pokles = likvidace | Bez historických forced-liquidation dat jde jen o proxy deleveragingu | dialog 0211 bod 3 |
