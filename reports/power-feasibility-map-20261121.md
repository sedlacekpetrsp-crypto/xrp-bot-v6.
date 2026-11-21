# POWER-PREFLIGHT-01 — mapa proveditelnosti (Claude, 2026-11-21, dialog 0432)

Čistá aritmetika modulu `research/episode_power_preflight.py` @ `65e4d6c` (ChatGPT, review kolo 2 `a7a44ec`).
**Žádná tržní data, žádný backtest, N +0.** σ epizody jsou ilustrativní PŘEDPOKLADY (řádové hodnoty pro BTC/ETH/XRP),
ne měření; každý kandidát musí σ a DEFF předregistrovat sám.

Brána (Q11b): hrubá hrana ≥ 3× náklad ⇒ čistá hrana 2× náklad; N_eff* = ((z_α/2m + z_0,8)·σ / (2·náklad))².

| Náklad (roundtrip) | c | Horizont | σ (předpoklad) | m | Hrubá hrana ≥ 3c | N_eff* | Potřebná čistá hrana / σ |
|---|---|---|---|---|---|---|---|
| perp taker (model K9) | 0,115 % | 15 min | 0,3 % | 1 / 10 | 0,345 % | 14 / 23 | 0,77 |
| perp taker | 0,115 % | 1 h | 0,7 % | 1 / 10 | 0,345 % | 73 / 124 | 0,33 |
| perp taker | 0,115 % | 4 h | 1,5 % | 1 / 10 | 0,345 % | 334 / 567 | 0,15 |
| perp taker | 0,115 % | 1 d | 4,0 % | 1 / 10 | 0,345 % | 2 374 / 4 027 | 0,058 |
| spot taker (příklad 0429) | 0,230 % | 15 min | 0,3 % | 1 / 10 | 0,690 % | 4 / 6 | 1,53 |
| spot taker | 0,230 % | 1 h | 0,7 % | 1 / 10 | 0,690 % | 19 / 31 | 0,66 |
| spot taker | 0,230 % | 4 h | 1,5 % | 1 / 10 | 0,690 % | 84 / 142 | 0,31 |
| spot taker | 0,230 % | 1 d | 4,0 % | 1 / 10 | 0,690 % | 594 / 1 007 | 0,115 |

## Závěr (návrh k oponentuře)
1. Na krátkých horizontech je vazebná podmínka **ekonomická** (hrana ≥ 0,33–1,5 σ na obchod), ne statistická — malé N_eff*
   je zde zavádějící. K9 (kulatá čísla) změřil reálný mikrostrukturní efekt (+11–18 % objemu), ale hrubý výnos ≈ 0
   vs. předbrána 0,42 %: přesně tento režim.
2. Na denním horizontu je potřebná hrana/σ ≈ 0,06–0,12 (realistické pro faktory), ale N_eff* ≈ 600–4 000 ⇒ dosažitelné jen
   **průřezově** (mnoho symbolů × dní) a pouze při nízkém DEFF (korelace kryptoaktiv je vysoká ⇒ DEFF průřezu velké).
3. Kalendářní/oznamovací události s desítkami výskytů (K7, K8, K13, K14, A5) jsou předem podsílené na jakémkoli horizontu ≥ 4 h.
4. Prakticky proveditelná oblast: horizont 4 h–1 d, ≥ 300–600 nezávislých epizod po shlukování, a mechanismus s doloženou
   velikostí ≥ 3× náklad v literatuře nebo datech projektu (RESEARCH_FRAMEWORK §filtr). Rodiny průřezové rotace,
   relativní síly, residual snapback a funding jsou v inventáři zamítnuté ⇒ nový kandidát musí mít jiný zdroj informace.
