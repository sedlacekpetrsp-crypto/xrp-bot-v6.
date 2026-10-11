# BEST: řízené ověření změn, 10. 10. 2026

Rozhodnutí: **žádná testovaná varianta nesplnila podmínky pro přechod do kandidátního PAPER provozu. Produkční strategie se nemění.**

Referenční zdroj: `a0c05bc4161f12bc7d5b3d9869f86fb11c43bb55` na větvi `v8-fly-layer-test`. Výzkum je na samostatné větvi `research/best-validation-20261010`, kterou Render nepoužívá. Protokol je v `protocol.json`; varianty a hranice období byly zapsány před prvním výpočtem.

## Rozsah a interpretace

Jde o samostatný přehrávač původních strategií BEST (BREAKOUT a FIB), které způsobily analyzované ztráty. Používá přímo jejich produkční detekci, trendový filtr, otevření, uzavření a nákladové vzorce. Není to přesné přehrání celého provozu: nezahrnuje samostatnou EMA 4h, souběh s jinými boty ani pořadí asynchronních požadavků. Simulace používá 5minutové OHLC místo skutečné 3sekundové cesty ceny.

Data: 4 trhy XRP/BTC/ETH/SOL, 31 968 pětiminutových svíček na trh, 13. 6.–1. 10. 2026 včetně zahřívací historie. Kontrolovány mezery, duplicity, zarovnání času, platnost OHLCV a shodná časová osa všech trhů. Otisky zdrojových souborů jsou v `results/data_manifest.json` a shodují se s manifestem dřívějšího stažení.

- Vývojové období: 4. 7.–31. 8. 2026 (59 dnů).
- Chronologické ověření: 1. 9.–1. 10. 2026 (31 dnů).
- Tato data již byla použita v dřívějším výzkumu. Nejde o čistý neviděný holdout; poslední říjnové ztráty ovlivnily výběr hypotéz. Úspěch by vyžadoval další budoucí ověření. Výsledek není roční backtest.
- Každé období začíná znovu na 10 000 USDT; výsledky nelze sčítat jako jedinou souvislou equity křivku.
- Žádné další ladění parametrů ani kombinování filtrů po přečtení výsledků.

## Výsledek

| Varianta | Vývoj čistý P/L | Ověření čistý P/L | Obchody ověření | PF ověření | Max. pokles ověření | Ověření při 2× skluzu |
|---|---:|---:|---:|---:|---:|---:|
| Současná původní část BEST | −555,29 | −450,69 | 152 | 0,67 | 4,62 % | −562,61 |
| Navíc shoda trendu 1h | −122,56 | −309,89 | 89 | 0,63 | 3,55 % | −324,43 |
| Fibonacci SL za swingem | −515,24 | −329,55 | 141 | 0,73 | 3,63 % | −457,05 |
| Bez XRP breakout LONG | −527,61 | −508,50 | 116 | 0,54 | 5,20 % | −583,08 |

P/L v USDT po modelovaných poplatcích a skluzu. PF = součet zisků / absolutní součet ztrát. Hodinový filtr snižuje celkovou ztrátu hlavně omezením obchodů; jeho PF v ověření je dokonce nižší než u základu. Vyřazení XRP breakoutu neobstálo. Žádná varianta není prokázaně kvalitní náhrada.

Předem stanovená podmínka: kladný ověřovací P/L, nejméně 30 obchodů, PF alespoň 1,1, pokles účtu nehorší než základ a kladný P/L i při dvojnásobném skluzu. **0 ze 3 úprav prošly.** Proto zatím nevzniká další běžící bot a žádná placená služba.

## Náklady a provedení

Původní část BEST skutečně používá poplatek **0,05 % za stranu**, skluz **0,02 % za stranu**, riziko nejvýše **0,15 % účtu na obchod**, čisté RR 1,3 a ochranu break-even při +0,75R. Samostatná EMA 4h používá jiný poplatek (0,095 %); nesmí se zaměňovat.

Vstup na následujícím open po uzavřeném signálu. Používají se pouze hotové 15m/1h svíčky. U zásahu SL i TP ve stejné svíčce rozhoduje SL; při mezeře za SL plnění na open. BE se aktualizuje až podle close pro další svíčku, takže to není přesná reprodukce live exitů. Na konci okna jsou pozice uzavřeny a tento počet je uveden v JSON. Kapitál a sloty uvolněné až během svíčky nelze použít k jejímu dřívějšímu vstupu. Short financování je stejně jako v původním PAPER modelu vynecháno.

## Kontroly a další překážky

Výsledná sada: 18 úspěšných testů a 2 očekávaná selhání pro prokázanou chybu portfolio kontrol. Viz `known_issues.md`. Testy kontrolují náklady, mezery v datech, pohled do budoucna, riziko, duplicity, kapacitu, intrabar pořadí a obnovu smíšených EMA/legacy pozic pomocí databázové makety. Neprokazují odolnost skutečné databáze při pádu procesu mezi zápisy.

Zjištěno přímo ve zdroji: společná aplikace připojuje k BEST portfolio kontroly, ale původní `app_bestof_core.open_trade` je nevolá. EMA 4h je volá. To je samostatná technická překážka před jakoukoli propagací kandidáta; neprokazuje příčinu historických ztrát. Zachycené testy očekávaného selhání ji explicitně evidují, místo aby byla zaměněna za úspěšný test.

## Reprodukce

Python s requirements.txt. Veškeré spuštění je offline po získání dat; nepřipojuje databázi ani neposílá příkazy na burzu.

```bash
python research/best_validation/download_data.py --output /tmp/best-data
python -m unittest research.best_validation.test_replay test_bestof_ema4h test_bestof_ema4h_persistence -q
python research/best_validation/replay.py --data /tmp/best-data
```

Kompletní výstupy jsou v `results/results.json`, konfigurace v `runtime_parameters.json`, seznam obchodů v `trades.json.gz`. Opakovaný download musí projít kontrolou SHA256; při rozdílu se výsledky nesmějí vydávat za totožný dataset.

Další rozhodnutí: opravit prokázané technické nedostatky s regresními testy, ale obchodní strategii nepřepisovat na základě neúspěšných variant. Před novým pokusem zaznamenat novou konkrétní hypotézu a vyhradit dosud nepoužité či budoucí období.
