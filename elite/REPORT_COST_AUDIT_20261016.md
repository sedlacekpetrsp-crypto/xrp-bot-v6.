# ELITE: audit nákladů zmrazených strategií,16.10.2026

Snížení nákladů samo nezajistí splnění původních podmínek ani V18, ani V49.
V18 překračuje limit propadu i bez nákladů. V49 má i bez nákladů PF pod1,2
a zápornou dolní mez denního bootstrapu. Žádný kandidát pro PAPER ani nasazení.

## Co bylo provedeno

Beze změny signálů a rizika znovu otestovány V18 a V49 na původních4 blocích
(duben2023–září2026) a souvislém období při6 úrovních nákladů:0;25;50;75;100;200 %.
Celkem60 simulací. Výběr těchto dvou strategií vychází z jejich již známých
výsledků, nejde o nezávislé ověření. Neproběhl výběr nových parametrů strategie.

100 % odpovídá na stranu fee0,10 %,skluz0,03 %,halfspread0,01 %. Násobek
škáluje všechny tři složky. Nižší sazby jsou hypotetické, nedoložené pro
konkrétní účet či burzu. Nulové náklady nejsou reálné provedení.
Účet10 000 USDT,spot LONG bez páky,riziko0,5 %,alokace35 % beze změny.
Kód a protokol zmrazeny v commitu `88414154d58ddea5981b05f54507201d0f751337`.

## Souvislé výsledky

| Násobek nákladů | V18 výnos | V18 DD | V18 kladné bloky | V49 výnos | V49 DD | V49 kladné bloky |
|---|---:|---:|---:|---:|---:|---:|
| 0 % | +59,46 % | 10,52 % | 3/4 | +23,61 % | 9,62 % | 4/4 |
| 25 % | +56,13 % | 10,69 % | 3/4 | +12,59 % | 11,74 % | 3/4 |
| 50 % | +52,93 % | 10,85 % | 3/4 | +2,82 % | 13,69 % | 2/4 |
| 75 % | +49,96 % | 11,01 % | 3/4 | −5,92 % | 15,92 % | 2/4 |
| 100 % | +47,18 % | 11,15 % | 3/4 | −14,19 % | 20,17 % | 1/4 |
| 200 % | +35,63 % | 11,68 % | 2/4 | −36,27 % | 37,75 % | 0/4 |

V18 má97 obchodů při každé úrovni, V49 má541. Stejný počet neznamená
identické účetní cesty: náklady mění velikosti pozic, fill a stop/target úrovně.
Čisté výnosy proto nejsou výsledkem prostého odečtení pevného součtu poplatků.

U V49 je výnos kladný při50 % nákladů a záporný při75 %. To vymezuje pouze
rozmezí testovaných scénářů, nikoli přesně odhadnutou dosažitelnou sazbu.
Není provedena interpolace ani důkaz monotónnosti mezi body. Při50 % navíc
strategie nesplňuje DD10 %,3/4 kladné bloky ani PF1,2 (PF1,024).

Bez nákladů V49 dosahuje PF1,19468, stále pod pevnou hranicí1,2; denní95%
interval [−0,307; +4,048] USDT obsahuje nulu. Ani tento ideální scénář tedy
nesplňuje původní kritéria. PF nebyl zaokrouhlen na průchod.
V18 má bez nákladů DD10,522 %, takže ani tam nevzniká průchod.

## Dopad na další vývoj

Není odůvodněné zachraňovat tyto varianty předpokladem nulového skluzu,
automatického maker plnění nebo zvýšením rizika. Každý skutečně odlišný
způsob provedení potřebuje vlastní model plnění a důkazy; tento audit jej
neimplementoval. V18 potřebuje řešit profil ztrát a stabilitu, V49 kromě
nákladové rezervy také slabší stabilitu a nejistotu výhody.

## Kontroly a reprodukce

Všech60 ledgerů účetně smířeno, bez překrývajících se pozic. Scénáře100 %
a200 % u obou kandidátů přesně odpovídají starým základním a stresovým
metrikám, ve všech4 blocích i souvisle (`control_checks.json`).
118 stávajících testů prošlo.
[GitHub CI](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38851545052)
zopakoval testy a audit. Úspěšný výpočet neznamená přijatou strategii.

Evidence `results/20261016_cost_audit`: souhrn s datovými manifesty a hashi,
`evidence.tar.gz` s úplnými obchody a denní equity všech60 simulací,
`control_checks.json`. Spuštění:
`python -m elite.cost_audit --cache CACHE --out OUT`.

Všechna období již prohlédnutá vývojová; intervaly nejsou korigované na
výběr po50 verzích. Rok2022 ani2021 nebyl v auditu otevřen. Původní brány
beze změny; ostatní boty a jejich provoz nebyly dotčeny.
