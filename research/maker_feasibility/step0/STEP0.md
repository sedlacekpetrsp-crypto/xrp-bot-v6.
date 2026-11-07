# Krok 0 — atribuce selhání z hotových výsledků (jen čtení)

Datum 2026-11-07. PAPER. Žádný backtest, žádná nová data, žádný workflow.

## Metoda
- Zdroj: všech 73 unikátních `research/*/results.json` ze všech vzdálených větví a `refs/pull/*/head`
  (seznam v `sources.tsv`). PR bez results.json: jen #1 (není strategie).
- Pro každý blok s `net_pnl`: náklady = `costs`, jinak `fees + slippage_cost`; hrubý = `gross_before_fees_and_slippage`, jinak net + náklady.
  Funding a likvidace zůstávají v hrubém (maker exekucí neodstranitelné; viz námitka ChatGPT 0118/5d).
- Primární bloky = base / ×1, mimo stress, ×2, ×3, tuning, grid, per_symbol (`attr2.py`).
- Nutný (nerealistický) test podle ChatGPT 0118/5a: **nulové poplatky i skluz**. Strategie je „nákladově limitovaná“
  jen když hrubý > 0 ve **všech** primárních blocích a čistý ne. DSR/WF/koncentrace tím neopravujeme.

## Výsledek (`attribution.tsv`)
| třída | počet |
|---|---:|
| hrubý ≤ 0 aspoň v jednom primárním bloku (selhání signálu, ne nákladů) | 69 |
| hrubý > 0 všude, čistý ne (kandidát „cost-only“) | 1 — `retest_cost_review_20261019` |
| čistý > 0 všude | 1 — `funding_carry` |
| bez nákladových polí | 2 — `cross_market_dispersion_20261026`, `polymarket_xrp` |

- `retest_cost_review_20261019`: v kontrolovaném období hrubý po skluzu +137 / 185 obchodů (~0,07 % notionalu na obchod),
  ale ve vývojovém vzorku hrubý po skluzu **−18,52** (README téže studie). Není cost-only.
- `funding_carry`: čistý kladný; ZAMÍTNUTO na A2/B5 (6 resp. 11 obchodů), tedy na velikosti vzorku; ×3 final −32,7 je důsledek 5 obchodů. Není cost-only.
- `cross_market_dispersion`, `polymarket_xrp`: nepokryto (neobsahují ledger nákladů) — nejde o obchodní PnL s poplatky.

## Závěr
**STOP 0.** Žádná hotová strategie neselhala výhradně na nákladech. Krok 1–4 protokolu (stažení L2/trade dat) se nespouští.
Protokol V1 (`de1088f`) zůstává beze změny; dodatek V2 (opravy fill bounds, implementation shortfall, funding) se napíše
jen pokud se téma C znovu otevře novou hypotézou.

Reprodukce: `python3 research/maker_feasibility/step0/attr2.py <adresář s results.json>`;
testy `python3 -m unittest test_attr` (v adresáři step0).
