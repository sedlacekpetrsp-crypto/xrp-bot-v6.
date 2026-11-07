# R10 — rekonstrukce počtu variant (N) a rozptylu Sharpe pokusů (2026-11-07)

Výhradně PAPER, jen čtení gitu. Žádná nová data z burzy, nic se neladí, žádná hypotéza se netestuje (nepočítá se do limitu 3/den).
Nástroj: `tools/research/variant_count.py` (pravidla počítání v hlavičce, stanovena před výpočtem), výstup
`reports/variant-count-reconstruction-20261107.json` (každá hypotéza / test zvlášť, se souborem, ze kterého je počet).

## Výsledek

| Část | Hypotéz / testů | Doložené N | Zdroj |
|---|---|---|---|
| Historie (inventář 110) — `candidates` (ELITE) | 26 | 58 | `summary.json` / `diagnostics.json` |
| — `variants` (`protocol.json`) | 7 | 17 | `protocol.json` |
| — jediná `config` | 17 | 17 | `*_results_*.json` |
| — jedno pravidlo, `runs` = období × náklady | 45 | 45 (49 počítáno na aktivum) | `*_validation_*/results.json` |
| — NEDOLOŽENO (strojově nenalezeno) | 15 | 0 | viz níže |
| **Historie celkem** | 110 | **137 (horní 141)** | |
| R-série PR #11–#32 (sloupec `variant` v `trades.csv`, bez placeb a benchmarků) | 16 | **53** | `research/*/trades.csv` |
| **Celkem doloženo** | 126 | **N = 190 (194)** | |

Nedoloženo (15): elite/V4, V5, V8, V60, autocorr_regime, candle, combined_selection_replay, cross_market_dispersion,
hourly_retest, polymarket_xrp, polymarket_xrp_signal, prospective_market_evidence, research, retest_cost_review,
xrp_bank_credit_expansion (část jsou audity / sběr dat bez obchodů, část má počet jen v textu).
Nezapočteno vůbec: ladění produkčních botů (FLY, TV 9 variant, BEST-OF…), číslování ELITE V1–V60 naznačuje další
nezaznamenané verze ⇒ **190 je doložená DOLNÍ mez**, skutečné N je vyšší.

**Rozptyl Sharpe pokusů** (roční Sharpe validace 2023–24, ×1, 42 strategických variant R-série; stejné dělení, náklady, √365):
- bez funding carry (41 směrových variant): průměr 1,24, **V[SR] = 0,40**;
- včetně carry (Sharpe 11,0 při DD 0,5 %): V[SR] = 2,67.
Pozn.: směrové varianty jsou ve validaci (býčí 2023–24) silně korelované s trhem ⇒ 0,40 je rozptyl jednoho režimu, ne obecná konstanta.

## Dopad na Deflated Sharpe (T = 731 dní, normální výnosy; SR0 = očekávané max. SR šumu / Sharpe potřebný pro DSR ≥ 0,95, ročně)

| N | V = 0,40 | V = 0,5 (dosud) | V = 2,67 |
|---|---|---|---|
| 159 | 1,70 / 2,87 | 1,90 / 3,07 | 4,39 / 5,58 |
| 190 | 1,74 / 2,91 | 1,94 / 3,11 | 4,49 / 5,68 |
| 250 | 1,79 / 2,96 | 2,01 / 3,18 | 4,64 / 5,83 |

Závěr:
1. Pracovní N = 159 bylo **podhodnocené**; doložená dolní mez je 190. Na výsledku DSR to ale skoro nic nemění
   (práh se posune o ~0,04 Sharpe) — DSR je na N necitlivé, rozhoduje V[SR].
2. Předpoklad V[SR] = 0,5 je pro směrové strategie mírně konzervativní (doloženo 0,40). Pro tržně neutrální strategie s nízkou
   volatilitou (carry) je rozptyl o řád vyšší ⇒ jejich DSR počítat s V odhadnutým z jejich vlastní rodiny, ne s 0,5.
3. Žádný dosavadní výsledek nepřekročil ani SR0 ≈ 1,9 kromě carry (ten padl na počtu obchodů) ⇒ závěry R1–R11 se nemění.

Návrh (rutinně, bez změny kritérií): od R12 uvádět DSR s **N = 190 + varianty od 2026-11-07** a V ∈ {0,40; 0,5}; 0,5 zůstává hlavní
kvůli srovnatelnosti. Ruční doplnění 15 nedoložených hypotéz = další krok R10 (nízká priorita).
