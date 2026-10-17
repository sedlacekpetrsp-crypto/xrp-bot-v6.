# ELITE: audit stejně dlouhých půlroků — 15.10.2026

Změna směru výzkumu: po35 variantách doplňující audit beze změny vstupů,
výstupů nebo původních přijímacích podmínek. Žádný nový kandidát ani nasazení.
Kód a protokol uložené před výsledky v commitu
`afccea54e9bf124655345706e70d5d89e3afe1b5`.

## Společné srovnání říjen2023–září2026

Šest nepřekrývajících se půlroků, každý se samostatným účtem10000USDT.
Všechny strategie mají stejné hranice, včetně měsíců ztrát. Doplňkově je
zveřejněn i duben–září2023; V30/V31 zde mají inicializaci bez obchodů.
Kalendářní půlroky se mírně liší počtem dnů. Nejde o nezávislé OOS: celé
období bylo mnohokrát použito, vybraná šestice vznikla podle známých výsledků.

| Verze | Kladné půlroky | Kladné při2× nákladech | Nejhorší výnos bloku | Nejlepší výnos bloku | Nejvyšší MTM DD uvnitř bloku |
|---|---:|---:|---:|---:|---:|
| V5 | 4/6 | 4/6 | -2.15% | 37.01% | 8.89% |
| V18 | 5/6 | 4/6 | -2.34% | 22.51% | 8.52% |
| V22 | 4/6 | 4/6 | -2.40% | 22.51% | 8.52% |
| V28 | 5/6 | 5/6 | -1.97% | 5.51% | 4.26% |
| V30 | 4/6 | 4/6 | -2.55% | 6.05% | 4.18% |
| V31 | 4/6 | 3/6 | -0.88% | 6.05% | 4.16% |

Propady v tabulce patří resetovaným půlročním účtům. Nejsou náhradou
celého souvislého drawdownu: například V18 nadále měla11,15% v původním
souvislém testu. Reset účtu a uzavření pozic na hranici mění následné obchody.

## Úplné blokové výsledky, USDT

| Začátek půlroku | V5 | V18 | V22 | V28 | V30 | V31 |
|---|---:|---:|---:|---:|---:|---:|
| 2023-04-01 | -245.69 | -232.04 | -169.50 | -100.49 | 0.00 | 0.00 |
| 2023-10-01 | -214.56 | 14.77 | -239.90 | -197.34 | 36.44 | 36.44 |
| 2024-04-01 | -60.93 | -233.70 | -196.46 | 306.28 | -170.87 | -79.42 |
| 2024-10-01 | 3701.48 | 2251.03 | 2251.03 | 550.75 | 246.53 | 246.53 |
| 2025-04-01 | 627.03 | 581.89 | 484.76 | 302.79 | 605.36 | 605.36 |
| 2025-10-01 | 440.74 | 506.63 | 383.49 | 333.22 | 595.27 | 10.09 |
| 2026-04-01 | 1028.74 | 1310.28 | 1383.48 | 178.01 | -255.01 | -87.51 |

## Co z toho plyne pro další vývoj

- V18 má5/6 kladných bloků, ale první z nich jen+14,77USDT; při zdvojených
  nákladech zůstávají4/6. Nejlepší půlrok vydělal22,51%, což stále ukazuje
  závislost části zisku na velkém růstovém období.
- V28 má5/6 kladných bloků i ve stresu a menší rozdíly mezi nimi. V každém
  však pouze4–15 obchodů. Původních54 souvislých obchodů a interval zahrnující
  zápornou očekávanou hodnotu nadále brání přijetí. Tato diagnostika ji
  nemění na schváleného bota.
- V30/V31:4/6 kladných bloků, V31 ve stresu jen3/6. V posledním půlroce
  V30−255,01USDT a V31−87,51USDT, zatímco V18+1310,28USDT. Nedokazuje to
  obecnou nadřazenost V18, ale nepodporuje tvrzení, že komplikovanější
  měsíční výběr zatím stabilitu vyřešil.
- Původní přijímací brány ani historické výsledky se nemění. Výběr příznivějších
  hranic období po znalosti výsledků by byl dalším přeučením. Další hypotéza
  musí řešit doloženou slabinu a být zapsána před testem; prosté přidávání
  parametrů nebo obchodů nyní nemá oporu v získaných výsledcích.

## Provedení a evidence

Stejné poplatky/skluz/polovina spreadu na stranu0,10/0,03/0,01%; stres2×.
Spot LONG,bez páky,riziko0,5% včetně nákladů,alokace<=35%. XRP/BTC po42
ověřených archivech,368352 svíčkách. Indikátory mohou používat starší historii,
nikdy budoucí data. Měsíční rozhodnutí V30/V31 znovu vypočtena z předchozích
180/90 dnů včetně nákladů. Volby nejsou přizpůsobeny auditovanému půlroku.

87 stávajících testů prošlo lokálně. Audit všech84 ledgerů potvrdil účetní
souhlas obchodních P/L a konečného denního kapitálu, bez překryvu pozic.
`results/20261015_halfyear/summary.json`: všechny základní/zátěžové metriky,
manifesty a zdrojové kontrolní součty; `evidence.tar.gz`: všech84 ledgerů
a denní kapitál; `audit_checks.json`: kontrola a počty obchodů po blocích.

Současně dokončeno uložení zamítnutých V34/V35 a jejich diagnostiky.
Rezervované2022/2021 neotevřeny, žádné PAPER/LIVE, ostatní boty beze změny.

GitHub zopakoval87 testů i vypsané blokové výsledky a souhrny všech6 strategií:
https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38681244986
Úspěch workflow potvrzuje provedení výpočtu, nikoli přijetí strategie.
