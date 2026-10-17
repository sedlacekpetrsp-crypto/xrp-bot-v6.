"""Post-result paired-entry audit; does not tune rules or acceptance gates."""
import argparse
import json
import math
import tarfile
from pathlib import Path


def run(out):
    dest = Path(out)
    summary = json.loads((dest / 'summary.json').read_text())
    previous = json.loads(Path('elite/results/20261014_v18/summary.json').read_text())
    assert summary['candidates']['v18_control'] == previous['candidates']['v18']
    with tarfile.open(dest / 'evidence.tar.gz') as archive:
        evidence = json.load(archive.extractfile('full_evidence.json'))
    report = {'phase': 'POST_RESULT_DIAGNOSTICS_NOT_SELECTION',
              'control_summary_exact': True, 'ledgers_reconciled': 0,
              'entry_signal_counts': summary['entry_signal_counts'], 'comparisons': {}}
    for periods in evidence.values():
        for runs in periods.values():
            for result in runs.values():
                trades = result['trade_log']
                assert math.isclose(sum(t['pnl'] for t in trades), result['net_pnl'], abs_tol=1e-7)
                assert all(a['exit_index'] < b['entry_index'] for a, b in zip(trades, trades[1:]))
                report['ledgers_reconciled'] += 1
    for mode in ('base', 'stress'):
        a = {t['entry_index']: t for t in evidence['v51']['continuous'][mode]['trade_log']}
        b = {t['entry_index']: t for t in evidence['v18_control']['continuous'][mode]['trade_log']}
        report['comparisons'][mode] = {
            'common_entries': len(a.keys() & b.keys()),
            'only_v51': [a[i] for i in sorted(a.keys() - b.keys())],
            'only_control': [b[i] for i in sorted(b.keys() - a.keys())],
            'common_exit_changes': [i for i in sorted(a.keys() & b.keys())
                                    if (a[i]['exit_index'], a[i]['reason']) !=
                                    (b[i]['exit_index'], b[i]['reason'])],
            'net_pnl_difference': evidence['v51']['continuous'][mode]['net_pnl'] -
                                  evidence['v18_control']['continuous'][mode]['net_pnl']}
    (dest / 'diagnostics.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    run(parser.parse_args().out)
