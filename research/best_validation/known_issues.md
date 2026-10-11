# Evidence chyb a podmínky přijetí

| Riziko / předchozí chyba | Důkaz / současný stav | Podmínka před nasazením kandidáta |
|---|---|---|
| Dvojí uzavření stejné pozice | FLY byl dříve opravován; sekvenční dvojí close BEST testován | Navíc atomické/idempotentní vypořádání s testem pádu a souběhu; současný offline test toto neprokazuje |
| Chybějící DATABASE_URL a ztráta historie | Historicky více botů; BEST nyní hlásí Postgres | Reálný DB restart a porucha zápisu, blokace nových vstupů při neuloženém stavu |
| Neviditelná otevřená pozice / zaměněné statistiky | Dřívější UI incidenty a nula pouze u EMA 4h | Oddělené účty, otevřené pozice i celkové a dílčí statistiky |
| Dvě karty pro stejný Hunter | Dřívější chybná záměna služeb | Unikátní identita, verze a tabulky každého kandidáta |
| Staré ceny a nehotové svíčky | Whale opraven 10. 10.; BEST legacy čerstvost není ekvivalentně testována | Ověření stáří, mezer, NaN a ceny po všech filtrech |
| Vynechané společné kontroly rizika | Opraveno 11. 10.: obě části používají bestof_portfolio.entry_budget | Dva původní expectedFailure testy nyní procházejí, navíc limity po obnově a fail-closed testy |
| Náklady zahrnuté nesprávně / dvakrát | U historie BEST rozklad přesně sedí | PnL = hrubý pohyb − skluz − poplatky; test zachován |
| Zvýšení rizika širším SL | Výzkumná varianta upravuje velikost pozice | Peněžní riziko stejné nebo menší; test zachován |
| Filtr blokující všechny vstupy | Každá testovaná varianta má obchody | Počty kandidátů, blokací a obchodů součástí výsledků |
| Výběr vítěze podle známých dat | Dřívější OOS neúspěch; současná data již zkoumaná | Neoznačovat za čistý holdout; předem fixovat další test a budoucí PAPER okno |
| Přepis základní verze | Zmrazen produkční commit a samostatná výzkumná větev | Přesný diff, testy, oddělené nasazení a možnost návratu |

Prior assistant recollections are context, not independent verification. Items labelled historical come from retrieved conversation history; direct code defects above were inspected in the frozen source. This is an issue register, not a claim that all listed protections already work.
