# CLAUDE.md — rozcestník (NÁVRH, bez normativní autority)

Tento soubor NEOBSAHUJE vlastní pravidla, jen odkazy. Dohoda dialogu QUICKSTART-01 (0216 ↔ 0217) a ZADANI-01 (0236 ↔ 0239).
Při rozporu platí zdroj výš v pořadí níže; při rozporu s aktuálním výslovným pokynem vlastníka nebo s omezením
automatizace ZASTAVIT a vyžádat rozhodnutí vlastníka, ne tiše vybrat starší soubor.

## Pořadí zdrojů
1. Aktuální výslovný pokyn vlastníka a `dialog/OWNER_DECISIONS.md` (větev `dialog/claude-chatgpt`; agenti NEUPRAVUJÍ).
2. `automation/RESEARCH_FRAMEWORK.md` — validace, nic není ziskové bez ní.
3. `automation/STATE.md` — fronta hypotéz, poslední stav, „KDE POKRAČOVAT“.
4. `automation/STRATEGY_REGISTRY.md` + `reports/hypothesis-inventory-20261105.md` — před každou novou hypotézou (duplicity).
5. `dialog/README.md` — formát a pravidla dialogu Claude ↔ ChatGPT.
6. `automation/RUNBOOK.md` — provozní postupy.

## Mantinely (odkazem, plné znění ve zdrojích výše)
- Výhradně PAPER. Žádný LIVE, Render, deploy, merge, push do `main` / `v8-fly-layer-test`, force push.
- Výkonnostní test jen podle předem commitnutého protokolu v izolované větvi `research/*` / `claude/*`.
- Tajné údaje nikdy do repozitáře.

## Testy
- `pip install -r requirements-dev.txt`
- `python -m pytest -q -p no:cacheprovider` (CI: `.github/workflows/autopilot-checks.yml`, větev `research/autopilot`)
- Binance Vision data stahovat přes GitHub Actions (relace na data.binance.vision nedosáhne).

## Šablona zadání (ZADANI-01; pro nové vývojové požadavky, ne pro krátké odpovědi na audit)
CÍL: jedna věc · KONTEXT: soubory/větve/commity · OMEZENÍ: co se nesmí ·
HOTOVO KDYŽ: měřitelné kritérium; odlišit mechanické testy od ekonomické validace, uvést stav důkazu;
výkonnostní kritérium samo NEAUTORIZUJE backtest (vždy OWNER_DECISIONS + datové brány) · VÝSTUP: co a kam.
