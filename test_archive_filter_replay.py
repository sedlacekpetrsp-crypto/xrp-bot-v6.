import base64,gzip,hashlib,json,unittest
from types import SimpleNamespace
from research.archive_validation.compare_filters import restore

def packed(sample,bucket=0,parent=None):
    data=dict(sample)
    if parent is not None:data['_archive_base_bucket']=parent
    raw=json.dumps(sample,separators=(',',':')).encode()
    return dict(bucket=bucket,run_id='a',complete=True,sha256=hashlib.sha256(raw).hexdigest(),payload=base64.b64encode(gzip.compress(json.dumps(data).encode())).decode())

def expand(data,previous):
    return {k:v for k,v in data.items() if k!='_archive_base_bucket'}
E=SimpleNamespace(expand_sample=expand,json_bytes=lambda x:json.dumps(x,separators=(',',':')).encode())

class ReplayTests(unittest.TestCase):
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):list(restore([],'a',E))
    def test_timezone_required(self):
        with self.assertRaises(ValueError):list(restore([packed({'started_at':'1970-01-01T00:00:01'})],'a',E))
    def test_roundtrip(self):
        s={'started_at':'1970-01-01T00:00:01+00:00'}
        self.assertEqual(list(restore([packed(s)],'a',E)),[s])
    def test_rejects_bad_checksum_context_completeness(self):
        for change in [dict(sha256='bad'),dict(run_id='b'),dict(complete=False)]:
            row=packed({'started_at':'1970-01-01T00:00:01+00:00'});row.update(change)
            with self.assertRaises(ValueError):list(restore([row],'a',E))
    def test_delta_requires_exact_parent(self):
        a=packed({'started_at':'1970-01-01T00:00:01+00:00'})
        b=packed({'started_at':'1970-01-01T00:01:01+00:00'},1,parent=5)
        with self.assertRaises(ValueError):list(restore([a,b],'a',E))
    def test_gaps_and_duplicate(self):
        a=packed({'started_at':'1970-01-01T00:00:01+00:00'})
        b=packed({'started_at':'1970-01-01T00:02:01+00:00'},2)
        for rows in ([a,b],[a,a]):
            with self.assertRaises(ValueError):list(restore(rows,'a',E))
    def test_time_bucket_mismatch(self):
        with self.assertRaises(ValueError):list(restore([packed({'started_at':'1970-01-01T00:01:01+00:00'})],'a',E))

if __name__=='__main__':unittest.main()
