# Rozhodnutí vlastníka

Rozhoduje pouze vlastník. ChatGPT i Claude smějí za vlastníka zapisovat jeho výslovná rozhodnutí s citací a kontextem; nesmějí si schválení udělovat sami ani rozšiřovat jeho rozsah.

Formát řádku: `YYYY-MM-DD SCHVÁLENO|ZAMÍTNUTO: <co>`

## Čeká na rozhodnutí
- Sloučení pracovních větví `claude/kolo6-opravy-*` do PR větví — zatím NESCHVÁLENO.

## Rozhodnuto
2026-11-06 SCHVÁLENO: zápis výslovných rozhodnutí vlastníka do tohoto souboru za vlastníka oběma agenty (ChatGPT i Claude).
2026-11-06 SCHVÁLENO: výkonnost PAPER výzkumných strategií v izolovaných větvích podle předem stanovených protokolů a datových/validačních bran.
2026-11-06 SCHVÁLENO: výkonnost PR #29 — jako první nejvýše jeden zmrazený diagnostický běh s branami kola 10 a závěry Q11; finální období s vadnými daty zůstává NEROZHODNUTO, bez udělení KANDIDÁTA.

2026-11-06 23:42 SEČ POTVRZENO vlastníkem přímo v chatu s Claudem („Potvrzuji“): obě schválení zapsaná ChatGPT ve 22:12 (zápis rozhodnutí za vlastníka oběma agenty; výkonnost PAPER výzkumu v izolovaných větvích vč. PR #29 v uvedeném rozsahu) platí. Zapsal Claude na pokyn vlastníka. Produkce (deploy, merge, Render, LIVE) tím schválena NENÍ.

### Původ a rozsah rozhodnutí (zapsal ChatGPT za vlastníka)
V přímém Work chatu dne 2026-11-06:
- Po vysvětlení, že před výkonnostními testy potřebujeme výslovné schválení, vlastník odpověděl: „Ano máte to schváleno“.
- Na otázku „Povoluješ mi tam tvé rozhodnutí zapsat za tebe?“ vlastník odpověděl: „Ano oba můžete“.

Souhlas umožňuje PAPER výkonnostní testování; neodstraňuje technické datové blokace, nenahrazuje předregistraci a neopravňuje k ladění na finálních datech. PR #30 zůstává technicky odložený. Konkrétní běhy musí uvádět strategii, commit, protokol a skutečně spuštěné testy; souhlas sám není záznamem spuštění.
Žádné schválení LIVE, Render změn, produkčního nasazení, merge ani force push. Další rozhodnutí nelze vytvářet bez výslovného pokynu vlastníka.

2026-11-10 SCHVÁLENO: obnovení hledání PAPER strategií (ruší pozastavení vývoje nových strategií evidované v dialogu 0254).
### Původ a rozsah (zapsal Claude za vlastníka, chat s Claudem 2026-11-10)
- 07:17 SEČ: „schválil, protože si to navrhoval ty, ale pokud jsi schopný něco vyvíjet a přijít na to, tak to zase hrozit.“
- 07:19 SEČ: „Tak udělej vše proto aby jsi na to přišel a našel je“ (odpověď na sdělení Clauda, že ziskového bota spolehlivě vyvinout neumí).
Rozsah čtu úzce: hledání a předregistrace hypotéz a datové audity bez výkonnosti. Výkonnostní běh nové hypotézy až po
dalším výslovném řádku vlastníka (dnešní zákaz výkonnostních testů předaný přes ChatGPT jsem nepovažoval za zrušený).
Žádné schválení LIVE, změn produkce, nasazení, merge ani force push. Zálohy podle ARCHIVE-01 pokračují.

2026-11-10 SCHVÁLENO: sloučení PR #47 (oprava unit testů radarů, jen testy) do výzkumné větve `research/xrp-top-risk-radar-v1-20261108`.
### Původ a rozsah (zapsal Claude za vlastníka, chat s Claudem 2026-11-10 16:05 SEČ)
- Na otázku Clauda „Sloučit PR #47 do výzkumné větve radarů?“ vlastník odpověděl: „Souhlasím“.
Platí jen pro PR #47. Žádné schválení produkce, nasazení, LIVE, výkonnostních testů ani jiných sloučení.

2026-11-12 SCHVÁLENO: sloučení PR #50 (radar P1, kanonický skórovací kontrakt) do výzkumné větve `research/xrp-top-risk-radar-v1-20261108`.
### Původ a rozsah (zapsal Claude za vlastníka, chat s Claudem 2026-11-12 06:37 SEČ)
- Na sdělení Clauda „Na vaše rozhodnutí čeká sloučení PR #50“ vlastník odpověděl: „Ano sluč je a pokračuj v opravach“.
Čteno úzce: platí jen pro PR #50 a pro pokračování v izolovaných opravách. PR #51, #52, #53 tím schváleny NEJSOU.
Žádné schválení produkce, nasazení, LIVE ani výkonnostních testů.

2026-11-12 SCHVÁLENO: sloučení PR #52 (radar P2, oprava M0) do `research/xrp-top-risk-radar-v1-20261108` a PR #53 (důkazní brány monitoru) do `research/autopilot`; PR #51 (radar P3 adaptér) až poté, co ChatGPT zapracuje nebo se zdůvodněním odmítne dva nálezy z dialogu 0308 §3.
### Původ a rozsah (zapsal Claude za vlastníka, chat s Claudem 2026-11-12 06:48 SEČ)
- Claude položil: „1. Sloučit PR #52 a PR #53? 2. PR #51 doporučuji sloučit až poté, co ChatGPT zapracuje nebo odmítne oba nálezy.“ Vlastník: „Dobře proved číslo 1 i 2“.
Jen výzkumné větve. Žádné schválení produkce, nasazení, LIVE ani výkonnostních testů; žádná další sloučení.

2026-11-12 SCHVÁLENO: výkonnost radar V1 G1 — jediný předem definovaný historický PAPER test XRP Top Risk Radaru −20 % / 14 dní, až po zmrazení protokolu, dat, kódu a kritérií vyhodnocení. Bez merge, deploy, Render, LIVE a změn produkce.
### Původ a rozsah (zapsal ChatGPT na výslovný pokyn vlastníka)
- Vlastník dne 2026-11-12 v chatu uvedl: „Schvaluji jeden předem definovaný PAPER historický výkonnostní test XRP Top Risk Radaru −20 % / 14 dní. Nejprve zmrazte protokol, data a kritéria vyhodnocení; žádný merge, deploy ani LIVE.“
- Po vysvětlení, že je nutné zapsat toto schválení do `dialog/OWNER_DECISIONS.md`, vlastník výslovně potvrdil „Ano, Ano.“ Tím povolil právě tento zápis, nikoli rozšíření rozsahu testu.
- Před spuštěním je nutné uzavřít PIT/datové/validační blokery a neměnný G1 freeze manifest. Zápis není důkazem splnění těchto bran ani záznamem spuštění. Povolen je nejvýše jeden výkonový běh, bez opakování nebo ladění podle výsledků.
