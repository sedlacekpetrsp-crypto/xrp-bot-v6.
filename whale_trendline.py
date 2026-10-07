"""Exploratory PAPER XRP 4h long bounce, frozen rules from 2026-10-06 report.

No live orders. Only confirmed pivots and completed candles are used.
The shared worker executes at the current observed quote (not a historical open).
"""
STRATEGY = "TRENDLINE_4H_LONG"
SYMBOL = "XRPUSDT"


def candidate(rows):
    diag = dict(strategy=STRATEGY, symbol=SYMBOL, reason="Čekám na rostoucí support a odraz na 4h")
    if len(rows) < 220:
        return None, dict(diag, reason="Chybí 220 uzavřených 4h svíček")
    highs = [float(r[2]) for r in rows]
    lows = [float(r[3]) for r in rows]
    closes = [float(r[4]) for r in rows]
    tr = [highs[0]-lows[0]] + [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1,len(rows))]
    atr = [sum(tr[max(0,i-13):i+1])/min(14,i+1) for i in range(len(rows))]
    # A pivot becomes available only when its third right candle has closed.
    pivots = [i for i in range(3,len(rows)-3) if all(lows[i] < lows[j] for j in range(i-3,i+4) if j != i)]
    if len(pivots) < 2:
        return None, diag
    a,b = pivots[-2:]
    i = len(rows)-1
    if not 5 <= b-a <= 80 or i-b > 120 or lows[b] <= lows[a]:
        return None, diag
    slope = (lows[b]-lows[a])/(b-a)
    line = lambda k: lows[a]+slope*(k-a)
    diag.update(support=line(i), atr=atr[i], anchor_times=[int(rows[a][0]),int(rows[b][0])], signal_candle=int(rows[i][6])+1)
    if any(closes[j] < line(j)-.25*atr[j] for j in range(a,i)):
        return None, dict(diag, reason="4h support byl porušen; čekám na nový")
    if not (abs(lows[i]-line(i)) <= .2*atr[i] and closes[i] > line(i)+.15*atr[i] and closes[i] > float(rows[i][1]) and closes[i-1] > line(i-1)):
        return None, diag
    diag['reason'] = "Odraz od 4h supportu potvrzen"
    return dict(side="LONG", entry=closes[i], stop=closes[i]-2*atr[i],
                tp=closes[i]+4*atr[i], key=f"trendline4h:{rows[a][0]}:{rows[b][0]}:LONG",
                strategy=STRATEGY, confirmation=diag), diag


def snapshot(state):
    trades = [t for t in state.get('trades',[]) if t.get('strategy') == STRATEGY]
    positions = [p for p in state.get('open_positions',[]) if p.get('strategy') == STRATEGY]
    return dict(strategy=STRATEGY, label="Trendline 4h · XRP · LONG", mode="PAPER",
                trades=len(trades), wins=sum(t['net_pnl']>0 for t in trades),
                win_rate=100*sum(t['net_pnl']>0 for t in trades)/len(trades) if trades else None,
                net_pnl=sum(t['net_pnl'] for t in trades), open_positions=len(positions),
                risk_per_trade=.03, last_check=state.get('trendline_last_check'))
