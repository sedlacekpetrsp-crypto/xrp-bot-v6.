"""Bounded, observation-only archive. Never calls a trading cycle or entry/exit.

Minute samples cannot reconstruct a tick stream. Signal eligibility is evaluated
in separate module instances using only the captured inputs, including WAITs.
"""
import asyncio
import copy
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time
from types import SimpleNamespace
import uuid
from datetime import datetime, timezone

import httpx
import news_signal
from market_data import market
from swing_paper import connect

BUILD = 'research-market-evidence-20261030-archive-cap-256m'
SYMBOLS = ('XRPUSDC', 'ETHUSDC', 'SOLUSDC')
FRAMES = tuple((s, i, 250) for s in SYMBOLS for i in ('1m', '5m')) + (
    ('BTCUSDC', '1m', 10), ('BTCUSDT', '1m', 90), ('ETHUSDT', '1m', 90))
INTERVAL_SECONDS = 60
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_SAMPLE_BYTES = 256 * 1024
CONSTANTS = ('BOOK_LONG_MIN', 'BOOK_SHORT_MAX', 'BREAKOUT_LOOKBACK', 'EMA_SEP_MIN',
             'ENABLED_SETUPS', 'MIN_BREAKOUT_VOLUME', 'MIN_EDGE_MULTIPLE', 'MIN_SCORE',
             'MIN_TREND_VOLUME', 'ORDER_BOOK_LEVELS', 'RANGE_ADX_MAX', 'ROUND_TRIP_COST',
             'SETUP_PARAMS', 'TREND_ADX_MIN', 'FEE_RATE', 'SLIPPAGE_RATE')
HELPERS = ('adx_wilder', 'atr_wilder', 'ema', 'macd_hist', 'rsi_wilder', 'vwap')
ROOT = Path(__file__).resolve().parent
runtime = dict(build=BUILD, mode='OBSERVATION_ONLY', status='starting',
               sample_interval_seconds=INTERVAL_SECONDS, archive_limit_bytes=MAX_ARCHIVE_BYTES,
               last_error=None, last_saved_at=None, last_sample=None)
_task = None


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def json_bytes(value):
    return json.dumps(value, separators=(',', ':'), allow_nan=False).encode()


def source_hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
        'app_v8.py', 'v8_fly_layer.py', 'fast_scalper.py', 'lead_lag_scalper.py',
        'news_signal.py', 'market_data.py', 'paper_stop_policy.py', 'research_market_evidence.py')}


