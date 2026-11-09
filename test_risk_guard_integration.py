"""Risk Guard zapojený do PAPER botů: blokuje jen NOVÉ vstupy, výstupy nikdy."""
import pytest
import lh_whale as lh
import liquidity_local as local
import risk_guard


def _signal(module, s, now=300010):
    return module.advance(s, dict(price=100, time=now), dict(candle=300000, signal='LONG', stop=98), now)


@pytest.mark.parametrize('module', [lh, local])
def test_entry_opens_normally_with_full_risk(module):
    s = module.initial(); s['activated_at'] = 1
    s = _signal(module, s)
    assert s['position'] and s['risk_guard']['last_decision'] == 'OK'


@pytest.mark.parametrize('module', [lh, local])
def test_kill_blocks_new_entry(module):
    s = module.initial(); s['activated_at'] = 1
    s['risk_guard'] = dict(risk_guard.update(None, 10000., 10000., 300000), killed=True, kill_reason='test')
    s = _signal(module, s)
    assert s['position'] is None and s['risk_guard']['last_decision'].startswith('KILL')


@pytest.mark.parametrize('module', [lh, local])
def test_throttle_halves_quantity(module):
    full = _signal(module, dict(module.initial(), activated_at=1))
    s = module.initial(); s['activated_at'] = 1; s['peak'] = 10000 / 0.94   # propad 6 % ⇒ ×0,5
    half = _signal(module, s)
    assert half['position']['qty'] == pytest.approx(full['position']['qty'] / 2, rel=1e-9)


@pytest.mark.parametrize('module', [lh, local])
def test_exit_still_runs_when_killed(module):
    s = _signal(module, dict(module.initial(), activated_at=1))
    assert s['position']
    s['risk_guard'] = dict(s['risk_guard'], killed=True, kill_reason='test')
    s = module.advance(s, dict(price=50, time=400000), None, 400000)   # cena pod stopem
    assert s['position'] is None and s['trades'] and s['trades'][0]['reason'] == 'STOP LOSS'
