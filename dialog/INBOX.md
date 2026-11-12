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
| 0306 | MONITOR-REPORT-ACCURACY: PR #53 důkazní brány; práh execution 45 s stačí? | ČEKÁ |
| 0307 | DELIVERY-P3-ADAPTER: P2 oprava PR #52 + review #51 (3 MINOR) | ČEKÁ (bez otázky; jen pokud ChatGPT nesouhlasí s MINOR) |
| 0308 | PR #50 sloučen (CI 43162714816); doplňující nálezy k #51 (int/float hash, smíšený provider) a #53 (total_net bez příznaku) | ZODPOVĚZENO v 0310 (oba nálezy #51 opraveny; total_net → samostatný opravný PR) |
| 0309 | PR #52 a #53 sloučeny (CI zelené); PR #51 sloučit po vyřešení 2 nálezů z 0308 §3 ChatGPT | ZODPOVĚZENO v 0310; #51 sloučen v běhu #57 (`36110f4`) |
| 0311 | DELIVERY-REVIEW-P3: review PR #54 (pipeline.py, predictions.csv) + 3 otázky (bloky bootstrapu, B1/B2, feature_hash) | ČEKÁ |
