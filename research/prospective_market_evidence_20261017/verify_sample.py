"""Recompute an archived sample from its recorded context, with no network/DB.

Run from the matching source checkout:
  python research/prospective_market_evidence_20261017/verify_sample.py CONTEXT_JSON SAMPLE_JSON [SAMPLE_SHA256]
The JSON inputs are the decompressed research_market_runs.context and
research_market_samples.payload bytes, obtained through authorized DB access.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import app_v8 as indicators
import research_market_evidence as evidence


async def verify(context_path,sample_path,expected_hash=None):
    context=json.loads(Path(context_path).read_bytes())
    raw=Path(sample_path).read_bytes()
    checksum=hashlib.sha256(raw).hexdigest()
    if expected_hash and checksum!=expected_hash:
        raise ValueError('Sample checksum mismatch')
    for filename,expected in context['source_hashes'].items():
        if filename not in evidence.source_hashes() or hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()!=expected:
            raise ValueError('Use the original source checkout: '+filename)
    config={name:context['constants'][name] for name in evidence.CONSTANTS}
    config['ENABLED_SETUPS']=set(config['ENABLED_SETUPS'])
    core=SimpleNamespace(**config,**{name:getattr(indicators,name) for name in evidence.HELPERS},
                         trade_history=context['fly_setup_health_history'])
    sample=json.loads(raw)
    replayed=await evidence.SignalObserver(core).evaluate(sample)
    if replayed!=sample['signals']:
        raise ValueError('Recomputed signal filters do not match the recorded result')
    return dict(matches=True,sample_sha256=checksum,started_at=sample['started_at'],
                quality=sample['quality'],scope='Signal filter reproducibility only; no execution or profitability claim')


if __name__=='__main__':
    print(json.dumps(asyncio.run(verify(*sys.argv[1:])),indent=2))
