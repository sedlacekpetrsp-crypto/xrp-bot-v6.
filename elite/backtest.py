"""Conservative research backtester for ELITE; no live execution.

Entry at NEXT bar open with adverse slippage. Stop/target checked against
subsequent OHLC bars. If both touch in one bar, assume STOP first.
"""
from dataclasses import dataclass
from typing import Sequence
from elite.strategy import signal_from_closed_bars

@dataclass
class Trade:
    side: str
    entry_index: int
    exit_index: int
    entry: float
    exit: float
    pnl: float
    reason: str

def backtest(bars: Sequence[tuple], initial_equity=10000.0, risk_fraction=0.005,
             fee_rate=0.0005, slippage_rate=0.0002, max_bars=24,
             max_notional_fraction=0.35):
    """Bars: (open,high,low,close), sorted oldest to newest; all values > 0.
    Spot OHLCV data supports simulated shorts but not executable spot shorting.
    Short performance is hypothetical until a valid derivatives execution model exists.
    """
    if not (0 < risk_fraction <= 0.02 and 0 <= fee_rate < 0.1 and
            0 <= slippage_rate < 0.1 and max_bars >= 1 and initial_equity > 0):
        raise ValueError("invalid backtest settings")
    equity=float(initial_equity)
    trades=[]
    equity_curve=[equity]
    i=99
    while i < len(bars)-1:
        hist=bars[max(0,i-100):i+1]
        sig=signal_from_closed_bars([b[1] for b in hist],[b[2] for b in hist],
                                    [b[3] for b in hist])
        if sig is None:
            i+=1
            continue
        direction=1 if sig.side=="LONG" else -1
        raw_entry=bars[i+1][0]
        entry=raw_entry*(1+direction*slippage_rate)
        stop=entry-direction*sig.stop_distance
        target=entry+direction*sig.target_distance
        if stop <= 0 or target <= 0:
            i+=1
            continue
        risk_budget=equity*risk_fraction
        qty=min(risk_budget/sig.stop_distance, equity*max_notional_fraction/entry)
        if qty <= 0:
            i+=1
            continue
        exit_i=min(i+max_bars,len(bars)-1)
        exit_price=None
        reason="TIME"
        for j in range(i+1,exit_i+1):
            o,h,l,c=bars[j]
            if direction==1:
                # Gaps can breach stops; fill at the worse of open and stop.
                if o<=stop: exit_price=o; reason="STOP_GAP"
                elif o>=target: exit_price=target; reason="TARGET_GAP"
                elif l<=stop: exit_price=stop; reason="STOP"
                elif h>=target: exit_price=target; reason="TARGET"
            else:
                if o>=stop: exit_price=o; reason="STOP_GAP"
                elif o<=target: exit_price=target; reason="TARGET_GAP"
                elif h>=stop: exit_price=stop; reason="STOP"
                elif l<=target: exit_price=target; reason="TARGET"
            if exit_price is not None:
                exit_i=j
                break
        if exit_price is None:
            exit_price=bars[exit_i][3]
        # Adverse slippage on exit as well; entry slippage already included.
        fill_exit=exit_price*(1-direction*slippage_rate)
        gross=direction*(fill_exit-entry)*qty
        fees=fee_rate*qty*(entry+fill_exit)
        pnl=gross-fees
        equity+=pnl
        equity_curve.append(equity)
        trades.append(Trade(sig.side,i+1,exit_i,entry,fill_exit,pnl,reason))
        i=exit_i+1  # never overlap positions; no reentry on same exit bar
    peak=initial_equity
    max_drawdown=0.0
    for value in equity_curve:
        peak=max(peak,value)
        max_drawdown=max(max_drawdown,(peak-value)/peak)
    wins=sum(t.pnl>0 for t in trades)
    gross_profit=sum(max(t.pnl,0) for t in trades)
    gross_loss=-sum(min(t.pnl,0) for t in trades)
    return {"starting_equity":initial_equity,"ending_equity":equity,
            "net_pnl":equity-initial_equity,"max_drawdown_pct":max_drawdown*100,"trades":len(trades),
            "win_rate":wins/len(trades) if trades else None,
            "profit_factor":gross_profit/gross_loss if gross_loss else None,
            "trade_log":trades}
