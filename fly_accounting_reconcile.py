"""User-authorized, one-time PAPER ledger correction; raw trades are retained."""
import json
import math
from datetime import datetime, timezone

MARKER='fly-ledger-reconcile-20261011'
EXPECTED_DUPLICATES={250:248,290:289,314:313}


def canonical_rows(rows):
    # Rows must be ordered by first close time, then record id.
    seen={};excluded={};kept=[]
    for row in rows:
        trade_id,symbol,side,opened,entry,qty,pnl,closed=row
        if opened is None or closed is None or not all(math.isfinite(float(v)) for v in (entry,qty,pnl)):
            raise ValueError('Incomplete ledger cannot be reconciled')
        fingerprint=(symbol,side,opened,entry,qty)
        if fingerprint in seen:excluded[trade_id]=seen[fingerprint]
        else:seen[fingerprint]=trade_id;kept.append(row)
    return kept,excluded


def reconcile(module):
    if not module.DATABASE_URL:raise ValueError('Persisted ledger required')
    with module.get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS fly_accounting_reconciliations
                           (marker text PRIMARY KEY,details jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now())''')
            cur.execute('SELECT details FROM fly_accounting_reconciliations WHERE marker=%s',(MARKER,))
            old=cur.fetchone()
            if old:return {'status':'already_applied',**old[0]}
            cur.execute('SELECT state FROM v8fixed_state WHERE id=1 FOR UPDATE')
            saved=cur.fetchone()[0]
            if saved.get('paper_position') or saved.get('paper_positions'):
                raise ValueError('Cannot reconcile an open portfolio')
            cur.execute('LOCK TABLE v8fixed_trades IN SHARE ROW EXCLUSIVE MODE')
            cur.execute('''SELECT id,symbol,side,opened_at,entry_price,qty,pnl,closed_at
                           FROM v8fixed_trades ORDER BY closed_at,id''')
            rows=cur.fetchall();kept,excluded=canonical_rows(rows)
            if len(rows)!=290 or excluded!=EXPECTED_DUPLICATES:
                raise ValueError('Ledger changed; explicit review required')
            if abs(math.fsum(float(r[6]) for r in rows)+855.1231999516979)>1e-6:
                raise ValueError('Ledger P/L changed; explicit review required')
            cur.execute('SELECT trade_id,canonical_trade_id FROM fly_trade_exclusions')
            if cur.fetchall():raise ValueError('Unexpected prior exclusions')
            for trade_id,keeper in excluded.items():
                cur.execute('''INSERT INTO fly_trade_exclusions(trade_id,canonical_trade_id,reason,marker)
                               VALUES(%s,%s,%s,%s)''',
                            (trade_id,keeper,'Later close of the same PAPER opening',MARKER))
            before=float(saved['paper_balance'])
            net=math.fsum(float(r[6]) for r in kept)
            after=float(module.STARTING_BALANCE)+net
            details={'raw_trade_count':len(rows),'canonical_trade_count':len(kept),
                     'excluded_trade_ids':list(excluded),'canonical_net_pnl':net,
                     'previous_balance':before,'corrected_balance':after,'accounting_adjustment':after-before,
                     'starting_balance':float(module.STARTING_BALANCE),
                     'policy':'Earliest recorded close for each identical PAPER opening fingerprint',
                     'authorized_at':datetime.now(timezone.utc).isoformat(),
                     'adjustment_is_trade_pnl':False,'historical_cash_provenance_reconstructed':False}
            cur.execute('INSERT INTO fly_accounting_reconciliations(marker,details) VALUES(%s,%s::jsonb)',
                        (MARKER,json.dumps(details)))
            # Update only the balance; recovery snapshots and all other state survive.
            cur.execute("UPDATE v8fixed_state SET state=jsonb_set(state,'{paper_balance}',%s::jsonb),updated_at=now() WHERE id=1",
                        (json.dumps(after),))
        conn.commit()
    module.load_state()
    return {'status':'applied',**details}
