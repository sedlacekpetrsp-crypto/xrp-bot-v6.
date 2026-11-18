# K10 XRPL-EXCHANGE-INFLOW — protokol kroku 0 (DATA ONLY)

Stav: PŘEDREGISTROVÁNO 2026-11-18 (Claude, dialog 0388; dohoda ChatGPT 0387 + Claude 0384/0386). NIC NESTAŽENO.
Rozsah: pouze dostupnost a pokrytí PIT štítků. Žádné ceny, výnosy, signály, náklady ani výkonnostní testy.
Výsledek kroku 0 je binární: **DATA GO** / **DATA NO-GO**. DATA GO neopravňuje k výkonu — ten vyžaduje
samostatný protokol a řádek `SCHVÁLENO:` v `dialog/OWNER_DECISIONS.md` (resp. pokrytí schválením PAPER 2026-11-06).

## 1. Cohort (jediná definice, neměnná)
- Zdroj rankingu: validované ledgery XRPL (hash ledgeru se zaznamená), žádný třetí žebříček.
- Hodnocené roky (dev): 2020, 2021, 2022, 2023; `sample_start` = 1. 1. 00:00:00 UTC daného roku.
- Okno rankingu: `close_time ∈ [sample_start − 90 d, sample_start)`.
- Metrika: součet `delivered_amount` v drops XRP transakcí `Payment`, `TransactionResult = tesSUCCESS`,
  `Account ≠ Destination`, nativní XRP (ne IOU); agregace podle `Destination`.
- **N = 50**; pořadí sestupně podle metriky, shoda ⇒ adresa lexikograficky vzestupně.
- `ranked_at` = `close_time` posledního validovaného ledgeru okna (společné pro celý cohort; vynuceno
  `research/k10_fixed_cohort.py`, MINOR-1).
- N, okno ani roky se po zahlédnutí jakýchkoli dat NEMĚNÍ (žádný ex-post výběr).

## 2. Štítky (PIT)
- Jediný přípustný zdroj historického štítku: snímek Internet Archive Wayback, raw varianta
  `https://web.archive.org/web/<YYYYMMDDhhmmss>id_/<původní URL>`.
- `captured_at` se ODVOZUJE z 14místného razítka v URL / CDX řádku, nikdy se nedeklaruje.
- Podmínka: `captured_at < sample_start` striktně.
- Z CDX se zaznamená: `timestamp`, `original`, `statuscode`, `mimetype`, `digest` (SHA-1 base32);
  po stažení `content_sha256`. Snímek se statusem ≠ 200 se nepoužije.
- Ověření bytů: `research/k10_snapshot_bytes_gate.verify_snapshot` (s opravou regexu `17455a8`);
  štítky: `research/k10_label_pit_gate.validate_labels` = jediná autorita (modul as-of z 0384-chatgpt se
  nezačleňuje).
- Spojka `ArchivedLabel` ↔ `Snapshot` (0386 MINOR-3): štítek se smí použít jen pokud `source_url`,
  `captured_at` a `content_sha256 == expected_sha256` odpovídají ověřenému snímku. Implementace před
  spuštěním kroku 0 (jinak běh nesmí začít).
- Účet bez snímku nebo s nejednoznačným štítkem = „neznámý“ a zůstává ve jmenovateli. Heuristické
  štítky (clustering, destination tags, LLM) ZAKÁZÁNY.
- Snímek dokládá jen veřejnou viditelnost štítku k datu, ne správnost atribuce.

## 3. Brána
- Pro každý rok: `coverage = označený objem cohortu / celkový objem cohortu` (v okně rankingu)
  počítaný `fixed_cohort_coverage(..., threshold=0.80)`.
- **DATA GO** ⇔ coverage ≥ 0,80 ve **všech čtyřech** letech. Jediný rok pod prahem ⇒ **DATA NO-GO**
  (žádné vyřazování let, žádná změna N).
- Selhání dat (ledger nedostupný, CDX nedostupný) ⇒ DATA NO-GO s důvodem, ne opakování s jinou definicí.

## 4. Diagnostika (není brána, jen do reportu)
- Podíl objemu cohortu na celkovém XRP objemu plateb v okně.
- Podíl objemu plateb na účty založené po `sample_start` (rotace hot walletů cohort nezachytí).
- Počet účtů cohortu typu Ripple/AMM/ODL bez štítku (konzervativně „neznámý“).

## 5. Provedení
- Pouze GitHub Actions (sandboxy agentů mají Wayback blokovaný), izolovaná větev `research/k10-xrpl-inflow-audit-<datum>`.
- Výstupy: CSV cohortu (rok, rank, adresa, metrika, ledger hash), CSV snímků (CDX pole + SHA-256),
  JSON verdikt; artefakt běhu + commit SHA.
- Žádný zápis na Render, žádný LIVE, žádné ceny.

## 6. Otevřené před spuštěním
1. ~~Implementace spojky ArchivedLabel ↔ Snapshot~~ — HOTOVO `d3aab73` (`research/k10_label_snapshot_link.py`).
2. ~~Seznam zdrojových URL~~ — PŘEDREGISTROVÁNO 2026-11-18 (autopilot běh #78) v `research/k10_step0/sources.json`
   + `SOURCES.md`, pravidla R1–R7 v `research/k10_step0_sources.py`; jen JSON zdroje S1/S2 (XRPScan), allowlist
   burz zmrazen, konflikt ⇒ „neznámý“ (0392 F1), vazba na pole štítku (0392 F2). Žádný dotaz na CDX zatím neproběhl.
3. Zdroj ledgeru — sonda proveditelnosti `research/k10_step0/ledger_probe.py` (workflow `k10-ledger-probe.yml`);
   předregistrovaný verdikt FEASIBLE_DIRECT ⇔ odhad ≤ 5 h sekvenčně a ≤ 50 GB pro všechna 4 okna. Jinak
   INFEASIBLE_DIRECT ⇒ změna zdroje/definice cohortu je dodatek protokolu s oponenturou ChatGPT, ne ad-hoc přepnutí.
