import re,unittest
from pathlib import Path
from test_exit_regressions import functions

BASE=Path('app_v8.py').read_text()
HTML=re.search(r'<!doctype html>[\s\S]*?</html>',BASE).group(0)

def hide():
    env=functions('app_v8_fly.py',{'_hide_paused_fly_cards'},{})
    src=Path('app_v8_fly.py').read_text()
    env['FLY_DASHBOARD_CARDS']=eval(re.search(r'FLY_DASHBOARD_CARDS = (\([\s\S]*?\n\))',src).group(1))
    return env['_hide_paused_fly_cards']

class HidePausedFlyTests(unittest.TestCase):
    def test_base_dashboard_contains_all_fly_cards(self):
        for card in ('<div class="card"><div id="stats" class="grid"></div></div>',
                     '<div class="card"><h2>📌 Otevřená pozice</h2>','<div class="card" id="flyTradesCard" style="display:none">'):
            self.assertIn(card,HTML)
    def test_paused_fly_cards_hidden_but_kept_in_dom(self):
        out=hide()(HTML,frozenset({'FLY','TV'}))
        self.assertEqual(out.count('data-paused-bot="FLY"'),3)
        self.assertIn('id="stats"',out); self.assertIn('id="position"',out); self.assertIn('id="trades"',out)
        self.assertIn('.card:has(> #stats)',out)
        self.assertNotIn('<div class="card"><div id="stats"',out)
        self.assertIn('id="health"',out)          # health card stays visible
    def test_running_fly_unchanged(self):
        self.assertEqual(hide()(HTML,frozenset({'TV'})),HTML)
    def test_route_applies_helper_before_response(self):
        src=Path('app_v8_fly.py').read_text()
        body=src[src.index('async def dashboard_with_pnl_breakdown'):]
        body=body[:body.index('\n@app.')]
        self.assertLess(body.index('_hide_paused_fly_cards(html, PAUSED_BOTS)'),body.rindex('return HTMLResponse'))

if __name__=='__main__':unittest.main()
