from __future__ import annotations

from app.indicators import IndicatorSnapshot

def evaluate_trend(snapshot: IndicatorSnapshot, min_adx: float = 20.0) -> dict:
    """A deliberately simple baseline; not a validated profitable strategy."""
    long_checks = {
        "ema_alignment": snapshot.ema9 > snapshot.ema21 > snapshot.ema50 > snapshot.ema200,
        "macd_bullish": snapshot.macd > snapshot.macd_signal,
        "rsi_not_extreme": 50.0 <= snapshot.rsi14 <= 70.0,
        "trend_strength": snapshot.adx14 >= min_adx,
    }
    short_checks = {
        "ema_alignment": snapshot.ema9 < snapshot.ema21 < snapshot.ema50 < snapshot.ema200,
        "macd_bearish": snapshot.macd < snapshot.macd_signal,
        "rsi_not_extreme": 30.0 <= snapshot.rsi14 <= 50.0,
        "trend_strength": snapshot.adx14 >= min_adx,
    }
    long_score = sum(long_checks.values())
    short_score = sum(short_checks.values())
    action = "BUY" if long_score == len(long_checks) else "SELL" if short_score == len(short_checks) else "HOLD"
    return {
        "action": action,
        "strategy": "baseline_ema_macd_rsi_adx_v1",
        "long_score": long_score,
        "short_score": short_score,
        "required_score": len(long_checks),
        "checks": {"long": long_checks, "short": short_checks},
        "stop_loss_distance": 1.5 * snapshot.atr14,
        "take_profit_distance": 4.5 * snapshot.atr14,
        "risk_reward_ratio": "1:3",
        "warning": "Research baseline only; not backtested or financial advice. Include spread, fees and slippage in validation.",
    }
