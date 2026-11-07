"""C krok 0 — atribuce selhání (protokol research/maker_feasibility/PROTOCOL.md, de1088f).

Jen čte hotové results.json + trades.csv (žádná nová data, žádný backtest).
Pro zvolenou variantu, validaci, náklady x1: hrubý P/L (= čistý + náklady; funding zvlášť),
náklady, čistý, hrubý bez 3 nejlepších obchodů; lineární extrapolace na náklady 0,5x
z hotových sloupců x1/x2 (X(0,5) = X1 + 0,5*(X1 - X2)).
Použití: python failure_attribution.py <adresář s podadresáři <hypotéza>/results.json, trades.csv>
"""
import csv, json, sys, os

# hypotéza: (PR, zvolená varianta v trades.csv nebo None, cesta k strategii, cesta k B&H)
CFG = {
    'donchian_trend':   (11, 'N20_k2', 'grid/N20_k2/{p}/{x}', 'buy_hold/{p}/{x}'),
    'turn_of_month':    (12, 'ToM', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}'),
    'rsi2_pullback':    (13, 'RSI2', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}'),
    'sma200_overlay':   (14, 'SMA200', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}'),
    'vol_breakout':     (15, 'K05', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}'),
    'ts_momentum_vote': (16, 'H4_MONTHLY', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}'),
    'ethbtc_switch':    (17, 'SMA50', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}/basket_50_50'),
    'rebalance_band':   (18, 'band5', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}/basket_50_50'),
    'xrpbtc_switch':    (19, 'SMA50', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}/basket_50_50'),
    'ethbtc_meanrev':   (20, 'z2', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}/basket_50_50'),
    'funding_carry':    (23, 'H10', 'strategy/H10/{p}/{x}', 'buy_hold_50_50/{p}/{x}'),
    'rsi2_cross_asset': (24, None, 'basket/{p}/{x}', 'basket_bh/{p}/{x}'),
    'vol_target':       (27, 'BTC_T40', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}'),
    'near_high':        (28, 'TOP3', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}'),
    'contrarian_ladder':(31, 'L20_30_40', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}'),
    'bab_beta':         (32, 'W60_H14', 'strategy/{p}/{x}', 'buy_hold/{p}/{x}'),
}


def flat(o, p=''):
    """Zploští JSON na cesty 'a/b/c' (klíče typu "validation/x1" i vnoření dají stejnou cestu)."""
    out = {}
    if isinstance(o, dict):
        out[p.strip('/')] = o
        for k, v in o.items():
            out.update(flat(v, p + '/' + k))
    return out


def getp(F, tmpl, p, x):
    return F.get(tmpl.format(p=p, x=x))


def ledger(d, variant):
    rows = list(csv.DictReader(open(os.path.join(d, 'trades.csv'))))
    ck = 'cost_multiplier' if 'cost_multiplier' in rows[0] else 'cost_mult'
    sel = [r for r in rows if r['period'] == 'validation' and r[ck] == '1'
           and (variant is None or r.get('variant') == variant)
           and r.get('mode', 'strategy') in ('strategy', '', 'BAB')]
    f = lambda r, k: float(r[k]) if r.get(k) not in (None, '') else 0.0
    cost_k = 'fees' if 'fees' in rows[0] else 'costs'
    net = sum(f(r, 'net_pnl') for r in sel)
    cost = sum(f(r, cost_k) for r in sel)
    fund = sum(f(r, 'funding') for r in sel)
    gross_each = [f(r, 'net_pnl') + f(r, cost_k) for r in sel]  # před náklady, vč. fundingu
    g = sorted(gross_each, reverse=True)
    return dict(n=len(sel), net=net, cost=cost, funding=fund, gross=sum(gross_each),
                gross_wo_top3=sum(g[3:]))


def main(root):
    out = []
    for h, (pr, var, st, bh) in CFG.items():
        d = os.path.join(root, h)
        j = flat(json.load(open(os.path.join(d, 'results.json'))))
        s1, s2 = getp(j, st, 'validation', 'x1'), getp(j, st, 'validation', 'x2')
        b1 = getp(j, bh, 'validation', 'x1')
        L = ledger(d, var)
        ex = lambda k: s1[k] + 0.5 * (s1[k] - s2[k])
        row = dict(hyp=h, pr=pr, variant=var or 'basket', **{k: round(v, 2) if isinstance(v, float) else v for k, v in L.items()},
                   json_net_x1=round(s1['net_pnl'], 2),
                   sharpe_x1=round(s1['sharpe'], 3), sharpe_x05=round(ex('sharpe'), 3),
                   dd_x1=round(s1['max_drawdown_pct'], 2), dd_x05=round(ex('max_drawdown_pct'), 2),
                   net_x05=round(ex('net_pnl'), 2),
                   bh_sharpe=round(b1['sharpe'], 3), bh_dd=round(b1['max_drawdown_pct'], 2), bh_net=round(b1['net_pnl'], 2))
        f1, f2 = getp(j, st, 'final_test', 'x1'), getp(j, st, 'final_test', 'x2')
        fb = getp(j, bh, 'final_test', 'x1')
        exf = lambda k: f1[k] + 0.5 * (f1[k] - f2[k])
        row.update(final_net_x1=round(f1['net_pnl'], 2), final_net_x05=round(exf('net_pnl'), 2),
                   final_sharpe_x05=round(exf('sharpe'), 3), final_dd_x05=round(exf('max_drawdown_pct'), 2),
                   final_bh_net=round(fb['net_pnl'], 2), final_bh_sharpe=round(fb['sharpe'], 3), final_bh_dd=round(fb['max_drawdown_pct'], 2))
        row['c_A5_at_x05'] = (row['final_net_x05'] > 0 and row['final_sharpe_x05'] > row['final_bh_sharpe']
                              and row['final_dd_x05'] < row['final_bh_dd'])
        row['c_A2_trades_ge_30'] = s1.get('trades', L['n']) >= 30
        row['a_gross_pos'] = L['gross'] > 0 and L['gross_wo_top3'] > 0
        row['c_A1_at_x05'] = row['sharpe_x05'] > row['bh_sharpe'] and row['dd_x05'] < row['bh_dd']
        row['cost_share_of_gross_pct'] = round(100 * L['cost'] / L['gross'], 1) if L['gross'] > 0 else None
        out.append(row)
    return out


if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1]), ensure_ascii=False, indent=1))
