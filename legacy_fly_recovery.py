"""One-time settlement of PAPER positions opened by the disabled scanner worker.

Never sends orders. Retains raw trade history and the pre-existing balance difference.
"""
import copy
import json
import math
from datetime import datetime, timezone

BUILD='legacy-fly-pause-recovery-20261011'
OPENINGS={
    'ETHUSDC':'2026-10-11T07:39:02.718477+00:00',
    'SOLUSDC':'2026-10-11T07:39:20.763869+00:00',
    'XRPUSDC':'2026-10-11T07:39:26.759590+00:00',
}
# Fixed constants in the deployed scanner's app_v8_fly_engine.py.
FEE_RATE=.0005
SLIPPAGE_RATE=.0002


def settlement(position,price,now):
    if not math.isfinite(price) or price<=0:raise ValueError('Invalid recovery quote')
    if position.get('partial_taken') or position.get('partial_realized_pnl',0):
        raise ValueError('Partial exits require a separate reconciliation')
    p=copy.deepcopy(position)
    entry=float(p['entry_price']);qty=float(p['qty'])
    if not math.isfinite(entry) or not math.isfinite(qty) or entry<=0 or qty<=0:
        raise ValueError('Invalid legacy position')
    if p['side'] not in ('LONG','SHORT'):raise ValueError('Invalid legacy side')
    exit_price=price*(1-SLIPPAGE_RATE if p['side']=='LONG' else 1+SLIPPAGE_RATE)
    gross=(exit_price-entry)*qty if p['side']=='LONG' else (entry-exit_price)*qty
    fees=(entry+exit_price)*qty*FEE_RATE
    p.update(exit_price=exit_price,gross_pnl=gross,fees=fees,pnl=gross-fees,
             closed_at=now.isoformat(),reason='AUDIT PAUSE CLOSE | legacy scanner FLY disabled',
             entry_features={'recovery_build':BUILD,'source':'v8-candle-scanner',
                             'fee_rate':FEE_RATE,'slippage_rate':SLIPPAGE_RATE,'observed_exit_quote':price})
    return p


async def recover(module):
    if not module.DATABASE_URL:return {'status':'no_database'}
    with module.get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT state FROM v8fixed_state WHERE id=1')
            row=cur.fetchone()
    saved=(row[0] if row else {}) or {}
    positions=saved.get('paper_positions') or {}
    if not positions:return {'status':'nothing_to_recover'}
    if set(positions)!=set(OPENINGS) or any(p.get('opened_at')!=OPENINGS[s] for s,p in positions.items()):
        raise ValueError('Unexpected legacy portfolio; recovery refused')
    trades=[]
    for symbol,p in positions.items():
        price=await module.get_live_price(symbol,max_age=1.0)
        trades.append(settlement(p,price,datetime.now(timezone.utc)))
    with module.get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT state FROM v8fixed_state WHERE id=1 FOR UPDATE')
            locked=cur.fetchone()[0]
            if locked!=saved:raise ValueError('Legacy state changed while collecting quotes')
            cur.execute('CREATE TABLE IF NOT EXISTS fly_settlements (position_key text PRIMARY KEY, closed_at timestamptz NOT NULL DEFAULT now())')
            for t in trades:
                fingerprint=(t['symbol'],t['side'],t['opened_at'],t['entry_price'],t['qty'])
                cur.execute('SELECT 1 FROM v8fixed_trades WHERE symbol=%s AND side=%s AND opened_at=%s AND entry_price=%s AND qty=%s LIMIT 1',fingerprint)
                if cur.fetchone():raise ValueError('Legacy position already closed; reconciliation required')
                key='|'.join(map(str,fingerprint))
                cur.execute('INSERT INTO fly_settlements(position_key) VALUES (%s) ON CONFLICT DO NOTHING RETURNING position_key',(key,))
                if not cur.fetchone():raise ValueError('Legacy position already claimed')
                cur.execute('''INSERT INTO v8fixed_trades
                    (symbol,side,setup,regime,score,entry_price,exit_price,qty,gross_pnl,fees,pnl,
                     initial_risk_usdc,mae_r,mfe_r,reason,opened_at,closed_at,entry_features)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)''',
                    tuple(t.get(k) for k in ('symbol','side','setup','regime','score','entry_price','exit_price','qty','gross_pnl','fees','pnl','initial_risk_usdc','mae_r','mfe_r','reason','opened_at','closed_at'))+(json.dumps(t['entry_features']),))
            updated=copy.deepcopy(saved)
            net=sum(t['pnl'] for t in trades)
            updated.update(paper_position=None,paper_positions={},paper_balance=float(saved['paper_balance'])+net,
                           legacy_recovery={'build':BUILD,'closed_positions':positions,'trades':trades,
                                            'net_pnl':net,'previous_balance':saved['paper_balance']})
            cur.execute('UPDATE v8fixed_state SET state=%s::jsonb,updated_at=now() WHERE id=1',(json.dumps(updated),))
        conn.commit()
    module.load_state()
    return {'status':'settled','count':len(trades),'net_pnl':net}
