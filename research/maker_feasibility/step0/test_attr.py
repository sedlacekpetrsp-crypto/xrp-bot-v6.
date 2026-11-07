import os,unittest
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'attr.py')).read().split('summary=[]')[0]
src=src.replace("import json,glob,os,sys","import json,glob,os,sys\nsys.argv=sys.argv[:1]+['.']")
ns={}; exec(src,ns)
class T(unittest.TestCase):
    def test_gross_from_fees_and_slippage(self):
        out=[]; ns['walk']({'a':{'net_pnl':-10,'fees':15,'slippage_cost':5,'trades':3}},'',out)
        self.assertEqual(out[0][3],10); self.assertEqual(out[0][2],20)
    def test_costs_field_and_explicit_gross(self):
        out=[]; ns['walk']({'x1':{'net_pnl':-5,'costs':7},'y':{'net_pnl':1,'gross_before_fees_and_slippage':4}},'',out)
        d={p:g for p,n,c,g,_,_ in out}; self.assertEqual(d['/x1'],2); self.assertEqual(d['/y'],4)
    def test_bool_ignored(self):
        out=[]; ns['walk']({'net_pnl':True,'fees':1},'',out); self.assertEqual(out,[])
if __name__=='__main__': unittest.main()
