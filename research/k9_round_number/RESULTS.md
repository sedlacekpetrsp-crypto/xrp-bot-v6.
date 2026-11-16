# K9 ROUND_NUMBER — výsledky kroku 0 a fáze A (mikrostruktura, BEZ výnosu)

Protokol: `PROTOCOL.md` (`a14b596`, zmrazeno před daty) + dodatek 1 (`2b234c4`, před daty, oponentura ChatGPT 0353).
Výhradně výzkum; žádný obchod, žádný výnos, žádné náklady se nepočítaly. **Toto NENÍ důkaz ziskovosti.**

## Krok 0 — datový audit (run [43935532445](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/43935532445), commit `68d9bd7`)
- Binance Vision UM `klines/1m`, BTCUSDT/ETHUSDT/XRPUSDT, 2020-01..2026-10 = 246 měsíců; SHA-256 vs CHECKSUM ověřen
  před parsováním u všech staženích (0 CHECKSUM_FAIL, 0 MISSING, 0 PARSE_FAIL).
- **DATA GO: 243/246 (98,8 %)**. Vyloučeno (LOW_COVERAGE < 99 % minut, nic se neimputuje): XRPUSDT 2020-01 (82,7 %,
  listing v průběhu měsíce), 2022-02 (89,3 %), 2022-04 (93,3 %).
- Manifest se SHA-256 každého ZIP: `step0_manifest.json`; nezávislá kontrola manifestu (Claude, Python -I): 0 nekonzistencí,
  0 duplicitních SHA, 0 řádků mimo měsíc.

## Fáze A (run [43936758796](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/43936758796), commit `0e06623`)
Runner `phase_a_run.py` (`c029c41`) znovu stáhl jen OK měsíce a vyžadoval SHA-256 shodné s manifestem kroku 0.
Blokový bootstrap přes kalendářní dny, 10 000 replik, seed 20261116; `invalid_frac` = 0 ve všech čtyřech případech.

| Období | Metrika | D | 95% CI | n kulaté / placebo |
|---|---|---|---|---|
| vývoj 2020-01..2023-12 | D1 log-objem | **+0,110** | [+0,090; +0,130] | 10 349 / 21 444 |
| vývoj | D2 směrový taker podíl | **+0,0175** | [+0,0152; +0,0198] | 10 349 / 21 440 |
| závěr 2024-01..2026-10 | D1 | **+0,180** | [+0,162; +0,197] | 12 754 / 25 339 |
| závěr | D2 (jen popis) | +0,0217 | [+0,0196; +0,0239] | 12 749 / 25 333 |

Po aktivech (D1 vývoj): BTC +0,118 [0,091; 0,145], ETH +0,101 [0,068; 0,134], XRP +0,106 [0,048; 0,165];
závěr: BTC +0,201, ETH +0,161, XRP +0,146 (všechny dolní meze > 0). Síla brány v rozhodující buňce (efekt 0,20, sd 1,0,
ρ 0,3) = 1,00; při efektu přesně na prahu 0,10 jen ~0,5 (tabulka `phaseA_power_table.csv`).

**Verdikt dle zmrazené brány: GO (jen pro sepsání dodatku fáze B).** Splněno: D1 vývoj ≥ 0,10 a dolní mez > 0, D2 > 0
s dolní mezí > 0, potvrzení v závěrečném úseku (D1 dolní mez > 0).

## Nezávislý přepočet (RESEARCH_FRAMEWORK bod 11)
Bodové D1/D2 obou období přepočteny z jednotlivých událostí `phaseA_events.csv.gz` (66 886 řádků) mimo runner:
shoda na 6 desetinných míst (0,109949 / 0,017511 / 0,179724 / 0,021744).

## Omezení a interpretace
- Bodový odhad D1 ve vývoji (0,110) je jen těsně nad prahem 0,10 a dolní mez CI (0,090) je pod ním; brána vyžaduje jen
  bod ≥ 0,10 a dolní mez > 0, takže GO je formálně platné, ale efekt ve vývoji je hraniční. Závěrečný úsek je silnější.
- Prokázána je jen **stopa mechanismu** (+11–20 % objemu a +1,7–2,2 p. b. taker podílu ve směru průrazu na kulaté
  vs. placebo úrovni). Taker objem je proxy stopů — nerozliší momentum tradery od spuštěných stop-příkazů.
- Ekonomická relevance je nejistá: fáze B potřebuje průměrný pohyb ≥ ~0,42 % (3× round-trip 0,14 %) — prior zůstává nízký.
- Expozice (`phaseA_exposure.csv`) je jen popisná; placebo se podle ní nepřelaďuje.

## Další krok
Fáze B (výnos po průrazu, náklady ×1/×2/×3, benchmark, DSR s N včetně K9) jen **samostatným předregistrovaným dodatkem**
→ oponentura ChatGPT → výslovné schválení vlastníka. Žádný výnos se do té doby nepočítá.
