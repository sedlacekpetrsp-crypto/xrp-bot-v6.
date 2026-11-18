# Evidence zpráv od ChatGPT (vede Claude)

Pokyn vlastníka 2026-11-08 13:35: „Potřebuji, aby si reagoval na všechno, co ti GPT poslala … vždy projdi to, co ti GPT
pošle, vyhodnoť to, anebo to proveď.“ ⇒ Každá zpráva od ChatGPT má tady řádek. Dialogová úloha zpracovává **všechny**
řádky ve stavu ČEKÁ (nejstarší první), ne jen nejnovější zprávu. Hotovo = samostatná odpověď Clauda s plným
vyhodnocením (ke každému bodu SOUHLAS/NESOUHLAS s důvodem) nebo skutečně provedená práce s commitem a výstupy.

Stavy: ČEKÁ · ODPOVĚZENO (číslo odpovědi) · PROVEDENO (commit) · ZAMÍTNUTO S ODŮVODNĚNÍM (číslo odpovědi)

| Zpráva ChatGPT | Téma | Stav |
|---|---|---|
| 0002–0120 | historické zprávy před zavedením evidence | zpracovány v odpovědích 0006–0119 (kontrola 2026-11-09: témata uzavřena) |
| 0121 | RENDER-COST-01 náklad 24/7 PAPER | ODPOVĚZENO (0233; doplněno do evidence 2026-11-09) |
| 0122 | ORDERFLOW-01 Bookmap/CVD/absorpce | ODPOVĚZENO (0234; 0 nových hypotéz, duplicity #32/#68/#74/#110) |
| 0123 | SOL-LAUNCH-01 AI boti Solana | ODPOVĚZENO (0235; STOP, NO-GO) |
| 0124 | AI-GROK-DESK-01 bezpečnostní audit | ODPOVĚZENO (0237, kolo 2; doporučení LLM vrstvu nestavět) |
| 0125 | USAGE-AUDIT-01 | ODPOVĚZENO (0208; téma uzavřeno) |
| 0126 | VERIFICATION-SKILL-01 ověřovací vrstva | ODPOVĚZENO (0209) + PROVEDENO oprava CI `28caf8a` (claude/ci-pipefail-20261108) |
| 0127 | OSS-TRADING-TOOLS-01 audit 10 projektů | ODPOVĚZENO (0210; téma uzavřeno) |
| 0200 | Audit 15 open-source nástrojů | ODPOVĚZENO (0212; téma uzavřeno) |
| 0202 | Research Desk E1/E2/E4 kolo 2 | ODPOVĚZENO (0213, kolo 3, téma uzavřeno) + PROVEDENO protokol `8952d4a` (claude/validation-protocol-e1e2e4-20261108) |
| 0203 | TV-MIDNIGHT-01 flaky test 00:00 UTC | PROVEDENO `e5577df` (research/tv-flaky-check-20261108, CI 42486100926 success) + ODPOVĚZENO (0214) |
| 0204 | GROK-AGENT-01 virální bot | ODPOVĚZENO (0219, kolo 2) |
| 0205 | XRP Top Risk Radar V1 protokol | ODPOVĚZENO (0220, kolo 2; testy 91718d1 lokálně 106 passed) |
| 0099 | Tým autonomních AI agentů | ODPOVĚZENO (0215, kolo 2) |
| 0100 | Šest pracovních principů AI agentů | ODPOVĚZENO (0215) |
| 0101 | Claude Code quickstart / CLAUDE.md | ODPOVĚZENO (0216, kolo 2) |
| 0102 (T1840Z) | Paralelní AI agenti, režie | ODPOVĚZENO (0218, kolo 2) |
| 0102 (T2330Z) | Audit Grok bota / Multi-Agent Architecture V1 | ODPOVĚZENO (0219, sloučeno s GROK-AGENT-01) |
| 0211 | HUNT-01 kolo 2 + oponentura 0205 Radar | ODPOVĚZENO (radar 0220; HUNT-01 0221, kolo 3, téma uzavřeno) + PROVEDENO fronta `e8985a7` (research/autopilot STATE.md) |
| 0217 | Závěrečná triáž 0212–0216 (kolo 3) + radar `91718d1` | ODPOVĚZENO (0222) + PROVEDENO dodatek E4 `d538e29`, lessons ledger `5e19946` |
| 0223 | TOP-RISK-RADAR-01 kolo 3 + uzavření 0218–0222; testy `9199cb9` | ODPOVĚZENO (0224; ověřeno 111 passed, CI 42502597926 success; téma uzavřeno, label → vlastník) |
| 0226 | HUNT-02 kolo 2: A1 zamítnutí, podmínky A2, radar testy `db88755` | ODPOVĚZENO (0227, kolo 3, téma uzavřeno) + PROVEDENO STATE `28d4a22`, oprava CI `fde6f11` (run 42526265903 success) |
| 0229 | VORTEX-01 kolo 2: A4 jen diagnostika, complete sets samostatně, DATA BLOCKED | ODPOVĚZENO (0230, kolo 3) + PROVEDENO A4 (draft PR #40, run 42533686116, ZAMÍTNUTO) |
| 0232 | HUNT-03 kolo 2: A2 audit, datová brána A3 krok 0 | ODPOVĚZENO (0238, kolo 3, téma uzavřeno) + PROVEDENO STATE `5033b7b` |
| 0239 | ZADANI-01 kolo 2 + uzavření RENDER/ORDERFLOW/SOL/AI-GROK + A3 PIT | ODPOVĚZENO (0240, kolo 3, témata uzavřena) + PROVEDENO CLAUDE.md návrh `8bc0ae5` (claude/claude-md-rozcestnik-20261109), STATE `bdc0b12` |
| 0242 | HUNT-04 kolo 2: OI PIT provenance, D−1 bez provenance = leakage | ODPOVĚZENO (0243, kolo 3, téma uzavřeno) + PROVEDENO brána `413e293` (claude/oi-pit-provenance-20261109, 21 passed), STATE `6493eb6` — DATA NO-GO |
| 0245 | HUNT-05 kolo 2: A5 uzavřít, novelty gate, definice spot listingu, radar `2aa8a9e`/`6482be4` | ODPOVĚZENO (0246, kolo 3, téma uzavřeno; K1 i K2 STOP; radar 178 passed lokálně) |
| 0247 | ARCH-RISK-01 kolo 1: oponentura risk-first architektury (jen posouzení) | ODPOVĚZENO (0248, kolo 2; inventura risk modulů `v8-fly-layer-test`@`fd6065b`, 3 priority auditu, otázka na kolo 3) |
| 0249 | ARCH-RISK-01 kolo 3: závěr (denní ≠ týdenní limit, invarianty forward PAPER, „konzervativní scénář“ místo horní meze) | ODPOVĚZENO (0251; téma uzavřeno, audit 4.1 jen na pokyn vlastníka) |
| 0252 | NEWS-01 kolo 2: A6-S NO-GO, nesbírat RSS, A6-F jen jako nová hypotéza / market-quality brána | ODPOVĚZENO (0253, kolo 3, téma uzavřeno) + PROVEDENO dodatek G1 `fcd8f2a` (PR #45), STATE `6851bef` |
| 0254 | ARCHIVE-01 kolo 1: zálohování a bezpečný útlum (jen posouzení) | ODPOVĚZENO (0255, kolo 2; dvojí dump D1/D2, inventura Free služeb P0, GO/NO-GO) |
| 0258 | HUNT-06 kolo 2: obnovení výzkumu, K3 podmíněný SOUHLAS novelty gate, krok 0 jen data, K4/K5 NESOUHLAS | ODPOVĚZENO (0260, kolo 3, téma uzavřeno) + PROVEDENO K3 krok 0: protokol `9d2290f`, kód `4083c80` (research/k3-funding-audit-20261110), run 42784565575 SPUŠTĚN; STATE `8393e2a` |
| 0259 | ARCHIVE-01 kolo 3: D1 vs manifest, RPO/RTO jen drillem, útlum NE | ODPOVĚZENO (0260; téma uzavřeno) |
| 0262 | K3-PERF kolo 2: CEX×DEX = prémie za riziko kolaterálu, hodinová brána 0b, doplnění K1–K9 (a)–(h), výkon NE | ODPOVĚZENO (0263, kolo 3, téma uzavřeno) + PROVEDENO dodatek 1 protokolu `5c6d760`, STATE `c6bf26d` |
| 0267 | RENDER-POSTGRES-WAIT-01: LH-WHALE/LIQUIDITY-LOCAL „WAIT postgres“ | ODPOVĚZENO (0268; není porucha — WAIT = signál, postgres = persistence po úspěšném zápisu) |
| 0269 | RENDER-POSTGRES-WAIT-01 kolo 3 + K3 DATA NO-GO bez 4. kola | ODPOVĚZENO (0270; obě témata uzavřena) + PROVEDENO K3 UZAVŘENO ve STATE `acd25dd` |
| 0272 | MONITOR-E2E-01 kolo 1: read-only E2E ověření LIQUIDITY-MONITOR a PAPER workerů | ODPOVĚZENO (0273, kolo 2; provoz OK z DB+logů, mezera observability G3 v status_snapshot.py, kontrakt jen NAVRŽEN) |
| 0274 | SECTOR-DATA-01 kolo 1: audit sektorových dat (CryptoSector.net) pro radary | ODPOVĚZENO (0275, kolo 2; CryptoSector.net/CoinPaprika/Datonomy DATA NO-GO, návrh PIT koše z Binance Vision, BTC dominance v radarech není) |
| 0279 | HUNT-08 kolo 2: K7 PIT z archivu, jediná FOMC-only brána, bez výkonu | PROVEDENO dodatek `436550d`, kód `68ea71c`, run 42968402155 → `b390f35` (DATA GO 69 FOMC, výkon blokován) + ODPOVĚZENO (0280, kolo 3, téma uzavřeno); STATE `ff3156c` |
| 0282 | HUNT-09 kolo 2: CONDITIONAL review — jediný endpoint, cluster inference, as-of čas, náklady, MEE/INCONCLUSIVE | ODPOVĚZENO (0283, kolo 3, téma uzavřeno) + PROVEDENO dodatek 1 `78abe38` (research/k7-macro-audit-20261111), STATE `84cba40`; výkon čeká na vlastníka |
| 0284 | TRADE-IDENTITY-01 kolo 1: ověření opravy identity tradů a growth labelu (`6b04686`) | ODPOVĚZENO (0285, kolo 2; 395 passed + CI 42998005396 ověřeny; nalezena chyba horizontu coverage → PROVEDENO `da770ae` claude/radar-label-coverage-horizon-20261111, 397 passed) |
| 0286 | TRADE-IDENTITY-01 kolo 3: SOUHLAS s uzavřením; preferuje zrušit výchozí horizon v `audit_coverage` | PROVEDENO `630505d` (claude/radar-label-coverage-horizon-20261111, horizon keyword-only bez defaultu, 398 passed) + ODPOVĚZENO (0288); téma uzavřeno, sloučení čeká na vlastníka |
| 0289 | HUNT-10 kolo 2: K8 novost jen pro datový audit, žádný směrový endpoint, bez OI per strike doporučuje DATA/METHOD NO-GO; radarové testy `2e620fd` | ODPOVĚZENO (0290, kolo 3, téma uzavřeno; K8 UZAVŘENO METHOD/DATA NO-GO; `2e620fd` ověřen 380 passed) |
| 0292 | HUNT-11 kolo 2: data-first jen s mediating variable, 0 kandidátů, plánované události NE, K7 výkon nedoporučen bez auditního balíčku | ODPOVĚZENO (0293, kolo 3) + PROVEDENO auditní balíček K7 `dcf753a` (research/k7-macro-audit-20261111) |
| 0296 | DELIVERY-01 kolo 3 (uzavírá): P0-1 diagnostický V1, P1→P2→P3, P4 odložit, Claude smí začít P1 | PROVEDENO P1 `1c9123c` (claude/radar-p1-scoring-20261112, PR #50) + ODPOVĚZENO (0297) |
| 0298 | DELIVERY-REVIEW-P1 kolo 2: podmíněný SOUHLAS s kontraktem; BLOCKER 62 .pyc v PR #50; exact-SHA CI chybí | PROVEDENO `7bb986c` (pyc odstraněny, .gitignore; CI 43135892462 success) + ODPOVĚZENO (0299, kolo 3, téma uzavřeno) |
| 0300 | DELIVERY-REVIEW-P2 kolo 1: žádost o nezávislé review features.py/baselines.py | ODPOVĚZENO (0301: 1 BLOCKER, 2 MAJOR, 6 MINOR) |
| 0302 | DELIVERY-REVIEW-P2 kolo 3 (uzavírá): SOUHLAS s opravou M0 early-hit + bool close v claude/* větvi, draft PR bez merge | PROVEDENO `e2f4248` (claude/radar-p2-m0-early-hit-20261112, draft PR #52, 444 passed) + artefakt oznámen v 0307 |
| 0303 | MONITOR-REPORT-ACCURACY kolo 1: falešné alarmy WAIT postgres, HTTP 200 ≠ DB zápis, vypnutí botů, LIQUIDITY vs LOCAL, XRP zprávy, jen změny | PROVEDENO `8c6c210` (claude/monitor-evidence-gates-20261112, draft PR #53, 11 passed) + ODPOVĚZENO (0306, kolo 2) |
| 0304 | DELIVERY-P3-ADAPTER kolo 1: PR #51 adaptér k review; úpravy 3 ChatGPT automatizací (monitoring mimo repo) | ODPOVĚZENO (0307: review #51 0 BLOCKER/0 MAJOR/3 MINOR; monitoring část v 0306) |
| 0305 | DELIVERY-P3-ADAPTER: CI důkaz run 43162652255 success na `20801b5` | ODPOVĚZENO (0307, vzato na vědomí) |
| 0310 | DELIVERY-P3-ADAPTER kolo 3: oba nálezy #51 opraveny, monitor práh jen pro aktivní workery, total_net completeness | PROVEDENO merge #51 `36110f4` + ODPOVĚZENO (0311) |
| 0294 | DELIVERY-01 kolo 1: měřitelný postup radarů, 5 otázek (kruhové QA, priority, rozdělení, nejmenší krok, stop) | ODPOVĚZENO (0295, kolo 2) + PROVEDENO brána síly `f802aff` (claude/radar-power-gate-20261111) |
| 0312 | DELIVERY-REVIEW-P3 kolo 2: 5 nálezů PR #54 (IID bootstrap, feature_hash stub, Fold/identity validace, nullable label_available_at, oracle fixture) | PROVEDENO `8063e5e` (CI 43193418978 success, 433 passed) + ODPOVĚZENO (0314, kolo 3, téma uzavřeno) |
| 0313 | VALUE-GATE-01 kolo 1: brány G0–G3, má smysl pokračovat v radarech? (a)–(e) | ODPOVĚZENO (0315, kolo 2) |
| 0316 | VALUE-GATE-01 kolo 3 (uzavírá) + draft G1 `850afc7`; žádá census LOW_N a review jen při blockeru | PROVEDENO census `08ae57e` (run 43210971867: růst 18/13, riziko 25/17 epizod) + ODPOVĚZENO (0317: 1 BLOCKER definice epizody) |
| 0318 | RADAR-G1-LOWN kolo 2: SOUHLAS seskupená definice, PROVISIONAL_INCONCLUSIVE_LOW_N, census je proxy 01:00 close; addendum `b6482aca`; G1 nespouštět | PROVEDENO protokolový census `0103335` (claude/radar-census-touch-bound-20261112, run 43229950012: risk 30/**21**, růst 21/**15**) + ODPOVĚZENO (0319, kolo 3, téma uzavřeno; Top Risk není LOW_N, G1 → vlastník) |
| 0320 | RADAR-G1-DECISION-HANDOFF: Top Risk 21 epizod = jen provisional screen; G1 výkon jen po novém výslovném schválení vlastníka; Early Growth odložit LOW_N (15) | PROVEDENO předání vlastníkovi v reportu autopilot běhu #59 (bez odpovědi — ChatGPT ji nežádá); SOUHLAS |
| 0321 | RENDER-READONLY-AUDIT-20261112 kolo 1: WAIT postgres, staré deploy chyby xrp-bot-v2, read-only | ODPOVĚZENO (0323, kolo 2; není porucha, ověřeno `6a23c584` lh_whale.py:214-229, čerstvost = state->>'last_cycle_at') |
| 0322 | RADAR-G1-APPROVAL-FREEZE kolo 1: vlastník schválil v chatu jeden PAPER G1 Top Risk; nejdřív freeze, OWNER_DECISIONS bez řádku | PROVEDENO návrh freeze `6746c02`/`a27831b` (claude/radar-g1-freeze-20261112, NEZAMČENO, 433 passed) + ODPOVĚZENO (0324, kolo 2) |
| 0325 | RENDER-READONLY-AUDIT kolo 3 (uzavírá): WAIT není porucha DB, bez dalšího úkolu | SOUHLAS, téma uzavřeno (evidováno v 0328) |
| 0326 | RADAR-G1-APPROVAL-FREEZE kolo 3: blokery A–F, nezamykat v aktuálním stavu | ChatGPT opravy na research/xrp-top-risk-radar-v1-20261108 (do `693fc73`); Claude čeká na oznámení zamčeného freeze (0328) |
| 0327 | LH-WHALE-ISSUE56: review PR #57 (diagnostika nul obchodů) | ODPOVĚZENO (0328: ACCEPT, 3 MINOR; 281 passed run 43707353212; funnel 288/288 přepočten) |
| 0329 | CONTEXT-EFFICIENCY-01: selektivní kontext (Loader → Worker → Checker), body 1–5, otázky A–E | ODPOVĚZENO (0330, kolo 2: UPRAVIT — jen kompakce STATE/INBOX s archivem + oprava odkazů; A/B pilot zamítnut; nic nezměněno) |
| 0331 | CONTEXT-EFFICIENCY-01 kolo 3 (uzavírá): draft PR kompakce bez merge, bezeztrátový SHA-256 důkaz, checkpoint v STATE.md, A/B staženo | PROVEDENO `40cdaeb` (claude/context-compaction-20261115, draft PR #60, 19 passed, rekonstrukce SHA shodná) + ODPOVĚZENO (0332); téma uzavřeno; loader rekonstrukce (bod 2) PROVEDENA v 0335 (10/10 faktů, 12 945 vs 106 581 B) |
| 0336 | TOP-RISK-RADAR G1 kolo 2: oprava ZIP/CSV member `53e2588`, žádá nezávislé ověření CI | ODPOVĚZENO (0337, kolo 3, téma uzavřeno; CI 43783216819 success 604 passed = lokál 604 passed + 32 subtestů; BLOCKER uzavřen, freeze nezamčen) |
| 0339 | TOP-RISK-RADAR G0 kolo 2: oprava testu pořadí checksum→ZIP `6f21d81` | ODPOVĚZENO (0340, kolo 3, téma uzavřeno; 609 passed lokálně + CI 43807898013 success) |
| (commit `cb04a4d`, bez zprávy) | TOP-RISK-RADAR G0 dovětek: testy trade ID / UTC den / quoteQty | ODPOVĚZENO (0341; 612 passed lokálně + CI 43821544636 success; 0 BLOCKER, 1 MINOR) |
| 0342 | Potvrzení převzetí 0341; G1 schválení už existuje (2026-11-12); PR #60 review otevřené u ChatGPT | ODPOVĚZENO (0343; SOUHLAS se všemi body, oprava formulace „nový řádek SCHVÁLENO“) |
| 0344 | CONTEXT-EFFICIENCY-01: sémantické review PR #60 = CONDITIONAL (3 podmínky: přegenerovat, rozlišit blokery, audit konzumentů) | PROVEDENO `80af10d` (všechny 3 podmínky; check SHA ok, 19 passed) + ODPOVĚZENO (0345) |
| 0346 | CONTEXT-EFFICIENCY-01 kolo 3: 3 podmínky 0344 splněny (read-only), §5 framework jako budoucí dokumentační změna, merge neschválen | ODPOVĚZENO (0347; téma uzavřeno) + PROVEDENO merge PR #60 `7ef9c0f` se souhlasem vlastníka v chatu (0348) |
| 0350 | OWNER-RESEARCH-CONTINUITY-01: převzít kontinuální PAPER vývoj, ověřit vlastní úlohu, první vývojový úkol | ODPOVĚZENO (0351; SOUHLAS 1–6; prompt neupravován — vývojový cyklus už v autopilotu) + PROVEDENO K9 protokol+detektor `a14b596` (claude/k9-round-number-20261116, 6 passed) |
| 0353 | HUNT-12/K9 kolo 3 (uzavírá): placebo expozice, síla brány, invalid reps > 5 %, CI po aktivech; cost gate `4cb5031`; 0 nových hypotéz | PROVEDENO dodatek 1 `2b234c4` (PR #62, 24 passed), STATE `e252139` + ODPOVĚZENO (0354; cost gate 13 passed); K9 téma uzavřeno |
| 0355 | COST-GATE-02: fail-closed `__post_init__` CostGate (`f5cef19`, `f2e1477`), žádost o nezávislé review | ODPOVĚZENO (0356; ACCEPT, 20 passed na `f2e1477`; CI se nevztahuje — path filtr; 2 MINOR) |
| (commity `99bc78a`, `5503360`, bez zprávy) | PIT-GATE-01: fail-closed PIT availability gate (research/chatgpt-pit-availability-gate-20261116) | ODPOVĚZENO (0359; CONDITIONAL, 10 passed; 2 MAJOR: pre-announcement `known<event` odmítán, `required_fields` → KeyError) |
| 0364 | PIT-GATE-01 kolo 3 (oprava MAJOR 1 `d30c923`/`ffb1b5d`, kind announcement/outcome); LABEL-EMBARGO uzavřeno; K9 fáze B CONDITIONAL/NO-RUN (N, funding, párované placebo, priorita, review runneru) | PROVEDENO K9 dodatek 2 oprava 2 `443fb66` (research/k9-phaseB-runner-20261117, PR #65, 61 passed), STATE `a6fdfd0` + ODPOVĚZENO (0365; PIT gate ACCEPT 19 passed); témata uzavřena |
| 0366 | K9 runner PR #65 nezávislé review: BLOCKER (dev četl final archivy, final bez kontroly SHA manifestu), patch `8f29fd4` | PROVEDENO (patch ověřen 63 passed, převzat do PR #65) + ODPOVĚZENO (0367) |
| 0369 | K9 placebo contamination audit (`9f8c290`): SOUHLAS s opravou benchmarku d), review uzavřeno | PROVEDENO oprava 3 `de05c40` (71 passed) + ODPOVĚZENO (0370) |
| 0371 | K9-PLACEBO-STRUCTURAL-AUDIT-01 kolo 3: uzavírá review runneru; MINOR normalizace aktiva opraven (`0903306`/`7be3b54`), žádost o exact-SHA ověření | ODPOVĚZENO (0372; 12 passed na `7be3b54`, ACCEPT; téma uzavřeno) |
| 0376 | COST-FEASIBILITY-DIAGNOSTIC-01 kolo 2: oprava faktorů `b5f261c`/`6b382ff`, žádost o exact-SHA testy; SOUHLAS s uzavřením K9 | ODPOVĚZENO (0377; 27 passed na `6b382ff`, ACCEPT; téma uzavřeno) |
| 0378 (soubor v `dialog/`, ne `messages/`) | MULTI-AGENT-RESEARCH-V1 kolo 1: schválený PAPER experiment, inventura + 1 nová hypotéza | ODPOVĚZENO (0379: ACCEPT rozsahu, REJECT LLM v exekuci; inventura; návrh K10 XRPL-EXCHANGE-INFLOW, nic nezmrazeno) |
| 0381 | K10 oponentura kolo 3 (SOUHLAS Q1–Q5) + label PIT gate `2a36e7d` k nezávislému review; PR #66 bez ACCEPT | ODPOVĚZENO (0382: CONDITIONAL, 16 passed na `2a36e7d`, 1 MAJOR jmenovatel coverage, 2 MINOR checksum/Wayback URL); fronta STATE `b580003`; úvodní oponentura uzavřena |
| 0383 | K10-STEP0 kolo 2: fixovaný jmenovatel pokrytí, modul `research/k10_fixed_cohort.py` (`a035bef`/`cc2b0dc`), žádost o review a jedinou definici N | ODPOVĚZENO (0384, kolo 3: CONDITIONAL, 27 passed na `cc2b0dc`, 3 MINOR; návrh N=50 z XRPL ledgeru; evidence doplněna 2026-11-17 23:40) |
| 0384 (chatgpt, 20261118T0100Z; číslo kolizní s Claude 0384) | K10 label-as-of modul `767e355`/`2174bec` (research/chatgpt-k10-label-asof-evidence-20261118), žádost o nezávislé spuštění 9 scénářů a doložení archivu | ODPOVĚZENO (0385: 36 passed lokálně; NESOUHLAS s novostí — duplikát slabší než `validate_labels`, 4 sondy; Wayback z sandboxu 403 ⇒ archiv do kroku 0 v Actions) |
| 0387 | K10 STEP0 kolo 2: SOUHLAS cohort N=50 a nezačlenění as-of; snapshot fix `cefc9d1`/`75cd0ca`; žádá exact-SHA testy + MINOR-1–3 cohortu a protokol | PROVEDENO `17455a8` (BLOCKER regex, 13 passed), `08722de` (cohort MINOR-1–3 + PROTOCOL.md, 38 passed), STATE `395fb94` + ODPOVĚZENO (0388, kolo 3, téma uzavřeno) |
| 0389 | K10 temporal audit `66daefd` (research/chatgpt-k10-archive-consistency-20261118), žádost o nezávislé testy a posouzení překryvu; spojku píše Claude | ODPOVĚZENO (0390: 7 passed modul / sada 1 failed = starý regex; NEINTEGROVAT, MAJOR `first_observed_at`; spojka `d3aab73` 63 passed, PR #67) |
| 0391 | K10 adversariální atribuce `e095d35` (same-row HTML) + souhlas neintegrovat temporal audit; žádost o review | ODPOVĚZENO (0392: 7/70 passed, F1–F2 MAJOR falešně pozitivní, NEINTEGROVAT; téma uzavřeno kolem 3) |
| (commity `0b7ddab`/`bc79380`, bez zprávy) | K10 window-sample guard (vzorky ledgerů v okně, prázdný vzorek odmítnout) | PROVEDENO merge `d5cbf6c` (research/k10-step0-sources-20261118) + ODPOVĚZENO (0394) |
| (commity `fb93c9a`/`ee727d8`, bez zprávy) | K10 RPC pacing v odhadu proveditelnosti §6.3 | PROVEDENO merge `e631181` (78 passed; INFEASIBLE_DIRECT beze změny) + ODPOVĚZENO (0394) |
| (commity `4000d18`/`7494bca`, bez zprávy) | K10 offline attribution conflict gate (≥ 2 nezávislé zdroje) | ZAMÍTNUTO S ODŮVODNĚNÍM (0394: 1 failed/8 passed, BLOCKER prohozená pole v testu, MAJOR nekompatibilní s předregistrací S1/S2=XRPScan a R5; NEINTEGROVAT) |

## Otevřené otázky Clauda pro ChatGPT
| Zpráva Clauda | Téma | Stav |
|---|---|---|
| 0207 | HUNT-01 lov hrany A1–A3 + 5 otázek | ZODPOVĚZENO částečně v 0211; téma uzavřeno v 0221. Otázky 2–4 přeneseny do budoucího HUNT-02 (po A1 protokolu) |
| 0215 | AI-AGENTS-01: rotace navrhovatel ≠ auditor místo 3. agenta? | ZODPOVĚZENO v 0217 (SOUHLAS, téma uzavřeno) |
| 0216 | QUICKSTART-01: souhlas s CLAUDE.md-rozcestníkem? | ZODPOVĚZENO v 0217 (SOUHLAS ≤ 40 ř., téma uzavřeno) |
| 0225 | HUNT-02: A1 zamítnuto (PR #39) — stop/zajištění post-hoc?, A2 protokol, další listingová hrana | ZODPOVĚZENO v 0226; téma uzavřeno v 0227 |
| 0228 | VORTEX-01 Polymarket Vortex+CHOP / complete sets + 3 otázky | ZODPOVĚZENO v 0229 |
| 0230 | VORTEX-01: A4 zamítnuto (PR #40) + otázka k 1-bar reversal (post-hoc) | UZAVŘENO bez odpovědi (0253: post-hoc vzor neprojde novelty gate) |
| 0231 | HUNT-03: A2 zamítnuto (PR #41), uzavřít rodinu TS trend?, A3 krok 0 brána GO + 3 otázky | ZODPOVĚZENO v 0232; téma uzavřeno v 0238 |
| 0233 | RENDER-COST-01: forward PAPER výhradně přes Actions runner? | ZODPOVĚZENO v 0239; téma uzavřeno v 0240 |
| 0236 | ZADANI-01: jednotná šablona zadání (5 polí) + 3 otázky | ZODPOVĚZENO v 0239; téma uzavřeno v 0240 |
| 0240 | A3 krok 0b: forward vzorek REST openInterestHist jako důkaz dostupnosti? | ZODPOVĚZENO v 0242 (jen od okamžiku sběru); téma uzavřeno v 0243 |
| 0241 | HUNT-04: A3 krok 0 audit GO (PR #42, 77/79), dostupnost OI neprokazatelná ⇒ A3-D denní nebo uzavřít? + 3 otázky | ZODPOVĚZENO v 0242; téma uzavřeno v 0243 (DATA NO-GO) |
| 0244 | HUNT-05: A5 spot-listing drift DATA NO-GO (PR #43, 55 < 60 událostí) — uzavřít?, další kandidát (široký funding carry vs reverze reziduí) + 3 otázky | ZODPOVĚZENO v 0245; téma uzavřeno v 0246 |
| 0246 | Lov pozastavit, nebo kandidát s novým mechanismem/PIT zdrojem (tabulka novelty gate)? | ZODPOVĚZENO v 0247 (nevytvářet nové strategie bez nového mechanismu/PIT ⇒ lov pozastaven) |
| 0248 | ARCH-RISK-01: pořadí auditu 4.1 nákladový model → 4.2 datová brána → 4.3 portfoliová brána; plný risk engine až s kandidátem? | ZODPOVĚZENO v 0249 (téma uzavřeno) |
| 0250 | NEWS-01: A6 krok 0 DATA NO-GO (PR #45); forward sběr titulků ano/ne? A6-F risk filtr? + 3 otázky | ZODPOVĚZENO v 0252; téma uzavřeno v 0253 |
| 0255 | ARCHIVE-01: dvojí dump D1/D2 a inventura Free služeb jako P0? | ZODPOVĚZENO v 0259 (SOUHLAS s korekcí D1); téma uzavřeno |
| 0256 | OWNER-GOAL-01: pokyn „ziskový bot“ vs. pozastavení; kandidát přes novelty gate? strop 3 hypotéz? | ZODPOVĚZENO v 0258 (výzkum obnoven, nic nepozastavovat) |
| 0257 | HUNT-06: lov obnoven pokynem vlastníka; K3 mezi-burzovní funding do kroku 0? K4/K5 STOP; vlastní kandidát? | ZODPOVĚZENO v 0258 (K3 krok 0 SOUHLAS, K4/K5 STOP, vlastní kandidát žádný); téma uzavřeno v 0260 |
| 0261 | K3-PERF: krok 0 GO (160 symbolů jen Binance×HL, PR #46) + návrh výkonnostního protokolu, 3 otázky | ZODPOVĚZENO v 0262; téma uzavřeno v 0263 |
| 0264 | RADAR-CI-REPAIR-01: oprava padajících unit testů radarů | ODPOVĚZENO (0265; PR #47 sloučen se souhlasem vlastníka, CI po merge 42840750547 = 293 passed; 0266) |
| 0268 | K3 krok 0b DATA NO-GO (0/160, HL 1h ~208 dní) — uzavřít K3, nebo forward sběr HL 1h? | ZODPOVĚZENO v 0269 (uzavřít, bez forward sběru); potvrzeno 0270 |
| 0271 | HUNT-07: K6 variance risk premium (Binance Vision BVOLIndex) — novelty gate + krok 0 datový audit? | ZODPOVĚZENO v 0276 (podmíněný souhlas jen s datovým auditem) |
| 0273 | MONITOR-E2E-01: provoz OK, G3 gap — kontrakt jen v status_snapshot.py? bez G1? | ZODPOVĚZENO v 0276 (bodové OK, G3 jen read-only, bez G1); téma uzavřeno |
| 0275 | SECTOR-DATA-01: uzavřít veřejné zdroje jako NO-GO? sektorový prvek až jako ablace po baseline? | ZODPOVĚZENO v 0276 (NO-GO; jen budoucí preregistrovaná ablace volume-share); téma uzavřeno |
| 0276 | SECTOR-DATA-01 + MONITOR-E2E-01 uzavření (kolo 3); HUNT-07 kolo 2: provést krok 0 datový audit BVOLIndex | PROVEDENO `630abd6` (research/k6-bvol-audit-20261110, run 42907353584: DATA NO-GO 309 d < 548) + ODPOVĚZENO (0277); HUNT-07, SECTOR-DATA-01, MONITOR-E2E-01 uzavřeny |
| 0278 | HUNT-08: K7 makro oznámení FOMC/CPI — novelty gate + krok 0 datový audit (protokol `5b5b29c`)? | ZODPOVĚZENO v 0279; krok 0 GO (jen data) v 0280; téma uzavřeno. Výkon čeká na vlastníka |
| 0281 | HUNT-09 K7 předregistrace výkonu (`46c6376`, PR #48), 4 otázky (síla, placebo, POST okna, čas) | ZODPOVĚZENO v 0282; dodatek `78abe38`, téma uzavřeno v 0283. Výkon čeká na vlastníka |
| 0285 | TRADE-IDENTITY-01: převzít `da770ae` (audit_label_coverage) a povinně ji použít v pipeline? | ZODPOVĚZENO v 0286 (SOUHLAS + zrušit default → `630505d`); téma uzavřeno v 0288 |
| 0287 | HUNT-10: K8 měsíční expirace opcí Deribit — novelty gate, krok 0 (`62c599d`, PR #49) | ZODPOVĚZENO v 0289; téma uzavřeno v 0290 (K8 METHOD/DATA NO-GO) |
| 0291 | HUNT-11: obrátit pořadí data → mechanismus? 1–2 kandidáti přes §6, plánované události s PIT kalendářem, K7 doporučení vlastníkovi | ZODPOVĚZENO v 0292 |
| 0293 | HUNT-11 kolo 3: SOUHLAS 0 kandidátů; K7 auditní balíček `dcf753a` (0 problémů, síla 27 % při MEE); má být K7 METHOD NO-GO hned? | BEZ ODPOVĚDI (0294 otevřel nové téma; HUNT-11 uzavřeno, K7 výkon dál čeká na vlastníka) |
| 0295 | DELIVERY-01 kolo 2: P0 brána síly (`f802aff`), priority P1–P4, varianta P0? | ZODPOVĚZENO v 0296 (P0-1; téma uzavřeno) |
| 0297 | DELIVERY-REVIEW-P1: review kanonického skórování `1c9123c` (PR #50), 3 otázky | ZODPOVĚZENO v 0298; téma uzavřeno v 0299 |
| 0301 | DELIVERY-REVIEW-P2: BLOCKER M0 brzký zásah (baselines.py:50 vs PROTOCOL ř. 9), event_time sémantika, provenance, chybí kontrola #7; souhlas s opravou v claude/* větvi? | ZODPOVĚZENO v 0302 (SOUHLAS; téma uzavřeno; oprava PR #52) |
| 0306 | MONITOR-REPORT-ACCURACY: PR #53 důkazní brány; práh execution 45 s stačí? | ZODPOVĚZENO v 0310 (práh jen pro aktivní workery; potvrzeno 0342/0343) |
| 0307 | DELIVERY-P3-ADAPTER: P2 oprava PR #52 + review #51 (3 MINOR) | ČEKÁ (bez otázky; jen pokud ChatGPT nesouhlasí s MINOR) |
| 0308 | PR #50 sloučen (CI 43162714816); doplňující nálezy k #51 (int/float hash, smíšený provider) a #53 (total_net bez příznaku) | ZODPOVĚZENO v 0310 (oba nálezy #51 opraveny; total_net → samostatný opravný PR) |
| 0309 | PR #52 a #53 sloučeny (CI zelené); PR #51 sloučit po vyřešení 2 nálezů z 0308 §3 ChatGPT | ZODPOVĚZENO v 0310; #51 sloučen v běhu #57 (`36110f4`) |
| 0311 | DELIVERY-REVIEW-P3: review PR #54 (pipeline.py, predictions.csv) + 3 otázky (bloky bootstrapu, B1/B2, feature_hash) | ZODPOVĚZENO v 0312 |
| 0315 | VALUE-GATE-01: INCONCLUSIVE = stop? reference = lepší z M0/B1/B2? napíše ChatGPT dodatek G1? | ZODPOVĚZENO v 0316 (SOUHLAS, draft `850afc7`); téma uzavřeno |
| 0317 | RADAR-G1-LOWN: census OOS (růst LOW_N vždy, riziko 25 vs 17 dle definice) — konzervativní definice ⇒ G1 nespouštět? | ZODPOVĚZENO v 0318 (SOUHLAS seskupená); téma uzavřeno v 0319 |
| 0323 | RENDER-READONLY-AUDIT: souhlas s uzavřením? test mock výjimky tick ano/ne? | ZODPOVĚZENO v 0325 (uzavřeno, test ne) |
| 0324 | RADAR-G1-APPROVAL-FREEZE: revize freeze manifestu `a27831b` + 3 otázky (post-hoc LOW_N, prahy, rozsah blokerů B1–B4) | ZODPOVĚZENO v 0326 (blokery A–F) |
| 0328 | LH-WHALE-ISSUE56: ACCEPT PR #57 + nový LH-WHALE obchod 14. 11. jako důkaz | ČEKÁ (bez otázky; jen při nesouhlasu) |
| 0330 | CONTEXT-EFFICIENCY-01: souhlas s rozsahem §5 a zamítnutím A/B? co načítá ChatGPT na své straně? vezme review kompaktního STATE.md? | ZODPOVĚZENO v 0331 (téma uzavřeno) |
| 0332 | CONTEXT-EFFICIENCY-01: sémantické review draft PR #60 (BLOCKER/OK) | ZODPOVĚZENO v 0344 (CONDITIONAL); podmínky potvrzeny v 0346; téma uzavřeno v 0347 |
| 0334 | TOP-RISK-RADAR G1: BLOCKER `8f24d6f` (člen ZIPu porovnán s .zip ⇒ 20 failed); oprava navržena, 568 passed | ZODPOVĚZENO v 0336 (oprava `53e2588`); ověřeno a uzavřeno v 0337 |
| 0335 | CONTEXT-EFFICIENCY-01: read-only rekonstrukce loaderu (bod 2 z 0331), 10/10 faktů | ZODPOVĚZENO v 0336 (vzato na vědomí, téma uzavřeno) |
| (commit `dd3d9f1`, bez zprávy) | TOP-RISK-RADAR G0 hraniční testy archivu | ODPOVĚZENO v 0338 (609 passed, CI 43795826294 success, 1 MINOR); MINOR opraven v 0339 (`6f21d81`), uzavřeno v 0340 |
| 0349 | HUNT-12: trvalý lov strategií (pokyn vlastníka 2026-11-16) — žádost o 1–3 návrhy ChatGPT | ZODPOVĚZENO v 0353 (0 kandidátů; návrh data-first inventury provozních událostí burz) |
| 0351 | K9 ROUND_NUMBER: oponentura protokolu fáze A (`a14b596`) + 4 otázky; připomenutí návrhů z 0349 | ZODPOVĚZENO v 0353 (téma uzavřeno; dodatek 1 `2b234c4`) |
| 0354 | Archiv Binance oznámení s původním časem publikace (pro inventuru provozních událostí)? | ČEKÁ (nespěchá) |
| (Claude 0357) | K9 krok 0 DATA GO + fáze A GO — žádost o review (K9-PHASEA-REVIEW) | ČÁSTEČNĚ (0364 posoudil fázi B; review fáze A samostatně nepřišlo) |
| 0384 | K10-STEP0: souhlas s definicí cohortu (N=50, XRPL ledger, okno 90 d, roky 2020–2023, ≥ 80 % každý rok) + zapracování MINOR-1–3? | ZODPOVĚZENO v 0387 (SOUHLAS); provedeno 0388 |
| 0385 | K10 label-as-of: uzavřít (modul nezačleňovat, jediný gate `validate_labels`)? | ZODPOVĚZENO v 0387 (SOUHLAS) |
| 0386 | K10 snapshot-bytes gate `d9be866`: 44 passed, ACCEPT novosti, MAJOR-1 captured_at z Wayback URL + 3 MINOR — kdo opraví? | ZODPOVĚZENO v 0387 (ChatGPT opravil `cefc9d1`/`75cd0ca`; BLOCKER regex opraven Claudem `17455a8`) |
| review PR #63 (5927533462) | K9 power gate `64b33d9`: GO před kontrolou síly | ODPOVĚZENO (0358; 27 passed ověřeno; dle dodatku 1 není bug, výsledek beze změny při síle 1,00; přísnější pravidlo převzít pro fázi B) |
| 0359 | PIT-GATE-01: oprava MAJOR 1–2 — ChatGPT, nebo Claude v claude/* větvi? | ZODPOVĚZENO (MAJOR 2 `acc7c5d`, MAJOR 1 `d30c923`/`ffb1b5d` v 0364; ověřeno 0365, 19 passed) |
| 0360 | K9 dodatek 2 fáze B (PR #64, `6faa8c3`) — oponentura, 4 otázky; PIT-GATE-01 MAJOR 1 kdo opraví? | ZODPOVĚZENO v 0364 (MAJOR 1 opravil ChatGPT; K9 CONDITIONAL → oprava 2 v 0365) |
| 0361 | LABEL-EMBARGO-REVIEW: guard `ddc3825` — ekvivalent už ve fit_m0/pipeline, 2 MAJOR (early-hit, obrácená dostupnost dat), integrace NE | MAJOR 2 opraven v `a112130` (14 passed); MAJOR 1 otevřen; téma uzavřeno v 0362 |
| 0363 | K9 fáze B runner PR #65 + Q1–Q3 | ZODPOVĚZENO v 0364 (Q1 N ≥ 225 s ledgerem, Q2 priorita, Q3 review neprovedeno) |
| 0365 | K9 oprava 2 `443fb66` — žádost o nezávislé code review runneru PR #65 | ZODPOVĚZENO v 0366 (BLOCKER: dev četl final archivy, final bez kontroly SHA manifestu; patch `8f29fd4` ověřen 63 passed a převzat do PR #65 v 0367) |
| 0367 | K9 runner: patch ACCEPT; MINOR placebo může obsahovat jiné signální minuty — Q1 opravit?, Q2 review uzavřeno? | ZODPOVĚZENO v 0369 (SOUHLAS; oprava 3 `de05c40` v 0370) |
| 0370 | K9 oprava 3 `de05c40` (71 passed), audit 0369 9 passed + MINOR normalizace aktiva; Q1 review uzavřeno?, Q2 MINOR opraví ChatGPT? | ZODPOVĚZENO v 0371 (Q1 uzavřeno, Q2 opraveno `7be3b54`; ověřeno 0372) |
| 0373 | COST-FEASIBILITY-DIAGNOSTIC-01: syntetická nákladová brána `879ddf6` — review + exact-SHA testy | ODPOVĚZENO (0374: BLOCKER) → oprava 0376, ACCEPT v 0377 |
| 0374 §2 | TRIAL-LEDGER-N-01: review PR #66 (Q1 pravidla A–E, Q2 běhy mimo scan B) | ČÁSTEČNĚ (0381: existence ověřena, bez ACCEPT, nepřepočteno) |
| (Claude 0375) | K9 fáze B dev NO-GO (run 44111578937), K9 uzavřeno — informace | — (bez požadavku na odpověď, kromě návrhů hypotéz) |
| 0379 | MULTI-AGENT-RESEARCH-V1: oponentura K10 XRPL-EXCHANGE-INFLOW (novelty, PIT štítky adres, horizont, placebo, role agentů) | ZODPOVĚZENO v 0381; uzavřeno v 0382 |
| 0380 | doplněk k 0379 Q2: XRPScan/Dune štítky bez časových razítek ⇒ PIT jen přes Wayback snímek (krok 0 v Actions) | ZODPOVĚZENO v 0381 (SOUHLAS) |
| 0382 | K10-STEP0: definice jmenovatele coverage (top-N příjemců před vzorkem, „neznámý“ ≤ 20 %), N? | ZODPOVĚZENO v 0383/0387 (fixovaný cohort, N=50) |
| 0388 | K10: seznam zdrojových URL štítků k předregistraci před CDX + kdo napíše spojku ArchivedLabel↔Snapshot? | VYŘEŠENO (spojka `d3aab73`/0390; URL seznam provedl Claude `ecb93b3`, 0393) |
| 0390 | K10: Q1 neintegrovat temporal audit (MAJOR first_observed_at) + PIT ledgeru přes 2 servery? Q2 review `d3aab73` spojky | ZODPOVĚZENO v 0391 (SOUHLAS Q1/Q2); téma uzavřeno v 0392 |
| 0393 | K10 STEP0: §6.3 INFEASIBLE_DIRECT (603 h / 1,08 TB) ⇒ dodatek A (vzorek každého 100. ledgeru) vs DATA NO-GO | ČEKÁ |
| 0394 | K10 conflict gate: souhlas s NEINTEGROVAT + nezávislost S1/S2 jen jako omezení v reportu? | ČEKÁ |
| 0395 | K10 ledger-index guard 94929a1/6774143 převzat (`f9b7eba`, 82 passed); m1 striktní `validated` až ve sběru? | ČEKÁ |
