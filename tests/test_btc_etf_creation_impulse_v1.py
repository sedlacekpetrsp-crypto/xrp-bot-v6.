import unittest
from dataclasses import replace
from research.btc_etf_creation_impulse_v1 import Config,DAY,backtest,make_signals,parse_farside_html

HTML=b'''<table class="etf"><tbody><tr><td>11 Jan 2024</td><td>111.7</td><td>227.0</td><td>237.9</td><td>65.3</td><td>17.4</td><td>50.1</td><td>29.4</td><td>10.6</td><td>1.0</td><td>-</td><td><span>(95.1)</span></td><td>-</td><td>655.3</td></tr><tr><td>12 Jan 2024</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>(20.0)</td></tr></tbody></table>'''
def bars(n=80):return [dict(timestamp=i*DAY,open=100.,high=101.,low=99.,close=100.) for i in range(n)]
class Tests(unittest.TestCase):
    def test_parse_sign_and_missing(self):
        x=parse_farside_html(HTML);self.assertEqual(len(x),2);self.assertEqual(x[0]['fund_values'][9],None);self.assertEqual(x[0]['fund_values'][10],-95.1);self.assertEqual(x[1]['total_flow'],-20.)
    def test_positive_only_and_two_day_lag(self):
        x=parse_farside_html(HTML);s=make_signals(x);self.assertEqual(list(s),[x[0]['timestamp']+2*DAY]);self.assertEqual(s[list(s)[0]]['total_flow'],655.3)
    def test_future_invariance(self):
        x=parse_farside_html(HTML);a=make_signals(x[:1]);x[1]['total_flow']=999.;self.assertEqual(a,{k:v for k,v in make_signals(x).items() if k<x[1]['timestamp']+2*DAY})
    def test_unsorted_rejected(self):
        with self.assertRaises(ValueError):parse_farside_html(HTML.replace(b'12 Jan 2024',b'10 Jan 2024'))
    def test_stop_first_and_stress(self):
        r=bars();r[30]['etf_signal']=dict(flow_timestamp=28*DAY,total_flow=10.);r[30].update(high=120,low=80);a,_=backtest(r,0,10**18);b,_=backtest(r,0,10**18,replace(Config(),fee=.0019,slippage=.0004));self.assertEqual(a[0]['reason'],'STOP');self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_gap_stop_sizing_and_cap(self):
        r=bars();r[30]['etf_signal']=dict(flow_timestamp=28*DAY,total_flow=10.);r[31].update(open=80,high=81,low=79,close=80);t,_=backtest(r,0,10**18);self.assertEqual(t[0]['reason'],'GAP_STOP');self.assertLessEqual(t[0]['leg_notional'],2000+1e-8);self.assertLessEqual(t[0]['qty']*(t[0]['entry']-t[0]['stop']),50+1e-8)
    def test_nonoverlap(self):
        r=bars();r[30]['etf_signal']=dict(flow_timestamp=28*DAY,total_flow=10.);r[31]['etf_signal']=dict(flow_timestamp=29*DAY,total_flow=20.);self.assertEqual(len(backtest(r,0,10**18)[0]),1)
if __name__=='__main__':unittest.main()
