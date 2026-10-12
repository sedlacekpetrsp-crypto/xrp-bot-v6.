import copy,json,unittest
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import fly_accounting_reconcile as fix

class ReconcileTests(unittest.TestCase):
    def setup_db(self,fail=False):
        now=datetime(2026,10,1,tzinfo=timezone.utc)
        rows=[]
        totals=[(248,250,-13.788149399171875,-14.968257388206425),
                (289,290,-15.156139489664865,-16.31725412403494),
                (313,314,.20516199353887732,-2.0426366704179917)]
        for i,(a,b,p,q) in enumerate(totals):
            opened=now+timedelta(minutes=i)
            for id,pnl in [(a,p),(b,q)]:rows.append((id,'XRP','LONG',opened,1.5+i,1,pnl,opened+timedelta(hours=id)))
        remainder=-855.1231999516979-sum(r[6] for r in rows)
        for i in range(284):rows.append((400+i,'ETH','LONG',now+timedelta(days=i+1),10,1,remainder if i==0 else 0,now+timedelta(days=i+2)))
        rows.sort(key=lambda r:(r[7],r[0]))
        db={'rows':rows,'exclusions':[],'marker':None,'state':{'paper_balance':9312.12507679486,'paper_position':None,'paper_positions':{},'legacy_recovery':{'keep':True}}}
        class Conn:
            def __init__(self):self.pending=copy.deepcopy(db)
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def cursor(self):return Cursor(self)
            def commit(self):db.clear();db.update(self.pending)
        class Cursor:
            def __init__(self,conn):self.conn=conn
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def execute(self,sql,args=None):
                self.sql=sql
                if 'INSERT INTO fly_trade_exclusions' in sql:
                    self.conn.pending['exclusions'].append(args)
                    if fail:raise RuntimeError('database error')
                if 'INSERT INTO fly_accounting_reconciliations' in sql:self.conn.pending['marker']=json.loads(args[1])
                if 'UPDATE v8fixed_state' in sql:self.conn.pending['state']['paper_balance']=json.loads(args[0])
            def fetchone(self):
                if 'SELECT details' in self.sql:return (db['marker'],) if db['marker'] else None
                return (copy.deepcopy(db['state']),)
            def fetchall(self):return db['rows'] if 'SELECT id,symbol' in self.sql else db['exclusions']
        return SimpleNamespace(DATABASE_URL='mock',STARTING_BALANCE=10000,get_db=Conn,load_state=lambda:None),db
    def test_atomic_correction_retains_history_and_is_idempotent(self):
        m,db=self.setup_db();before=copy.deepcopy(db['rows'])
        result=fix.reconcile(m)
        self.assertAlmostEqual(result['corrected_balance'],9178.204948230961)
        self.assertAlmostEqual(result['accounting_adjustment'],-133.9201285638996)
        self.assertEqual(db['rows'],before);self.assertEqual(len(db['exclusions']),3)
        self.assertEqual(db['state']['legacy_recovery'],{'keep':True})
        self.assertEqual(fix.reconcile(m)['status'],'already_applied')
        self.assertEqual(len(db['exclusions']),3)
    def test_failure_rolls_back_balance_and_exclusions(self):
        m,db=self.setup_db(fail=True);before=copy.deepcopy(db)
        with self.assertRaises(RuntimeError):fix.reconcile(m)
        self.assertEqual(db,before)
    def test_open_or_changed_ledger_refused(self):
        for change in ('open','count','pnl'):
            m,db=self.setup_db()
            if change=='open':db['state']['paper_position']={'symbol':'XRP'}
            elif change=='count':db['rows'].pop()
            else:
                r=list(db['rows'][-1]);r[6]=1;db['rows'][-1]=tuple(r)
            before=copy.deepcopy(db)
            with self.assertRaises(ValueError):fix.reconcile(m)
            self.assertEqual(db,before)
    def test_first_close_selected_by_opening_not_reason(self):
        m,db=self.setup_db();kept,excluded=fix.canonical_rows(db['rows'])
        self.assertEqual(excluded,fix.EXPECTED_DUPLICATES)
        self.assertEqual(len(kept),287)

if __name__=='__main__':unittest.main()
