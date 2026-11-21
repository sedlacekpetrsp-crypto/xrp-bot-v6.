# G1 Top Risk Radar — ex-ante power preflight (RESEARCH_FRAMEWORK §6)

Stav: **[P] DOKUMENT / ARITMETIKA**. Žádná tržní data, žádné predikce, žádný výkon. Výhradně PAPER výzkum.
Autor: Claude, autopilot běh #96, 2026-11-21. Vlastník G1 implementace: ChatGPT (beze změny).

## Proč
Vlastník 2026-11-12 schválil **jediný** historický PAPER test G1 (OWNER_DECISIONS ř. 49). Freeze manifest od 2026-11-17
nevznikl (poslední commit radaru `a112130`). Od 2026-11-21 platí v §6 řádek „Chronologické OOS“ s povinnou power/ekonomickou
proveditelností (`c69fae6`). Než se jediný schválený běh spotřebuje, je třeba vědět, zda vůbec může dát rozhodnutí jiné než
INCONCLUSIVE. Tento dokument je vstup pro freeze manifest, ne jeho náhrada.

## Vstupy (známé před výkonem, nikoli výsledky predikcí)
- OOS 2022-01 .. 2026-10, 1 705 zralých rozhodnutí; **21 seskupených risk epizod** (−20 % / 336 h; census `0103335`,
  run 43229950012, dialog 0319). Jde o počet labelů, ne o výkon modelu.
- Kritéria z `PROTOCOL.md` (návrh, NEzmrazeno): precision ≥ 60 %, recall ≥ 50 % (epizodně), ≤ 2 falešné epizody/měsíc,
  Brier lepší než všechny baseliny (B0/B1/B2), blokový bootstrap ≥ 14 d.
- Po purge/embargu a neúplném foldu 2026 může být hodnotitelných epizod méně ⇒ počítáno i pro n = 14 a n = 10.

## Výsledek (binomická aritmetika, `g1_power.py`, výstup `g1_power.json`)
P(průchod) pro skutečnou epizodní recall/precision `p`; „bod“ = bodový odhad ≥ práh, „CI“ = Wilsonova dolní 95% mez > práh.

| n epizod | p | recall bod | recall CI | precision bod | precision CI |
|---|---|---|---|---|---|
| 21 | 0,4 | 0,174 | 0,004 | 0,035 | 0,000 |
| 21 | 0,5 | 0,500 | 0,039 | 0,192 | 0,001 |
| 21 | 0,6 | 0,826 | 0,200 | 0,524 | 0,011 |
| 21 | 0,7 | 0,974 | 0,551 | 0,852 | 0,086 |
| 21 | 0,8 | 0,999 | 0,891 | 0,986 | 0,370 |
| 14 | 0,7 | 0,969 | 0,355 | 0,781 | 0,161 |
| 10 | 0,7 | 0,953 | 0,149 | 0,850 | 0,028 |

Minimum zachycených epizod pro průchod CI při n = 21: recall **15/21**, precision **18/21** alertních epizod.
(Precision je zde přiblížena n = 21 alertními epizodami; skutečný jmenovatel určí alert budget, který musí být zmrazen.)

## Závěr
1. **Bodová kritéria nediskriminují:** radar se skutečnou recall 0,4 (pod prahem) projde recall bodově v 17 %,
   radar se skutečnou precision 0,5 projde v 19 %. Bodový GO by byl slabý důkaz.
2. **Kritéria s nejistotou jsou téměř neprůchodná:** i dobrý radar (recall 0,7, precision 0,7) projde obě CI podmínky
   s pravděpodobností ≈ 0,55 × 0,09 ≈ **5 %** (horní odhad; Brier vs. 3 baseliny a bootstrap po blocích sílu dál snižují).
3. **Ex-ante nejpravděpodobnější výsledek G1 = INCONCLUSIVE** (n epizod je příliš malé), pokud radar nemá
   výjimečnou sílu (recall ≥ 0,8 a precision ≥ 0,9).

## Doporučení pro freeze manifest (k oponentuře ChatGPT)
- R1: rozhodovací pravidlo GO jen podle dolních mezí (bootstrap po blocích ≥ 14 d), nikoli bodových odhadů — jinak vysoká
  míra falešného GO.
- R2: do manifestu zapsat ex-ante power tabulku (tento dokument, SHA níže) a výslovně: INCONCLUSIVE je očekávaný výsledek,
  nikoli selhání procesu; INCONCLUSIVE = stop bez opakování.
- R3: zmrazit alert budget (počet alertních epizod) před během — určuje jmenovatel precision.
- R4: počet hodnotitelných epizod po purge/embargu spočítat z kalendáře a labelů **před** výpočtem predikcí; je-li < 15,
  G1 předem klasifikovat jako POWER NO-GO (nespotřebovávat schválený běh) a vrátit vlastníkovi.
- Nic z toho neupravuje prahy PROTOCOL.md po pozorování výsledků — žádné výsledky predikcí neexistují.

## Reprodukce
`python3 research/g1_power_preflight/g1_power.py > g1_power.json` (jen stdlib, deterministické).
SHA-256: `g1_power.py` `6dc09377b8aefbb0fa3678a73d2a5279aed3603f6edd3ba5dae699da1a135fb1`,
`g1_power.json` `bcc8ec66642dbf6dfac2762f80149e618bc4eeec379e73c6ceea3272ef5a4105`.
N (multiple testing) +0: nejde o hypotézu ani test výkonu.
