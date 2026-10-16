"""Post-fix exact historical replay and real-data prefix causality audit."""
import argparse,hashlib,json,tarfile,io,unittest
from pathlib import Path
from elite.research_data import load_cached
from elite.research_engine import simulate
from elite.cross_market_v18 import decisions as cross
from elite.session_v49 import decisions as session
from elite.loss_overlay_v38 import LossOverlay


def run(cache,out):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    report={'phase':'ENGINE_VALIDATION_AUDIT_NOT_SELECTION','paper_eligible':[],
            'replays':{},'real_data_prefix_checks':{},'references':{}}
    suite=unittest.defaultTestLoader.discover('elite',pattern='test_*.py')
    capture=io.StringIO();tests=unittest.TextTestRunner(stream=capture).run(suite)
    (dest/'tests.txt').write_text(capture.getvalue())
    report['tests']={'run':tests.testsRun,'failures':len(tests.failures),'errors':len(tests.errors)}
    if not tests.wasSuccessful():raise AssertionError('unit audit failed')
    rows,xm=load_cached(cache);btc,bm=load_cached(cache,symbol='BTCUSDT')
    report['data_manifest']={'XRPUSDT':xm,'BTCUSDT':bm}
    base=cross(rows,btc,'v18');opening=session(rows,'v49')
    cut=len(rows)//2+5
    for name,stream,prefix in [('v18',base,cross(rows[:cut],btc[:cut],'v18')),
                               ('v49',opening,session(rows[:cut],'v49'))]:
        assert prefix=={i:d for i,d in stream.items() if i<cut}
        report['real_data_prefix_checks'][name]={'cutoff_index':cut,'passed':True,'decisions':len(prefix)}
    streams={'v18':base,'v38':LossOverlay(rows,base,{},'v38'),'v49':opening}
    paths={'v18':'20261014_v18','v38':'20261015_v38','v49':'20261015_v49'}
    for name,sig in streams.items():
        path=Path('elite/results')/paths[name]/'evidence.tar.gz'
        report['references'][name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        with tarfile.open(path) as archive:previous=json.load(archive.extractfile('full_evidence.json'))[name]['continuous']
        report['replays'][name]={}
        for mode,scale in [('base',1),('stress',2)]:
            current=simulate(rows,sig,fee=.001*scale,slip=.0003*scale,half_spread=.0001*scale)
            # Normalize integer date keys exactly as historical JSON storage did.
            normalized=json.loads(json.dumps(current,allow_nan=False))
            assert normalized==previous[mode],(name,mode,'full evidence changed')
            digest=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            report['replays'][name][mode]={'full_evidence_exact_match':True,'sha256':digest,'trades':current['trades'],
                                         'net_pnl':current['net_pnl'],'daily_points':len(current['daily_equity'])}
            print(name,mode,'EXACT_FULL_MATCH',current['trades'],flush=True)
    sources=['elite/engine_audit.py','elite/test_engine_audit.py','elite/research_engine.py',
             'elite/research_data.py','elite/cross_market_v18.py','elite/session_v49.py','elite/loss_overlay_v38.py']
    report['code_sha256']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources}
    (dest/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print('AUDIT_PASS',report['tests'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.cache,a.out)