def isolated_module(filename):
    spec = importlib.util.spec_from_file_location('_research_'+filename[:-3], ROOT/filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SignalObserver:
    """Only pure indicators and captured-data callbacks are given to each copy.

    No database URL, order/entry callback, live price callback, shared state,
    client or application is present on this core object.
    """
    def __init__(self, core):
        self.config = {k: copy.deepcopy(getattr(core, k)) for k in CONSTANTS}
        self.history = [{k: copy.deepcopy(t.get(k)) for k in (
            'symbol', 'side', 'setup', 'initial_risk_usdc', 'pnl', 'closed_at')}
            for t in core.trade_history]
        self.core = SimpleNamespace(**copy.deepcopy(self.config),
            **{k: getattr(core, k) for k in HELPERS}, trade_history=copy.deepcopy(self.history))
        self.fly = isolated_module('v8_fly_layer.py')
        self.fast = isolated_module('fast_scalper.py')
        self.lead = isolated_module('lead_lag_scalper.py')
        self.fly.m = self.core
        self.fast.base = self.core
        self.lead.base = self.core

    def context(self):
        # Explicit allowlist above excludes all connection strings and secrets.
        config = copy.deepcopy(self.config)
        config['ENABLED_SETUPS'] = sorted(config['ENABLED_SETUPS'])
        return dict(build=BUILD, source_hashes=source_hashes(), constants=config,
                    fly_setup_health_history=self.history,
                    commit=os.getenv('RENDER_GIT_COMMIT'), captured_at=now_iso(),
                    scope='Signal filters only; production setup-health history frozen at observer start. No portfolio, recovery, sizing, execution, or PnL simulation.')

    async def evaluate(self, sample):
        async def klines(symbol, interval, limit=250):
            return copy.deepcopy(sample['frames'][symbol+':'+interval]['data'][-limit:])

        async def book(path, params):
            if path != '/api/v3/depth':
                raise ValueError('Observer permits captured depth only')
            return copy.deepcopy(sample['books'][params['symbol']]['data'])

        async def news(symbol):
            return copy.deepcopy(sample['news'][symbol])

        self.core.get_klines = klines
        self.core.binance_get = book
        self.fly.news_signal = SimpleNamespace(get_news=news)
        fly_rows, fast_rows, errors = [], [], {}
        for symbol in SYMBOLS:
            try:
                row = await self.fly.strategy(symbol)
                fly_rows.append(row)
                fast_rows.append(self.fast._fast_signal(row))
            except Exception as exc:
                errors[symbol] = type(exc).__name__+': '+str(exc)
        try:
            lead = copy.deepcopy(await self.lead.analyze())
        except Exception as exc:
            lead = None
            errors['LEADLAG'] = type(exc).__name__+': '+str(exc)
        return dict(scope='SIGNAL_FILTERS_ONLY_NO_TRADES', fly=fly_rows,
                    fast=fast_rows, leadlag=lead, errors=errors)


def validate_book(data):
    sides = []
    for name in ('bids', 'asks'):
        rows = data.get(name) or []
        if not rows or len(rows) > 20:
            raise ValueError('Missing or oversized depth')
        values = [(float(r[0]), float(r[1])) for r in rows]
        if any(not math.isfinite(x) or x <= 0 for pair in values for x in pair):
            raise ValueError('Invalid depth level')
        prices = [p for p, q in values]
        if prices != sorted(prices, reverse=name == 'bids') or len(set(prices)) != len(prices):
            raise ValueError('Unordered depth levels')
        sides.append(prices[0])
    if sides[0] >= sides[1]:
        raise ValueError('Crossed or locked book')


def validate_frame(rows, interval, captured_ms, minimum):
    step = {'1m': 60000, '5m': 300000}[interval]
    if not rows:
        raise ValueError('Missing candles')
    closed = 0
    for index, row in enumerate(rows):
        stamp = int(row[0])
        o, h, l, c, volume = map(float, row[1:6])
        if not all(math.isfinite(x) for x in (o,h,l,c,volume)) or not 0 < l <= min(o,c) <= max(o,c) <= h or volume < 0:
            raise ValueError('Invalid OHLCV')
        if stamp % step or int(row[6]) != stamp+step-1 or (index and stamp-int(rows[index-1][0]) != step):
            raise ValueError('Misaligned candles or gap')
        if stamp > captured_ms+5000:
            raise ValueError('Future candle')
        closed += int(row[6]) < captured_ms
    if closed < minimum or int(rows[-1][6]) < captured_ms-30000:
        raise ValueError('Insufficient or stale candle window')


async def capture(client, api, request=market.get):
    start = time.time()
    sample = dict(started_at=now_iso(), frames={}, books={}, quotes={}, errors={},
                  news={s:news_signal.cached_state(s) for s in SYMBOLS})
    semaphore = asyncio.Semaphore(2)

    async def fetch(group, key, path, params, validator):
        began = time.time()
        try:
            async with semaphore:
                response = await asyncio.wait_for(request(client, api+path, params=params, timeout=8), 10)
                response.raise_for_status()
                data = response.json()
                ended = time.time()
                validator(data, int(ended*1000))
                sample[group][key] = dict(data=data, requested_at=datetime.fromtimestamp(began, timezone.utc).isoformat(),
                    received_at=datetime.fromtimestamp(ended, timezone.utc).isoformat(), provider=market.provider,
                    exchange_sequence_available=bool(group == 'books' and data.get('lastUpdateId')),
                    exchange_quote_timestamp_available=False,
                    cache_max_age_seconds=15 if group == 'frames' else 1 if group == 'quotes' else 0)
        except Exception as exc:
            sample['errors'][group+':'+key] = type(exc).__name__+': '+str(exc)

    jobs = []
    for symbol, interval, limit in FRAMES:
        minimum = 200 if limit == 250 else 60 if limit == 90 else 4
        jobs.append(fetch('frames',symbol+':'+interval,'/api/v3/klines',
            dict(symbol=symbol,interval=interval,limit=limit),
            lambda data, now, i=interval, n=minimum:validate_frame(data,i,now,n)))
    for symbol in SYMBOLS:
        jobs.append(fetch('books',symbol,'/api/v3/depth',dict(symbol=symbol,limit=20),lambda d,n:validate_book(d)))

        def validate_price(data, now):
            p = float(data['price'])
            if not math.isfinite(p) or p <= 0:
                raise ValueError('Invalid quote')
        jobs.append(fetch('quotes',symbol,'/api/v3/ticker/price',dict(symbol=symbol),validate_price))
    tasks = [asyncio.create_task(job) for job in jobs]
    try:
        done, pending = await asyncio.wait(tasks, timeout=25)
        if pending:
            sample['errors']['batch'] = '25 second sampling budget exceeded; unfinished inputs omitted'
            for task in pending: task.cancel()
    finally:
        for task in tasks:
            if not task.done(): task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    sample['finished_at'] = now_iso()
    sample['duration_seconds'] = time.time()-start
    providers = sorted({v['provider'] for g in ('frames','books','quotes') for v in sample[g].values()})
    sample['quality'] = dict(inputs_complete=not sample['errors'], providers=providers,
        synchronized=sample['duration_seconds']<=20 and len(providers)==1,
        news_ready=all(n.get('status')=='running' and n.get('checked_at') for n in sample['news'].values()),
        scope='Minute samples with request timestamps, 20-level normalized depth; not tick data. Quote exchange timestamps unavailable; candles may be cached up to 15 seconds. No forward fills.')
    return sample


def init_archive(url):
    with connect(url) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS research_market_runs (id TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), context BYTEA NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS research_market_samples (bucket BIGINT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES research_market_runs(id), observed_at TIMESTAMPTZ NOT NULL, complete BOOLEAN NOT NULL, payload BYTEA NOT NULL, sha256 TEXT NOT NULL)')


def capacity(url):
    with connect(url) as conn:
        row = conn.execute("SELECT pg_total_relation_size('research_market_samples'),count(*),count(*) FILTER (WHERE complete),min(observed_at),max(observed_at) FROM research_market_samples").fetchone()
    return dict(archive_bytes=row[0],samples=row[1],complete_samples=row[2],first_observed_at=row[3].isoformat() if row[3] else None,
                last_observed_at=row[4].isoformat() if row[4] else None)


def archive_encoding(sample, bucket, previous=None):
    """Lossless candle patches, with a full checkpoint at least once per hour.

    Metadata, books, prices, news and decisions are always stored in full.
    Existing rows remain immutable and every patch points to a committed bucket.
    """
    if previous is None or bucket//60 != previous[0]//60:
        return sample
    base_bucket, base = previous
    if base_bucket >= bucket:
        raise ValueError('Archive base must precede sample')
    packed = copy.deepcopy(sample)
    packed['_archive_base_bucket'] = base_bucket
    for key, frame in packed['frames'].items():
        old = base['frames'].get(key)
        rows = frame['data']
        if not old or frame.get('provider') != old.get('provider') or not rows:
            continue
        old_rows = {int(row[0]):row for row in old['data']}
        changes = [row for row in rows if old_rows.get(int(row[0])) != row]
        frame['candle_patch'] = dict(first=int(rows[0][0]), last=int(rows[-1][0]),data_position=list(frame).index('data'),
            changes=changes, sha256=hashlib.sha256(json_bytes(rows)).hexdigest())
        del frame['data']
    return packed


def expand_sample(packed, base=None):
    """Restore exact original arrays, including partial bars and later revisions."""
    sample = copy.deepcopy(packed)
    if '_archive_base_bucket' not in sample:
        return sample
    if base is None:
        raise ValueError('Missing preceding committed research sample')
    del sample['_archive_base_bucket']
    for key, frame in sample['frames'].items():
        patch = frame.pop('candle_patch',None)
        if patch is None:
            continue
        old = base['frames'][key]
        if old.get('provider') != frame.get('provider'):
            raise ValueError('Research provider mismatch')
        rows = {int(row[0]):copy.deepcopy(row) for row in old['data']
                if patch['first']<=int(row[0])<=patch['last']}
        rows.update({int(row[0]):row for row in patch['changes']})
        restored = [rows[stamp] for stamp in sorted(rows)]
        if hashlib.sha256(json_bytes(restored)).hexdigest() != patch['sha256']:
            raise ValueError('Research candle reconstruction checksum mismatch')
        items = list(frame.items())
        items.insert(patch['data_position'],('data',restored))
        sample['frames'][key] = dict(items)
    return sample


def read_archived_sample(url, bucket):
    """Read-only export of a restored sample, checksum and its frozen context."""
    chain = []
    current = int(bucket)
    with connect(url) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        for _ in range(61):
            row = conn.execute('SELECT payload,sha256,run_id FROM research_market_samples WHERE bucket=%s',(current,)).fetchone()
            if row is None:
                raise ValueError('Missing archived research bucket')
            packed = json.loads(gzip.decompress(row[0]))
            if chain and row[2] != chain[0][2]:
                raise ValueError('Archive chain crosses frozen run contexts')
            chain.append((packed,row[1],row[2]))
            preceding = packed.get('_archive_base_bucket')
            if preceding is None:
                break
            if preceding >= current:
                raise ValueError('Invalid research archive chain')
            current = preceding
        else:
            raise ValueError('Research checkpoint chain too long')
        context_row = conn.execute('SELECT context FROM research_market_runs WHERE id=%s',(chain[0][2],)).fetchone()
    decoded = None
    for packed,checksum,run_id in reversed(chain):
        decoded = expand_sample(packed,decoded)
        if hashlib.sha256(json_bytes(decoded)).hexdigest() != checksum:
            raise ValueError('Research sample checksum mismatch')
    return decoded,chain[0][1],json.loads(gzip.decompress(context_row[0]))


def store_sample(url, run_id, context, sample, previous=None):
    raw = json_bytes(sample)
    bucket = int(datetime.fromisoformat(sample['started_at']).timestamp())//INTERVAL_SECONDS
    compressed = gzip.compress(json_bytes(archive_encoding(sample,bucket,previous)), mtime=0)
    if len(compressed)>MAX_SAMPLE_BYTES:
        raise ValueError('Research sample exceeds byte budget')
    quality = sample['quality']
    complete = quality['inputs_complete'] and quality['synchronized'] and quality['news_ready'] and not sample['signals']['errors']
    with connect(url) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(20261017, 1)')
        used = conn.execute("SELECT pg_total_relation_size('research_market_samples')").fetchone()[0]
        if used+len(compressed)+8192>MAX_ARCHIVE_BYTES:
            return dict(saved=False,reason='archive_full',archive_bytes=used)
        conn.execute('INSERT INTO research_market_runs (id,context) VALUES (%s,%s) ON CONFLICT DO NOTHING',
                     (run_id,gzip.compress(json_bytes(context),mtime=0)))
        result = conn.execute('INSERT INTO research_market_samples VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING bucket',
            (bucket,run_id,sample['finished_at'],complete,compressed,hashlib.sha256(raw).hexdigest())).fetchone()
    return dict(saved=bool(result),reason='saved' if result else 'duplicate_bucket',bucket=bucket,complete=complete,compressed_bytes=len(compressed))


def compact(sample):
    signals = sample['signals']
    return dict(started_at=sample['started_at'],quality=sample['quality'],errors=sample['errors'],
                analysis_errors=signals['errors'],
                fly=[{k:r.get(k) for k in ('symbol','signal','armed_side','no_trade_reason')} for r in signals['fly']],
                fast=[dict(symbol=r['symbol'],signal=r['fast_signal'],blockers=r['fast_blockers']) for r in signals['fast']],
                leadlag={k:signals['leadlag'].get(k) for k in ('signal','reason','blockers')} if signals['leadlag'] else None)


async def worker(core):
    initialized = False
    observer = None
    previous = None
    run_id = str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=8,limits=httpx.Limits(max_connections=2)) as client:
        while True:
            began = time.monotonic()
            try:
                if not initialized:
                    await asyncio.to_thread(init_archive,core.DATABASE_URL)
                    initialized = True
                stats = await asyncio.to_thread(capacity,core.DATABASE_URL)
                runtime.update(stats)
                if stats['archive_bytes']+MAX_SAMPLE_BYTES+8192>=MAX_ARCHIVE_BYTES:
                    runtime.update(status='archive_full',last_error=None)
                else:
                    if observer is None:
                        observer = SignalObserver(core)
                        context = observer.context()
                    sample = await capture(client,core.BINANCE_API)
                    sample['signals'] = await observer.evaluate(sample)
                    result = await asyncio.to_thread(store_sample,core.DATABASE_URL,run_id,context,sample,previous)
                    runtime.update(status='collecting' if result['saved'] else result['reason'],
                        last_error=None,last_sample=compact(sample),last_store=result,run_id=run_id)
                    if result['saved']:
                        runtime['last_saved_at'] = sample['finished_at']
                        previous = (result['bucket'],sample)
                    runtime.update(await asyncio.to_thread(capacity,core.DATABASE_URL))
                    print('RESEARCH_EVIDENCE',BUILD,result['reason'],'complete='+str(result.get('complete')),flush=True)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                runtime.update(status='error',last_error=type(exc).__name__+': '+str(exc))
                print('RESEARCH_EVIDENCE',type(exc).__name__,str(exc),flush=True)
            await asyncio.sleep(max(5,INTERVAL_SECONDS-(time.monotonic()-began)))


def install(app,core):
    from fastapi.responses import JSONResponse

    @app.on_event('startup')
    async def start():
        global _task
        if _task is None or _task.done():
            _task = asyncio.create_task(worker(core))

    @app.on_event('shutdown')
    async def stop():
        if _task:
            _task.cancel()
            try: await _task
            except asyncio.CancelledError: pass

    @app.get('/research/market-evidence/status')
    async def status():
        return JSONResponse({**runtime, 'running':bool(_task and not _task.done()),
            'trading_enabled':False,'scope':'Prospective sampled research evidence only; no profitability approval or trades.'},
            headers={'Cache-Control':'no-store'})
