"""Issue 56: rejection diagnostics; no production I/O or performance tests."""
import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch
import httpx
import pytest
import lh_whale as lh
from lh_sweep import signal_from_closed_candles


def setup_rows(side='LONG', volume=20):
    trend=[95+i*.1 for i in range(60)]
    if side=='SHORT': trend=list(reversed(trend))
    h=[101.]*60;l=[99.]*60;c=[100.]*60;v=[10.]*60
    if side=='LONG':l[-1]=98.
    else:h[-1]=102.
    v[-1]=volume
    return h,l,c,v,trend,trend

@pytest.mark.parametrize('side',['LONG','SHORT'])
def test_setup_diagnostics_preserve_signal(side):
    d={};args=setup_rows(side)
    plain=signal_from_closed_candles(*args)
    observed=signal_from_closed_candles(*args,diagnostics=d)
    assert observed==plain and observed.side==side
    assert d['reason_code']=='setup_ready'

@pytest.mark.parametrize('kind,expected', [('sweep','no_sweep_reclaim'),('trend','trend_mismatch'),('volume','volume_below_threshold')])
def test_setup_blockers(kind,expected):
    args=list(setup_rows());d={}
    if kind=='sweep':args[1][-1]=99.
    elif kind=='trend':args[4]=[100.]*60
    else:args[3][-1]=1.
    assert signal_from_closed_candles(*args,diagnostics=d) is None
    assert d['reason_code']==expected

@pytest.mark.parametrize('age,expected',[(-1,'future_signal'),(0,'paper_entry_opened'),(120000,'paper_entry_opened'),(120001,'stale_signal')])
def test_close_timestamp_window_is_feasible(age,expected):
    s=lh.initial();s['activated_at']=1
    now=600000+age
    out=lh.advance(s,dict(price=100,time=now),dict(candle=600000,signal='LONG',stop=98),now)
    assert out['entry_decision']['code']==expected
    assert bool(out['position'])==(expected=='paper_entry_opened')

@pytest.mark.parametrize('field,value,code', [('activated_at',600001,'before_activation'),('seen',600000,'already_seen'),('cooldown',700000,'cooldown'),('peak',20000,'risk_guard')])
def test_account_blockers(field,value,code):
    s=lh.initial();s['activated_at']=1;s[field]=value
    out=lh.advance(s,dict(price=100,time=600010),dict(candle=600000,signal='LONG',stop=98),600010)
    assert out['position'] is None and out['entry_decision']['code']==code
    if code=='risk_guard':assert 'KILL' in out['entry_decision']['risk_reason']


def test_wait_can_retry_same_candle_and_stale_quote_cannot_trade():
    s=lh.initial();s['activated_at']=1
    wait=dict(candle=600000,signal='WAIT',reason_code='futures_unavailable')
    s=lh.advance(s,dict(price=100,time=600010),wait,600010)
    assert s['seen']==0 and s['entry_decision']['code']=='futures_unavailable'
    a=dict(candle=600000,signal='LONG',stop=98)
    out=lh.advance(s,dict(price=100,time=580000),a,600020)
    assert out['entry_decision']['code']=='quote_stale_or_missing' and out['seen']==0
    assert lh.advance(out,dict(price=100,time=600030),a,600030)['position']


