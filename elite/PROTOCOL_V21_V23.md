# Frozen V21–V23 exit experiment — 2026-10-14

Controlled ablation of V18, not three independent strategies. All V18 entry
signals, initial 3ATR stop, 0.5% risk and 35% allocation cap remain unchanged.
V21: trailing distance fixed at initial stop distance; ratchet stop upward from
completed 5m CLOSE only, effective on the next bar, including after entry bar.
Never use that bar's high to retrospectively trigger an exit. Gap below stop
fills at worse opening price plus costs. Original XRP channel exit retained.
V22: original V18 plus exit when completed hourly BTC close < its SMA168.
V23: both modifications. No parameter grid or adjustment after results.

Data and gates identical to PROTOCOL_V18_V20.md: Apr2023–Sep2026 DEVELOPMENT,
4 reset blocks and continuous run, 10000USDT, fee/slip/halfspread per side
.001/.0003/.0001, stress doubles all. Require >=3/4 positive blocks, >=60 trades,
PF>=1.2, close DD<=10%, intrabar bound<=12%, stress P/L>0, positive lower95%
7day block-bootstrap daily mean (2000 draws, seed713). Report all failures.
Both XRP and BTC checksums/coverage/alignment required. No threshold changes.
Only frozen survivors unlock reserved 2022 historical challenge; 2021 remains
reserved. These historical tests cannot replace prospective validation.
No PAPER acceptance from development alone. No live orders or other bot changes.
Selection after >=23 variants adds bias; bootstrap is not search-corrected.
