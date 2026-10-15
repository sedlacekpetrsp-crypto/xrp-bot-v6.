# V40–V41: denní horizont, předem pevná hypotéza

Zmrazeno před výpočtem výsledků. Hypotéza: pomalejší denní signály mohou
omezit krátké obraty a náklady. Denní horizont není zárukou nové výhody;
V40 je příbuzná dřívějším průrazům, V41 návratům v trendu. Žádná mřížka.

V40: close kompletního UTC dne nad maximem předchozích20 dnů, stop2×ATR20,
bez cíle; výstup close pod minimem předchozích10 dnů.
V41: close nad SMA50, SMA50 nad hodnotou před10 dny, dva předchozí poklesy
close (C[k-3]>C[k-2]>C[k-1]) a aktuální close nad high předchozího dne.
Stop2×ATR20, cíl4×ATR20, výstup pod SMA50 nebo po20 dnech.
Obě:60 celých dnů rozehřátí; signál až po uzavření UTC dne, provedení
následující5m open. Stop je stále kontrolován na5m datech. Žádný BTC filtr.

Stejný simulátor, spot LONG, riziko0,5 %, alokace35 %, účet10 000 USDT.
Fee0,1 %, skluz0,03 %, halfspread0,01 % na stranu; stres dvojnásobek.
Vývojová data duben2023–září2026, původní4 bloky s resetem a souvislý běh.
Brány beze změny:3/4 kladné bloky,60 obchodů, PF1,2, DD<=10 %, intrabar<=12 %,
kladný stres a dolní95% bloková bootstrap mez denního P/L nad0.
I pomalejší strategie musí splnit počet obchodů; málo obchodů není úspěch.
Případná diagnostika nulových nákladů pouze vysvětluje zamítnutí.

Rok2022 je již prohlédnutý po V38, nepoužívat jako nový holdout.
Rok2021 se v tomto běhu neotevírá. Případný přeživší vyžaduje další předem
zmrazenou validaci a prospektivní data; tento běh nikoho neschvaluje pro PAPER.
Uváděné intervaly nejsou korigované na mnohonásobné hledání (již41 variant).
Žádné nasazení ani změna ostatních botů.