def test_analyze_to_atomic_tick_to_snapshot_with_in_memory_sql_double():
    """Real strategy, mock HTTP and transactional SQL double; not real PostgreSQL."""
    stamp=216000000; now=stamp+10
    async def klines(symbol,interval,limit):
        step={'5m':300000,'15m':900000,'1h':3600000}[interval]
        h,l,c,v,t,_=setup_rows()
        if interval!='5m': c=t;h=[x+1 for x in c];l=[x-1 for x in c]
        return [[stamp-step*(60-i),c[i],h[i],l[i],c[i],v[i],stamp-step*(59-i)-1] for i in range(60)]
    def response(req):
        if 'openInterest' in req.url.path: data=[dict(timestamp=stamp-300000,sumOpenInterest='100'),dict(timestamp=stamp,sumOpenInterest='101')]
        elif 'topLong' in req.url.path:data=[dict(timestamp=stamp-300000,longShortRatio='1.2')]
        else:data=[dict(timestamp=stamp-300000,buySellRatio='1.2')]
        return httpx.Response(200,json=data)
    class DB:
        def __init__(self):
            self.state=lh.initial();self.state['activated_at']=1;self.trades={};self.sql=[];self.fail=False
        def __enter__(self):self.saved=copy.deepcopy((self.state,self.trades));return self
        def __exit__(self,kind,*args):
            if kind:self.state,self.trades=self.saved
        def execute(self,sql,args=None):
            self.sql.append(sql)
            if sql.startswith('INSERT INTO lh_whale_trades'):
                assert args[0] not in self.trades
                self.trades[args[0]]=json.loads(args[1])
            if sql.startswith('UPDATE lh_whale_state'):
                if self.fail:raise RuntimeError('simulated write failure')
                self.state=json.loads(args[0])
            self.result=[1] if 'SELECT 1 FROM paper_epoch_resets' in sql else [copy.deepcopy(self.state)]
            return self
        def fetchone(self):return self.result
    async def run():
        with patch.object(lh.time,'time',return_value=now/1000),patch.object(lh,'_futures_retry_at',0):
            async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
                a=await lh.analyze(SimpleNamespace(LH_LOCAL_ONLY=True,get_klines=klines),client)
        assert a['signal']=='LONG' and a['reason_code']=='signal_ready'
        db=DB()
        with patch.object(lh,'connect',return_value=db):
            s=lh.tick('test-only',dict(price=100,time=now),a,now)
            assert s['position'] and s['entry_decision']['code']=='paper_entry_opened'
            db.fail=True
            with pytest.raises(RuntimeError):lh.tick('test-only',dict(price=90,time=now+10),None,now+10)
            assert db.state['position'] and not db.trades
            db.fail=False
            s=lh.tick('test-only',dict(price=90,time=now+20),None,now+20)
            lh.tick('test-only',dict(price=90,time=now+20),None,now+20)
            assert s['count']==1 and len(db.trades)==1 and s['entry_decision']['code']=='position_just_closed'
            assert any('FOR UPDATE' in q for q in db.sql)
        with patch.object(lh,'runtime',dict(state=s,quote=dict(price=90,time=now+20),analysis=a)),patch.object(lh.time,'time',return_value=(now+20)/1000):
            assert lh.snapshot()['entry_decision']['code']=='position_just_closed'
    asyncio.run(run())


def test_original_rejection_survives_seen_followup():
    s=lh.initial();s.update(activated_at=1,cooldown=700000)
    a=dict(candle=600000,signal='LONG',stop=98)
    s=lh.advance(s,dict(price=100,time=600010),a,600010)
    s=lh.advance(s,dict(price=100,time=600020),a,600020)
    assert s['entry_decision']['code']=='already_seen'
    assert s['last_signal_decision']['code']=='cooldown'
    assert s['last_signal_decision']['at']==lh.iso(600010)


def test_worker_db_failure_never_reports_saved_decision(capsys):
    async def run():
        async def price(*a,**k):return 100
        async def stop(*a):raise asyncio.CancelledError
        core=SimpleNamespace(DATABASE_URL='test-only',get_live_price=price,LH_LOCAL_ONLY=True)
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req: (_ for _ in ()).throw(AssertionError('unexpected network'))))
        with patch.object(lh.httpx,'AsyncClient',return_value=client),patch.object(lh,'runtime',{}),patch.object(lh,'init_db'),patch.object(lh,'tick',side_effect=RuntimeError('write failed')),patch.object(lh.asyncio,'sleep',stop):
            with pytest.raises(asyncio.CancelledError):await lh.worker(core)
            assert lh.runtime['last_error']=='RuntimeError: write failed'
            assert 'state' not in lh.runtime
    asyncio.run(run())
    log=capsys.readouterr().out
    assert 'LH-WHALE RuntimeError' in log
    assert 'LH-WHALE entry' not in log and 'LH-WHALE scan' not in log
