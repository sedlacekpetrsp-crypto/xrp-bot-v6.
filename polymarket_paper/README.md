# PAPER test: párová strategie Polymarket Up/Down

Stav: **26. 11. 2026, kód hotový a otestovaný offline (7 testů). Zatím neběží na živých datech.**

## Hypotéza (z tweetu @RetroValix, 26. 11. 2026)
Na 5m/15m krypto trzích „Up or Down“ nakupovat obě strany tak, aby průměrná
cena páru byla < 1 USDC. Jeden z kusů se vždy vyplatí 1 USDC.

## Strategie
| název | logika | riziko |
|---|---|---|
| `instant_pair` | taker nákup UP+DOWN naráz, jen když `ask_up + ask_dn + poplatky <= 0.99` | téměř žádné (pokud se plní) |
| `leg_in` | koupit stranu pod 0.45, druhou dokoupit, až je pár ≤ 0.97; max 40 nespárovaných kusů; posledních 60 s žádné nové nohy | nespárované kusy = směrová sázka |

Poplatek: `shares × rate × p × (1 − p)`, `rate` z `feeSchedule` každého trhu
(26. 11. 2026: XRP 15m = 0.01; dokumentace uvádí pro krypto až 0.07).

## Proč jsou výsledky spíš optimistické
- plnění za zobrazený ask bez latence a bez konkurence jiných botů,
- strategie jen jako taker (maker rebaty nesimulujeme),
- knihu čteme po ~3 s, skutečné příležitosti trvají milisekundy.

Kladný výsledek tedy je **nutná, ne postačující** podmínka. Záporný výsledek strategii prakticky vyřazuje.

## První pozorování (ruční snímek, 26. 11. 2026, 12:47)
XRP 15m: nejlepší ask UP 0.50, DOWN ≈ 0.54, takže součet je 1.04. Okamžitá arbitráž v tu chvíli nebyla.

## Spuštění (jen čte veřejná API, žádné klíče)
```
python -m polymarket_paper.collector       # sběr + simulace, JSONL do data/polymarket_paper
python -m polymarket_paper.report          # souhrn
python -m pytest -q test_polymarket_paper.py
```

## Kritérium úspěchu (stanoveno předem)
Alespoň 7 dní dat a 300 vyhodnocených trhů na strategii, kladný PnL po poplatcích,
a také kladný PnL v obou polovinách období zvlášť.
