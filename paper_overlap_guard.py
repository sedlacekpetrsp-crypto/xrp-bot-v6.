"""Candidate shared-asset admission policy. No I/O, sizing, or exit changes."""

def asset_key(symbol):
    symbol = str(symbol or '').upper().replace('/', '').replace('-', '')
    for quote in ('USDC', 'USDT', 'USD'):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol[:-len(quote)]
    return None


def entry_allowed(symbol, side, positions):
    asset = asset_key(symbol)
    if not asset or side not in ('LONG', 'SHORT'):
        return False, 'INVALID_ENTRY'
    for position in positions:
        if not isinstance(position, dict) or not asset_key(position.get('symbol')):
            return False, 'UNKNOWN_OPEN_EXPOSURE'
        if asset_key(position['symbol']) == asset:
            return False, 'ASSET_ALREADY_OPEN'
    return True, 'ASSET_AVAILABLE'
