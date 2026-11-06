# Návrhy hypotéz a oponentury (vstup od externího asistenta / vlastníka)

Autopilot tento soubor čte při každém běhu. Nové položky přidávejte **na konec**, každou jako samostatnou
sekci podle šablony níže. Autopilot u každé doplní řádek „Stav:“ (zařazeno do fronty / zamítnuto, proč /
už testováno jako …) a nikdy položky nemaže.

Pravidla: výhradně PAPER výzkum; návrh je jen podnět — o zařazení rozhoduje rámec
`automation/RESEARCH_FRAMEWORK.md` (protokol předem, náklady ×1/×2/×3, chronologické dělení, Deflated Sharpe).

## Šablona — hypotéza
```
## H-<YYYYMMDD>-<n>: <krátký název>
- Zdroj výhody (proč by to mělo fungovat a proč to ještě není arbitrované):
- Pravidla (vstup / výstup / velikost pozice, bez volitelných detailů):
- Parametry a max. mřížka (nejvýš 4 varianty):
- Aktiva a časový rámec:
- Data (musí být veřejná a zdarma, ideálně Binance Vision):
- Čím se liší od už testovaných (viz STRATEGY_REGISTRY.md):
- Očekávaný počet obchodů za rok:
- Hlavní riziko / proč to může selhat:
- Odkaz na literaturu nebo zdroj (pokud existuje):
```

## Šablona — oponentura
```
## R-<YYYYMMDD>-<n>: oponentura <PR #N / soubor>
- Co jsem zkontroloval:
- Podezření na chybu (konkrétní řádek / číslo / soubor):
- Jak to ověřit (konkrétní test nebo výpočet):
- Závažnost: vysoká / střední / nízká
```

---
