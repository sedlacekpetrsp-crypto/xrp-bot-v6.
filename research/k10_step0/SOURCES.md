# K10 krok 0 — předregistrované zdroje štítků (§6.2) a sonda ledgeru (§6.3)

Stav: PŘEDREGISTROVÁNO 2026-11-18 ~11:30 UTC (autopilot běh #78), **před jakýmkoli dotazem na Wayback CDX**.
Strojově čitelné znění: `sources.json` (autorita); pravidla R1–R7: `research/k10_step0_sources.py`; testy
`tests/test_k10_step0_sources.py`. Žádné ceny, výnosy ani výkon.

## Zdroje (uzavřený seznam)
| ID | URL | Formát | Pole účtu → štítku |
|---|---|---|---|
| S1 | `https://api.xrpscan.com/api/v1/names/well-known` | JSON pole | `account` → `name` |
| S2 | `https://api.xrpscan.com/api/v1/account/{account}` (jen adresy cohortu §1) | JSON objekt | URL účet (= `account`) → `accountName.name` |

Vyřazeno s důvodem: Bithomp API (vyžaduje `x-bithomp-token`, archiv by měl chybovou stránku), HTML stránky
exploreru (bez pevného pole štítku — nelze vynutit 0392 F1/F2), Ripple Data API `/v2/gateways` (IOU emitenti,
ne vkladové účty burz), Dune/clustering/destination tags/LLM (bez PIT, zakázáno §2).

## Výběr snímku
Pro každou URL a rok jediný **nejnovější** snímek s `captured_at < sample_start`, status 200, mimetype JSON
(CDX `matchType=exact`). Jiný snímek zvolit nelze (žádný cherry-picking).

## Atribuce (zmrazeno)
R3 normalizace = lowercase + NFKC + ořez/sloučení mezer, **bez odstraňování sufixů**; R4 burza jen při přesné
shodě s aliasem v `exchange_allowlist` (46 entit), jinak „neznámý“ (zůstává ve jmenovateli); R5 rozpor mezi
S1/S2 nebo duplicitními řádky ⇒ „neznámý“ (0392 F1); R1 čte se jen dvojice pole účtu/štítku (0392 F2);
R7 allowlist se po prvním dotazu na CDX nemění, nezařazená jména jen diagnosticky do reportu.
Známé riziko: přesná shoda podhodnotí pokrytí (např. „Binance Hot Wallet“ ⇒ neznámý) ⇒ chyba jen směrem k DATA NO-GO.

## §6.3 sonda ledgeru
`ledger_probe.py` přes Actions (`k10-ledger-probe.yml`, spouštěč `RUN_REQUEST_LEDGER_PROBE`): `server_info`
a full-history test na `s2.ripple.com:51234` a `xrplcluster.com`, binárním hledáním přesné hranice 4 oken
(90 d před 1. 1. 2020–2023), vzorek 20 ledgerů na okno (bajty, počet tx/Payment, latence) a extrapolace.
Verdikt předem: **FEASIBLE_DIRECT** ⇔ ≤ 5 h sekvenčně a ≤ 50 GB; jinak **INFEASIBLE_DIRECT** (bez automatické
náhrady — alternativy jako systematický vzorek ledgerů nebo hromadný dataset jsou dodatek protokolu k oponentuře).
Apriorní odhad (ne měření): ~22 tis. ledgerů/den ⇒ ~2 mil. ledgerů na okno, ~8 mil. celkem ⇒ přímé stahování
pravděpodobně neproveditelné.
