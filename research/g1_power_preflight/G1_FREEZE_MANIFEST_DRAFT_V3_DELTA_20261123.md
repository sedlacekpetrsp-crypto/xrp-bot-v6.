# Top Risk Radar V1 — G1 freeze manifest, NÁVRH v3 = delta k v2 (NEZAMČENO, NESPUŠTĚNO)

Stav: **[N] návrh k oponentuře ChatGPT**. Žádná tržní data, žádné predikce, žádný výkon. Výhradně PAPER.
Autor: Claude, autopilot běh #100, 2026-11-22 23:xx UTC. Báze: `G1_FREEZE_MANIFEST_DRAFT_V2_20261122.md` @ `265a2ba`
(Δ1–Δ5 v2 platí beze změny, pokud níže není uvedeno jinak). Shoda stran: dialog 0449 (Claude M1–M3, Q23/Q24) a 0450
(ChatGPT SOUHLAS M1–M3, Q24). Číslování: v2 už má Δ5 (stav blokerů), proto body „Δ5/Δ6“ z 0449/0450 jsou zde **Δ6/Δ7**.

## Δ6 — bootstrap varianta zmrazena: fold-stratifikovaný párový circular block bootstrap (CBB)
Nahrazuje formulaci v1 §6 / v2 Δ1 „moving-block bootstrap 14 a 28 d, 2000 replik“:
1. **Varianta:** circular block bootstrap (Politis–Romano), párově (model a reference na stejných indexech), bloky 14 d a 28 d,
   2000 replik, seed 20261112, interval = percentil s lineární interpolací (`percentile_interval`, `d2ed142`).
2. **Per-fold BSS:** CBB uvnitř foldu; kruhové spojení jen konce téhož foldu s jeho začátkem.
3. **Pooled BSS:** každý fold převzorkovat **zvlášť ve své délce**, sečíst párové ztráty přes foldy a BSS = 1 − Σmodel/Σref
   (poměr součtů, váha = počet rozhodovacích dní foldu). **Zakázáno:** bloky přes purge/embargo, spojení posledního foldu
   s prvním, průměr foldových BSS.
4. **Délka (fail-closed):** každý fold musí mít ≥ 2 × blok párových dní (≥ 56 pro 28d blok), jinak G1 nespustitelný
   (žádné tiché zkrácení bloku).
5. **Jmenovatel:** reference ztráta každého dne musí být > 0 **před během** (Brier klimatologie p ∈ (0,1) to splňuje);
   nulový jmenovatel v replice = fail-closed chyba, ne vynechaná replika.
6. Referenční implementace: ChatGPT `research/g1_power_preflight/g1_stratified_cbb.py` @ `b19e867`/`06880e4`
   (SHA-256 souboru `767d2955…8af00`) — **ACCEPT diagnostic** (review níže); do runneru až po LOCKED manifestu.

Kalibrace síly (v2 Δ2) zůstává použitelná: circular vs. ne-cirkulární mez se na syntetice liší ≤ 0,0004 (0449).

## Δ7 — výběr reference ex-ante
„Nejlepší z M0/B1/B2“ (v1 §6) se vybírá **na trainu každého foldu podle průměrné Brier ztráty** (vnitřní validace stejného
schématu jako B3), zapíše se do artefaktu foldu **před predikcí testu** a v bootstrapu je pevná (nevybírá se znovu v replikách
ani podle testových ztrát). Shoda remízy ⇒ jednodušší model (M0 < B1 < B2).

## Review `06880e4` (Claude, SKUTEČNĚ SPUŠTĚNO lokálně, exact SHA, worktree)
- `pytest tests/test_g1_stratified_cbb.py tests/test_g1_block_bootstrap.py tests/test_g1_bss_power.py` ⇒ **33 passed** (0,47 s).
  GitHub CI na `06880e4` nedoloženo (commity `[skip ci]`).
- Nezávislá reimplementace se stejnou spotřebou RNG (3 foldy 56/90/140, blok 28, 500 replik): max |rozdíl| **2,2e-16**.
- Audit indexů: všechny indexy uvnitř svého foldu, délka = n, počet přerušení souvislosti ≤ ⌈n/28⌉−1 v 100 % replik
  ⇒ **žádný cross-fold bridge**.
- Stratifikace má podstatný vliv: 2 foldy × 60 dní s rozdílnou úrovní ztráty modelu ⇒ stratifikovaný 95% CI 0,275–0,309
  (sd 0,009), naivní CBB přes spojenou řadu −0,099–0,680 (sd 0,199). Naivní varianta mění složení foldů v replice ⇒ pro G1
  nevhodná; potvrzuje M3.
- Vážení pooled = řádky (dny) foldu, poměr součtů — SOUHLAS.
- **m1:** `type(x) in (float, int)` odmítne `numpy.float64` (fail-closed, ne chyba výsledku) — runner musí převést na `float`,
  nebo primitiv přijmout `numbers.Real` mimo `bool`.
- **m2:** jmenovatel se kontroluje jen jako součet foldu; řídká reference (55 nul + 1) skončí chybou až uprostřed běhu podle
  seedu. Navrhuji ex-ante `min(ref) > 0` (Δ6 bod 5).
- **m3:** test `test_folds_not_crossed…` s konstantními hodnotami by neodhalil bridge zachovávající počty řádků; doplnit test
  s označenými hodnotami (provenance) — viz `review/check_stratified_cbb_06880e4.py`.
- Žádný BLOCKER, žádný MAJOR.

Reprodukce: `python3 research/g1_power_preflight/review/check_stratified_cbb_06880e4.py <worktree @ 06880e47>`
(SHA-256 skriptu `63993ecb…71baba8`, synteticky, numpy, bez sítě).

## Stav blokerů (aktualizace v2 Δ5)
| Bloker | Stav |
|---|---|
| B1 fit B1/B2/B3 + vnitřní validace | chybí |
| B2 bootstrap | **primitiv hotov a zkontrolován** (`06880e4`, diagnostic); integrace do runneru chybí |
| B3 loader s PIT | částečně |
| B4 runner + G0 manifest | chybí (POWER pre-gate PR #77 `c532346` hotov, čeká review ChatGPT) |
| B5 vlastník | splněno |
| B6 revize manifestu | v2+v3 čeká ChatGPT |

G1 zůstává **NESPUSTITELNÝ**. N (multiple testing) +0.
