from research.whale_short_rsi_shadow import evaluate

def candidate(side="SHORT", rsi=50, strategy="FIB_618_786"):
    return {"strategy": strategy, "side": side, "candidate_entry": 1.25,
            "candidate_key": "test-1", "symbol": "XRPUSDT",
            "technical_details": {"1h": {"rsi": rsi}}}

def test_valid_short_is_shadow_only():
    result = evaluate(candidate())
    assert result["status"] == "SHADOW_ONLY_NO_ORDERS"
    assert result["side"] == "SHORT"

def test_long_rejected():
    assert evaluate(candidate(side="LONG")) is None

def test_outside_rsi_rejected():
    assert evaluate(candidate(rsi=61)) is None
    assert evaluate(candidate(rsi=39)) is None

def test_other_strategy_rejected():
    assert evaluate(candidate(strategy="VWAP_REVERSION")) is None

def test_missing_data_rejected():
    assert evaluate({}) is None
