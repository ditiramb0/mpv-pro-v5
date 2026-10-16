from app.indicators import IndicatorSnapshot
from app.strategy import evaluate_trend

def make_snapshot(**overrides):
    values = dict(
        close=100, ema9=110, ema21=108, ema50=105, ema200=100,
        rsi14=60, macd=2, macd_signal=1, adx14=25,
        bb_upper=112, bb_middle=100, bb_lower=88, atr14=2,
    )
    values.update(overrides)
    return IndicatorSnapshot(**values)

def test_bullish_confluence_emits_buy_with_three_to_one_plan():
    result = evaluate_trend(make_snapshot())
    assert result["action"] == "BUY"
    assert result["risk_reward_ratio"] == "1:3"
    assert result["stop_loss_distance"] == 3
    assert result["take_profit_distance"] == 9

def test_mixed_signals_hold():
    result = evaluate_trend(make_snapshot(rsi14=80))
    assert result["action"] == "HOLD"

def test_bearish_confluence_emits_sell():
    result = evaluate_trend(make_snapshot(
        ema9=90, ema21=92, ema50=95, ema200=100,
        rsi14=40, macd=-2, macd_signal=-1, adx14=25,
    ))
    assert result["action"] == "SELL"
