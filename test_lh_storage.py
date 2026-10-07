import asyncio
import os
import unittest
from unittest.mock import patch
import httpx
from fastapi import FastAPI
import lh_storage

class Tests(unittest.TestCase):
    def test_no_unauthorized_database_access(self):
        app=FastAPI()
        class Core: DATABASE_URL='not-a-real-database'
        lh_storage.install(app,Core())
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
                self.assertEqual((await c.get('/lh-whale/storage')).status_code,503)
                with patch.dict(os.environ,{'LH_STORAGE_TOKEN':'test-token'}):
                    self.assertEqual((await c.get('/lh-whale/storage')).status_code,401)
                    self.assertEqual((await c.put('/lh-whale/storage',json={})).status_code,401)
        asyncio.run(run())

    def test_execution_remains_local_to_europe_and_cas_is_used(self):
        calls=[]
        def call(method,payload=None):
            calls.append((method,payload))
            return {'state':{'n':1},'revision':'r1'} if method=='GET' else {'state':payload['state']}
        with patch.object(lh_storage,'remote_call',call):
            s=lh_storage.remote_tick({},None,1,lambda s,q,a,n:{'n':s['n']+1})
        self.assertEqual(s,{'n':2})
        self.assertEqual(calls[1][1]['expected'],'r1')

if __name__=='__main__': unittest.main()
