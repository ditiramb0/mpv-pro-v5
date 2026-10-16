import pytest
from app.indicators import calculate_indicators

def rising_candles(count=240):
    candles = []
    for i in range(count):
        close = 100 + i * 0.2
        candles.append({
            "open": close - 0.05,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
        })
    return candles

def test_indicators_calculate_from_valid_ohlc_history():
    result = calculate_indicators(rising_candles())
    assert result.ema9 > result.ema21 > result.ema50 > result.ema200
    assert result.atr14 > 0
    assert result.bb_upper > result.bb_middle > result.bb_lower
    assert 0 <= result.rsi14 <= 100

def test_indicator_calculation_requires_warmup_history():
    with pytest.raises(ValueError):
        calculate_indicators(rising_candles(100))
