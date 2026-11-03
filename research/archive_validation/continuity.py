"""Offline segmentation of minute research metadata; never starts trading.

Input: JSON rows with bucket (UTC epoch minute), run_id, complete.
Usage: python continuity.py /private/metadata.json
Complete snapshots are not necessarily a continuous replay dataset.
"""
import json
import sys


def segments(rows):
    rows=sorted(rows,key=lambda r:r['bucket'])
    seen=set();result=[];current=None;invalid=0;missing=0;previous=None
    for row in rows:
        bucket=row['bucket'];run=row['run_id']
        if isinstance(bucket,bool) or not isinstance(bucket,int) or bucket<0:
            raise ValueError('Invalid minute bucket')
        if bucket in seen:raise ValueError('Duplicate minute bucket')
        seen.add(bucket)
        if not isinstance(run,str) or not run:raise ValueError('Missing run context')
        if type(row['complete']) is not bool:raise ValueError('Invalid completeness flag')
        if previous is not None:missing+=bucket-previous-1
        previous=bucket
        if not row['complete']:
            invalid+=1;current=None;continue
        if current is None or current['run_id']!=run or bucket!=current['last_bucket']+1:
            current=dict(run_id=run,first_bucket=bucket,last_bucket=bucket,samples=1)
            result.append(current)
        else:
            current['last_bucket']=bucket;current['samples']+=1
    return dict(total_samples=len(rows),incomplete_samples=invalid,missing_minutes=missing,
                continuous_segments=result,
                longest_segment_samples=max((s['samples'] for s in result),default=0),
                scope='Continuity only. Does not verify payload hashes, source equivalence, fills or profitability.')

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: continuity.py /private/metadata.json')
    with open(sys.argv[1]) as f:print(json.dumps(segments(json.load(f)),indent=2))
