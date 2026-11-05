# Předávací dokument pro další vývojáře / asistenty (např. ChatGPT)

Účel: sjednotit práci na PAPER botech v `sedlacekpetrsp-crypto/xrp-bot-v6.` tak, aby se
neopakovaly stejné testy a výsledky byly srovnatelné. Platí jen PAPER, žádný LIVE.

## Současný stav (2026-11-05)

Podrobnosti a čísla: `reports/strategy-review-20261105.md` (úrovně důkazu A/B/C).

- V prohledaných výsledcích není žádná strategie s průkazným kladným výsledkem po nákladech
  na datech nepoužitých při ladění. Ve větvi `autocorr-regime-research-20261024` má 35 z 36
  validací rozhodnutí NEPROŠEL.
- ELITE V18/V56 a Combined běží (podle kódu) jako experimentální PAPER, nikoli validované.
  Zisk V18 tvoří z 111 % jen 3 obchody; Combined výběr nebyl nikdy backtestován.
- Opraveno a sloučeno (PR #5, `da2f665`): účetnictví Combined PAPER (nerealizovaný P/L,
  časování rebalance), zastaralé TV testy. Celá sada testů: 231 prošlo / 6 selhalo.
- Stav produkce na Renderu není ověřen (viz oddíl C reportu).

## Co prosíme poslat / doplnit (do repozitáře, ne do chatu)

1. **Seznam všech testovaných hypotéz** včetně neúspěšných a nedokončených, s datem
   a větví — potřebné pro posouzení vícenásobného testování.
2. **Surová data nebo přesné zdroje** s SHA-256 (ideálně `manifest.json`), aby šly
   výsledky zreprodukovat. Nikdy ne API klíče ani hesla.
3. **Ledgery obchodů** (`trades.json.gz`) u každého výsledku, nejen souhrnná čísla.
4. **Skutečná konfigurace Renderu:** start command služby (`app_v8_ui` vs. `app_v8_fly`),
   které služby existují a kterou větev nasazují. Bez tajných hodnot.
5. **Výstupy PAPER účtů z produkce:** `/combined/status`, `/elite-paper/status`,
   `/swing/status`, `/news-paper/status` s časem stažení.

## Společná pravidla, aby výsledek byl důvěryhodný

- Protokol, parametry a brány zapsat a commitnout **před** prvním výsledkem.
- Náklady: fee 0,095–0,10 % + skluz/spread na každou stranu; stres 2× a 3×; u futures funding.
- Chronologicky oddělit vývoj / kontrolu / **nikdy nepoužitá data**; vybírat jen podle vývoje.
- Uvádět vždy: počet obchodů, čisté P/L, max. propad, PF, výsledek bez 3 nejlepších obchodů,
  výsledky po letech/režimech.
- Méně hypotéz, ale každou důkladněji: při desítkách testů se náhodně „ziskový“ výsledek
  objeví i bez skutečné výhody. Úspěch na historii nestačí — nutných je ≥ 30 nových PAPER
  obchodů za nezměněných pravidel.
- Pracovat ve vlastních větvích; do `v8-fly-layer-test` (spouští deploy) jen přes PR se
  souhlasem vlastníka.

## Nejbližší konkrétní krok

Spustit připravený backtest `research/combined_selection_replay/` (README obsahuje přesné
příkazy). Potřebuje jen veřejný přístup na `data.binance.vision`. Kdo má síťový přístup,
může ho spustit a commitnout `results.json` beze změny protokolu.
