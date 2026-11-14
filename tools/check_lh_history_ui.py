"""Isolated browser check of actual dashboard HTML/CSS; no workers, network or DB."""
import ast
import asyncio
import importlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lh_whale_dashboard

OUT = Path('ui-check-artifacts')
OUT.mkdir(exist_ok=True)

def function(path, name, scope):
    tree = ast.parse(Path(path).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), scope)
    return scope[name]

async def build():
    original = function('app_v8.py', 'dashboard', {})
    scope = {'_original_dashboard': original, 'HTMLResponse': lambda value, **kw: value,
             'PAUSED_BOTS': frozenset({'FLY','FAST','LEADLAG','TV','WHALE','BEST'})}
    for name in ['news_dashboard','swing_dashboard','lh_whale_dashboard']:
        scope[name] = importlib.import_module(name)
    html = await function('app_v8_fly.py', 'dashboard_with_pnl_breakdown', scope)()
    # Preserve generated DOM and every style; isolate JS to the exact shared helper and LH module.
    scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
    shared = next(s for s in scripts if 'function renderTradeHistory(' in s)
    shared = shared[shared.index('function historyEscape'):shared.index('async function refreshFlyGuard')]
    f = re.search(r'const f=.*?;', Path('app_v8.py').read_text()).group()
    html = re.sub(r'<script>.*?</script>', '', html, flags=re.S)
    return html.replace('</body>', '<script>'+f+shared+'</script>'+lh_whale_dashboard.SCRIPT+'</body>')

async def main():
    from playwright.async_api import async_playwright
    html = await build()
    trade = dict(symbol='XRPUSDT',side='SHORT',pnl=49.139413568378586,closed_at='2026-11-14T07:20:27Z',
                 entry_price=.998100,exit_price=.983097,reason='TAKE PROFIT',fees=3.47)
    data = dict(healthy=True,running=True,balance=10049.139413568379,equity=10049.139413568379,
                net_pnl=49.139413568378586,trades_count=1,win_rate=100,positions=[],trades=[trade],
                market_price=.9723,analysis={'signal':'WAIT','reason':'Čekám na sweep + reclaim + 15m/1h trend + volume'},
                persistence='postgres',last_cycle_at='2026-11-14T15:00:00Z')
    report=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        for width in [360,393,709,1280]:
            page=await browser.new_page(viewport={'width':width,'height':900}, device_scale_factor=1)
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            async def route(r):
                if r.request.url=='http://lh-test/': await r.fulfill(content_type='text/html',body=html)
                elif r.request.url=='http://lh-test/lh-whale/status': await r.fulfill(json=data)
                else: await r.abort()
            await page.route('**/*',route)
            await page.goto('http://lh-test/')
            history=page.locator('#lhWhaleHistory')
            await history.locator('.history-row:not(.history-heading)').wait_for()
            assert await history.locator('.history-heading span').count()==4
            assert '49.14 USDT' in await history.inner_text()
            assert '08:20:27' in await history.inner_text()
            await history.locator('summary').click()
            assert not await history.evaluate('(e)=>e.open')
            await page.evaluate('refreshLHWhale()')
            assert not await history.evaluate('(e)=>e.open')
            await page.locator('[data-lh-history]').click()
            assert await history.evaluate('(e)=>e.open')
            await page.evaluate('refreshLHWhale()')
            assert await history.evaluate('(e)=>e.open')
            await history.scroll_into_view_if_needed()
            assert not await page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'horizontal page overflow'
            boxes=await history.locator('.history-row:not(.history-heading)>span').evaluate_all('(els)=>els.map(e=>{let r=e.getBoundingClientRect();return {x:r.x,right:r.right,y:r.y}})')
            assert len(boxes)==4 and all(boxes[i]['right']<=boxes[i+1]['x']+1 for i in range(3)), boxes
            assert await page.locator('a[href="/combined"]').evaluate('(e)=>getComputedStyle(e.parentElement).position')!='fixed'
            await history.screenshot(path=str(OUT/f'history-{width}.png'))
            await page.locator('#lhWhaleStatus').screenshot(path=str(OUT/f'card-{width}.png'))
            assert not errors, errors
            report.append({'width':width,'status':'PASS','columns':boxes})
            await page.close()
        await browser.close()
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    asyncio.run(main())
