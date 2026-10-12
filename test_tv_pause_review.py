import asyncio,bisect,copy,unittest
from datetime import datetime,timezone
from types import SimpleNamespace
from test_exit_regressions import functions

class PauseTests(unittest.TestCase):
    def test_pause_blocks_entries_and_retains_position_management(self):
        for position in (None,{'side':'LONG'}):
            calls=[]
            async def cycle():calls.append(True)
            module=SimpleNamespace(cycle=cycle,state={'open_position':position,'balance':10000})
            env={'PAUSED_BOTS':{'TV'},'datetime':datetime,'timezone':timezone}
            install=functions('app_v8_fly.py',{'_install_pause_cycle'},env)['_install_pause_cycle']
            install(module,'TV');asyncio.run(module.cycle())
            self.assertEqual(len(calls),int(position is not None))
            self.assertEqual(module.state['status'],'paused')
            self.assertTrue(module.state['trading_paused'])
    def test_changing_future_close_does_not_change_available_input(self):
        rows=[[0,100,999,1,900,10000,59999],[60000,101,999,1,800,99999,119999]]
        env={'frames':{'1m':rows},'ends':{'1m':[59999,119999]},'clock':[60000],'bisect':bisect}
        get=functions('research/tv_validation_20261012/run.py',{'klines'},env)['klines']
        first=asyncio.run(get('XRP','1m'))
        rows[1][2:6]=[999999,.001,900000,100000]
        self.assertEqual(asyncio.run(get('XRP','1m')),first)
        self.assertEqual(first[-1][1:6],[101,101,101,101,0])
        self.assertEqual(first[-2],rows[0])

if __name__=='__main__':unittest.main()
