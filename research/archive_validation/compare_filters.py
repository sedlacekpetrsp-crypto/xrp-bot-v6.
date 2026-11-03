"""Replay recorded signal filters offline; no orders, fills or PnL simulation.

Usage: compare_filters.py BASELINE_DIR CANDIDATE_DIR CONTEXT_EXPORT SAMPLES_EXPORT
Exports are private JSON rows: context(id,context base64 gzip), samples
(bucket,run_id,complete,payload base64 gzip,sha256), starting at a full checkpoint.
Never upload the exports to a public repository.
"""
import asyncio,base64,collections,copy,gzip,hashlib,importlib.util,json,pathlib,sys
from datetime import datetime
from types import SimpleNamespace


def restore(rows, context_id, evidence):
    if not rows:raise ValueError("No archived samples supplied")
    previous=None;previous_bucket=None
    for row in sorted(rows,key=lambda r:r['bucket']):
        bucket=row['bucket']
        if previous_bucket is not None and bucket!=previous_bucket+1:
            raise ValueError('Gap or duplicate: split into continuous segments first')
        if row['run_id']!=context_id or row['complete'] is not True:
            raise ValueError('Incomplete sample or wrong frozen context')
        packed=json.loads(gzip.decompress(base64.b64decode(row['payload'])))
        parent=packed.get('_archive_base_bucket')
        if parent is not None and (previous_bucket is None or parent!=previous_bucket):
            raise ValueError('Missing or wrong delta parent')
        sample=evidence.expand_sample(packed,previous)
        if hashlib.sha256(evidence.json_bytes(sample)).hexdigest()!=row['sha256']:
            raise ValueError('Sample checksum mismatch')
        stamp=datetime.fromisoformat(sample['started_at'])
        if stamp.tzinfo is None:raise ValueError('Timezone required')
        if int(stamp.timestamp())//60!=bucket:
            raise ValueError('Timestamp does not match minute bucket')
        previous=sample;previous_bucket=bucket
        yield sample


def module_at(root,name):
    spec=importlib.util.spec_from_file_location('candidate_'+name,pathlib.Path(root)/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


async def compare(baseline,candidate,context_path,samples_path):
    baseline=pathlib.Path(baseline).resolve();candidate=pathlib.Path(candidate).resolve()
    sys.path.insert(0,str(baseline))
    import app_v8 as indicators
    import research_market_evidence as evidence
    contexts=json.loads(pathlib.Path(context_path).read_text())
    if len(contexts)!=1:raise ValueError('Exactly one frozen context required')
    context_row=contexts[0]
    context=json.loads(gzip.decompress(base64.b64decode(context_row['context'])))
    for name,digest in context['source_hashes'].items():
        if name not in evidence.source_hashes() or hashlib.sha256((baseline/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Baseline source differs from archived context: '+name)
    config={name:context['constants'][name] for name in evidence.CONSTANTS}
    config['ENABLED_SETUPS']=set(config['ENABLED_SETUPS'])
    core=SimpleNamespace(**config,**{name:getattr(indicators,name) for name in evidence.HELPERS},trade_history=context['fly_setup_health_history'])
    observer=evidence.SignalObserver(core)
    fly=module_at(candidate,'v8_fly_layer');fly.m=observer.core
    fast=module_at(candidate,'fast_scalper');fast.base=observer.core
    labels=[v+':'+b for v in ('baseline','candidate') for b in ('FLY_CLOSED','FLY_ARMED','FAST')]
    counts=collections.Counter({k:0 for k in labels+['verified_samples','LEADLAG_signal_samples']})
    blockers=collections.Counter();unique={k:set() for k in labels}
    rows=json.loads(pathlib.Path(samples_path).read_text());first=last=None
    for sample in restore(rows,context_row['id'],evidence):
        replay=await observer.evaluate(sample)
        if replay!=sample['signals']:raise ValueError('Recorded signal replay mismatch')
        counts['verified_samples']+=1
        first=first or sample['started_at'];last=sample['started_at']
        for row in replay['fly']:
            for label,engine in [('baseline',observer.fly),('candidate',fly)]:
                reason=engine.entry_blocker(copy.deepcopy(row))
                blockers[label+':FLY:'+str(reason)]+=1
                if reason is None:
                    key=label+':FLY_CLOSED';counts[key]+=1
                    unique[key].add((row['symbol'],row['candle_time'],row['signal']))
                armed=engine.armed_candidate(copy.deepcopy(row))
                if armed:
                    key=label+':FLY_ARMED';counts[key]+=1
                    unique[key].add((armed['symbol'],armed['candle_time'],armed['signal']))
            for label,engine in [('baseline',observer.fast),('candidate',fast)]:
                a=engine._fast_signal(copy.deepcopy(row))
                for reason in a['fast_blockers']:blockers[label+':FAST:'+reason]+=1
                if a['fast_signal'] in ('LONG','SHORT'):
                    key=label+':FAST';counts[key]+=1
                    unique[key].add((a['symbol'],a['candle_time'],a['fast_signal']))
        if (replay.get('leadlag') or {}).get('signal') in ('LONG','SHORT'):counts['LEADLAG_signal_samples']+=1
    return dict(scope='Signal eligibility only. ARMED is not a triggered fill. No positions, sizing, exits, fees or PnL simulated.',
                first_sample=first,last_sample=last,counts=dict(counts),
                unique_signal_candles={k:len(v) for k,v in unique.items()},blockers=dict(blockers),
                candidate_hashes={n:hashlib.sha256((candidate/n).read_bytes()).hexdigest() for n in ['v8_fly_layer.py','fast_scalper.py']})

if __name__=='__main__':
    if len(sys.argv)!=5:raise SystemExit(__doc__)
    print(json.dumps(asyncio.run(compare(*sys.argv[1:])),indent=2))
