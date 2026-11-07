# Koordinátor výzkumu — pilot v1 (PAPER)

Stav: [P] specifikace vytvořena, [N] implementace a testování, [S] žádný automatický agent ani běh zatím spuštěn.
Větev: research/agent-coordinator-pilot-20261107. Tento dokument nezavádí autonomní běh.

## Cíl
Zrychlit uzavírání existujících úkolů bez nárůstu počtu AI agentů, nákladů a neověřených tvrzení. Koordinátor neobchoduje a nemá oprávnění ke schvalování.

## Role a odpovědnosti
- Koordinátor (logická role, nikoliv nový placený agent): načte evidenci, zvolí JEDEN nejvyšší nezablokovaný úkol, přiřadí vlastníka, požaduje důkazy, hlídá blokace a stop podmínky.
- ChatGPT: nezávislá kritická oponentura, specifikace testů, posouzení dat, statistiky a exekuce.
- Claude: nezávislá oponentura, implementace v izolované větvi a doložení unit/diagnostických testů.
- Validátor: oddělený checklist; kontroluje reprodukovatelnost, SHA, původ dat, leakage, OOS, poplatky a skluz. Nesmí označit vlastní práci za nezávisle reprodukovanou.
- Vlastník: schvaluje výkonnostní běhy dle aktuálního OWNER_DECISIONS.md a jakékoli nasazení, merge či změny produkce.

## Prioritní fronta pro první pilot
1. #67 hourly_retest — manifest historických dat + SHA256 + syntetické unit testy. Dokud nejsou zdroj a zmrazené období ověřeny, BLOCKED pro performance.
2. #29 ELITE V60 — ověřit dostupnost a archivovat původní Actions artefakt před 2027-01-16; žádné opětovné spouštění výkonového testu.
3. Kontrola kvality historických dat, která blokuje již schválené výzkumy.
Nové hypotézy až po odstranění těchto překážek, s kontrolou registru 110 hypotéz.

## Protokol úkolu
Každý úkol má: id, výzkumnou větev, odpovědnou roli, stav TODO/IN_PROGRESS/BLOCKED/REVIEW/DONE, vstupní commit a zdroje, předem stanovené acceptance criteria, důkazy (commit SHA, soubory, přesný testovací příkaz, exit code, výsledky), otevřená rizika a next action.

Změna stavu DONE vyžaduje ověřitelný výstup. [N] navrženo, [P] provedeno, [S] skutečně spuštěno. Úspěch unit testů neznamená ziskovost. Shoda ChatGPT a Clauda neznamená nezávislou validaci.

## Pilotní acceptance criteria
- Jedna práce #67 projde TODO → REVIEW s manifestem, kontrolami gapů/duplicit a syntetickými unit testy v izolované větvi; doložené SHA a logy.
- Oponent uvede alespoň jednu reálnou slabinu, nebo doloží konkrétní kontrolní body bez vymyšlených problémů.
- Koordinátor nevyvolá opakované zprávy, neotevře znovu uzavřená témata, nepřekročí 3 kola na téma a nezmění žádnou produkční větev.
- Měřit počet dokončených ověřených úkolů, chyby a čas/náklady; nepřidávat další agenty bez doloženého přínosu.

## Bezpečnost
Pouze PAPER. Žádný LIVE, Render, deploy, merge, force push, tajné údaje ani úpravy OWNER_DECISIONS.md. Výkonnostní test jen v rozsahu skutečně schváleném vlastníkem a po splnění datových bran. Větev dialog/claude-chatgpt je pouze komunikační schránka; tento pilot se nenasazuje do workflow. Všechny další automatizace vyžadují samostatné ověření možností a schválení rozsahu.
