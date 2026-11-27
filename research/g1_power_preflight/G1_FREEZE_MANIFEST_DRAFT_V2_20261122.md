# Top Risk Radar V1 — G1 freeze manifest, NÁVRH v2 (NEZAMČENO, NESPUŠTĚNO)

Stav: **[N] návrh k oponentuře ChatGPT** (vlastník implementace G1 = ChatGPT, beze změny). Žádná tržní data, žádné predikce,
žádný výkon. Výhradně PAPER. Autor: Claude, autopilot běh #98, 2026-11-22.

Báze: návrh v1 `research/top_risk_radar_v1/G1_FREEZE_MANIFEST_DRAFT_20261112.md` @ `a27831b`
(větev `claude/radar-g1-freeze-20261112`). **§1–§9 v1 platí beze změny**, pokud níže není uvedeno Δ. Vstupy: power preflight
PR #73 (`604bda8`, binomická aritmetika precision/recall) a tento běh (`g1_bss_power.py`, syntetická síla BSS pravidla).
Schválení vlastníka: `OWNER_DECISIONS.md` ř. 49 (2026-11-12, jediný běh) — B5 v1 je tím **splněn**; neznamená splnění ostatních bran.

## Δ1 (R1) — rozhodnutí jen podle dolních/horních mezí, primární metrika BSS
- G1 verdikt rozhoduje **výhradně** pravidlo v1 §6 (BSS vs. nejlepší z M0/B1/B2, moving-block bootstrap 14 a 28 d, 2000 replik,
  seed 20261112). Bodový BSS ≥ 0,05 je nutná, ne postačující podmínka.
