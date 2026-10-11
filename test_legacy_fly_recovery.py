import asyncio
import copy
import json
import unittest
from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import legacy_fly_recovery as recovery


class RecoveryTests(unittest.TestCase):
    def setup_account(self,fail=False,changed=False):
        positions={symbol:dict(symbol=symbol,side='SHORT',entry_price=100,qty=1,
                    setup='RAPID_MOMENTUM',opened_at=opened,partial_taken=False)
                   for symbol,opened in recovery.OPENINGS.items()}
        database={'state':{'paper_positions':positions,'paper_position':positions['ETHUSDC'],
                           'paper_balance':9327.277655852935},'trades':[],'keys':[]}
        class Connection:
            def __init__(self):self.pending=copy.deepcopy(database);self.committed=False
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def cursor(self):return Cursor(self)
            def commit(self):database.clear();database.update(self.pending);self.committed=True
        class Cursor:
            def __init__(self,conn):self.conn=conn
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def execute(self,sql,args=None):
                self.sql=sql
                if sql.startswith('INSERT INTO fly_settlements'):self.conn.pending['keys'].append(args[0])
                if 'INSERT INTO v8fixed_trades' in sql:
                    self.conn.pending['trades'].append(args)
                    if fail:raise RuntimeError('disk failure')
                if sql.startswith('UPDATE v8fixed_state'):self.conn.pending['state']=json.loads(args[0])
            def fetchone(self):
                if 'SELECT state' in self.sql:
                    state=copy.deepcopy(database['state'])
                    if changed and 'FOR UPDATE' in self.sql:state['paper_balance']+=1
                    return (state,)
                if self.sql.startswith('SELECT 1'):return None
                return ('claimed',)
        module=SimpleNamespace(DATABASE_URL='mock',get_db=Connection,get_live_price=AsyncMock(return_value=99),
                               load_state=lambda:None)
        return module,database

    def test_three_positions_settle_once_and_balance_matches_recorded_delta(self):
        module,db=self.setup_account();before=db['state']['paper_balance']
        result=asyncio.run(recovery.recover(module))
        self.assertEqual(result['count'],3)
        self.assertEqual(len(db['trades']),3);self.assertEqual(len(db['keys']),3)
        self.assertEqual(db['state']['paper_positions'],{})
        self.assertIsNone(db['state']['paper_position'])
        self.assertAlmostEqual(db['state']['paper_balance'],before+result['net_pnl'])
        self.assertEqual(asyncio.run(recovery.recover(module))['status'],'nothing_to_recover')
        self.assertEqual(len(db['trades']),3)
        self.assertEqual(len(db['state']['legacy_recovery']['closed_positions']),3)

    def test_write_failure_rolls_back_all_positions(self):
        module,db=self.setup_account(fail=True);before=copy.deepcopy(db)
        with self.assertRaises(RuntimeError):asyncio.run(recovery.recover(module))
        self.assertEqual(db,before)

    def test_state_change_aborts_before_writing(self):
        module,db=self.setup_account(changed=True);before=copy.deepcopy(db)
        with self.assertRaisesRegex(ValueError,'changed'):asyncio.run(recovery.recover(module))
        self.assertEqual(db,before)

    def test_unexpected_opening_is_not_automatically_closed(self):
        module,db=self.setup_account();db['state']['paper_positions']['ETHUSDC']['opened_at']='different'
        before=copy.deepcopy(db)
        with self.assertRaisesRegex(ValueError,'Unexpected'):asyncio.run(recovery.recover(module))
        self.assertEqual(db,before);module.get_live_price.assert_not_awaited()

    def test_long_short_costs_and_invalid_quotes(self):
        now=datetime.now(timezone.utc)
        for side,price in [('LONG',101),('SHORT',99)]:
            p=dict(entry_price=100,qty=2,side=side)
            t=recovery.settlement(p,price,now)
            self.assertGreater(t['pnl'],0)
            self.assertAlmostEqual(t['pnl'],t['gross_pnl']-t['fees'])
            self.assertEqual(p,dict(entry_price=100,qty=2,side=side))
        for price in [float('nan'),float('inf'),0,-1]:
            with self.assertRaises(ValueError):recovery.settlement(p,price,now)

    def test_partial_position_refused(self):
        with self.assertRaisesRegex(ValueError,'Partial'):
            recovery.settlement(dict(partial_taken=True),100,datetime.now(timezone.utc))

if __name__=='__main__':unittest.main()