- Epizodní precision/recall/falešné epizody za měsíc jsou **jen popisné**. Důvod (PR #73): při 21 epizodách bodová kritéria
  nediskriminují (recall 0,4 projde v 17 %), CI kritéria projde i dobrý radar jen v ≈ 5 %. Kritéria PROTOCOL.md zůstávají
  kritérii přijetí kandidáta po G1, ne G1.

## Δ2 (R2) — ex-ante power je součástí manifestu
Syntetika (`g1_bss_power.py`, 300 simulací/řádek, bootstrap 1000, seed 20261122; optimistická: oracle kalibrace, reference
jen M0, AR(1) šum φ = 0,9; `L` = počet pozitivních rozhodovacích dní na epizodu, `s` = síla signálu):

| epizod | L | s | skutečný BSS | P(GO) | P(NO-GO) | P(INCONCL.) |
|---|---|---|---|---|---|---|
| 21 | 8 | 0 | 0,000 | 0,000 | 1,000 | 0,000 |
| 21 | 8 | 0,5 | 0,021 | 0,067 | 0,137 | 0,797 |
| 21 | 8 | 1,0 | 0,107 | 0,630 | 0,007 | 0,363 |
| 21 | 8 | 1,5 | 0,242 | 0,883 | 0,000 | 0,117 |
| 21 | 14 | 0,5 | 0,037 | 0,240 | 0,077 | 0,683 |
| 21 | 14 | 1,0 | 0,146 | 0,740 | 0,000 | 0,260 |
| 14 | 8 | 1,0 | 0,081 | 0,287 | 0,040 | 0,673 |
| 14 | 8 | 3,0 | 0,681 | 0,717 | 0,000 | 0,283 |

(celá mřížka v `g1_bss_power.json`.) Čtení:
1. Pravidlo BSS + bloky je **řádově silnější** než epizodní CI kritéria: radar se skutečným BSS ≈ 0,11 dostane GO v ≈ 63 %,
   radar s BSS ≈ 0,24 v ≈ 88 %. Falešné GO u nulového signálu 0/300 (ale viz omezení O1).
2. Radar se skutečným BSS ≈ 0,02–0,04 skončí převážně INCONCLUSIVE — to je správné chování, ne selhání.
3. Při 14 epizodách je i velmi silný radar ve 28 % INCONCLUSIVE jen proto, že < 3 foldy mají ≥ 3 epizody ⇒ podpora Δ4.
4. INCONCLUSIVE = konec G1 bez opakování a bez ladění (v1 §9 platí).

Omezení: O1 nulový model zde nemá přeučení (b ≈ 0); skutečný B3 s 9 featurami a výběrem C může mít falešné GO > 0 —
ochranou je vnitřní validace a fold podmínka ≥ 2/3, nikoli tato simulace. O2 reference M0 je nejslabší; s B1/B2 je P(GO) nižší.
O3 L (pozitivních dní na epizodu) z censu `0103335` neznám — G0 ho musí vykázat; tabulka pokrývá 8 a 14.
O4 kalibrační sklon v [0,5; 2,0] (v1 §6) zde nesimulován (oracle kalibrace).

## Δ3 (R3) — zmrazený alert budget (jen sekundární metriky)
- Práh alarmu v každém foldu = 90. percentil predikcí B3 **na trainu téhož foldu** (v1 §6), stanovený před predikcí testu.
- Alertní epizoda = alarmy seskupené stejně jako labely (odstup > 14 d ⇒ nová epizoda). Jmenovatel precision = počet
  alertních epizod; 0 alertních epizod ⇒ precision `UNDEFINED` (ne 0, ne 1). Nic z toho nemění verdikt G1.

## Δ4 (R4) — POWER NO-GO pre-gate (před fitem jakéhokoli modelu)
- Po G0 datovém manifestu a z **labelů a kalendáře** (bez featur a predikcí) spočítat seskupené pozitivní epizody v OOS foldech
  po vyřazení (chybějící minuty, bez obchodu), purge a embargu 14 d.
- `< 15` hodnotitelných epizod **nebo** `< 3` foldy s ≥ 3 epizodami ⇒ `POWER_NO_GO`: výkonový běh se nespotřebuje,
  vrátit vlastníkovi. Práh 15 je stanoven teď, před jakýmkoli výsledkem modelu (census 21 je znám — LOW_N_MARGIN_POST_HOC_GATE
  z v1 §7 platí dál).
- Pre-gate je samostatný krok s vlastním artefaktem (`power_pregate.json`), commitnutý před výkonovým během.

## Δ5 — stav blokerů v1 §8 k 2026-11-22 (ověřeno v remote větvích radaru, jen čtení)
| Bloker | Stav |
|---|---|
| B1 fit B1/B2/B3 + vnitřní validace | **chybí** (v `research/xrp-top-risk-radar-v1-20261108` jen M0/baselines prevalence) |
| B2 moving-block bootstrap | **chybí** (v radarových větvích nenalezen; zdejší `block_bootstrap_bss` je jen syntetický nástroj, ne implementace G1) |
| B3 reálný loader 1m→denní XRP+BTC s PIT | částečně (`binance_spot_trades.py`, `feature_input.py`, PIT brány); integrace do runneru chybí |
| B4 runner + G0 manifest | **chybí** (preflight brány `g1_preflight.py`/`g1_manifest_gate.py` existují, runner ne) |
| B5 řádek vlastníka | **splněno** (OWNER_DECISIONS ř. 49) |
| B6 nezávislá revize manifestu | čeká ChatGPT (tento návrh) |

## Doporučení
G1 zůstává **NESPUSTITELNÝ** do uzavření B1–B4 a B6. Power argument (Δ2) říká, že má smysl G1 dokončit (rozhodovací pravidlo
dokáže rozlišit radar s BSS ≥ 0,1), na rozdíl od epizodních kritérií. Vlastník implementace B1–B4: ChatGPT; Claude provede
nezávislou kontrolu na přesných SHA. Žádné úpravy prahů po jakémkoli výsledku; N (multiple testing) +0.

## Reprodukce
`python3 research/g1_power_preflight/g1_bss_power.py 300 > g1_bss_power.json` (numpy, deterministické, ≈ 3 min).
SHA-256: `g1_bss_power.py` `af7cde2776de48b3a15cd504aaa78a6489008f794dc0a43c50378de34b0a250d`,
`g1_bss_power.json` `6312159dba06704e15a56d23bb57d446896729012bb6420dd23bbb34634a556a`.
Testy: `tests/test_g1_bss_power.py` + `tests/test_g1_power_preflight.py` — 6 passed lokálně (Python 3.13).
