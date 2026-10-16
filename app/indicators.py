from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class IndicatorSnapshot:
    close: float
    ema9: float
    ema21: float
    ema50: float
    ema200: float
    rsi14: float
    macd: float
    macd_signal: float
    adx14: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    atr14: float

def _ema(values: Sequence[float], period: int) -> list[float]:
    alpha = 2.0 / (period + 1.0)
    out: list[float] = []
    for value in values:
        out.append(value if not out else alpha * value + (1.0 - alpha) * out[-1])
    return out

def _rsi(closes: Sequence[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        raise ValueError(f"RSI requires at least {period + 1} closes.")
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(x, 0.0) for x in changes]
    losses = [max(-x, 0.0) for x in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)

def _atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        raise ValueError(f"ATR requires at least {period + 1} candles.")
    trs = []
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    value = sum(trs[:period]) / period
    for tr in trs[period:]:
        value = (value * (period - 1) + tr) / period
    return value

def _adx(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float:
    if len(closes) < period * 2 + 1:
        raise ValueError(f"ADX requires at least {period * 2 + 1} candles.")
    trs, plus_dm, minus_dm = [], [], []
    for i in range(1, len(closes)):
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
        trs.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
    def smooth(series):
        v = sum(series[:period])
        vals = [v]
        for x in series[period:]:
            v = v - v / period + x
            vals.append(v)
        return vals
    tr_s, p_s, m_s = smooth(trs), smooth(plus_dm), smooth(minus_dm)
    dx = []
    for tr, p, m in zip(tr_s, p_s, m_s):
        if tr <= 0:
            dx.append(0.0)
        else:
            pdi, mdi = 100 * p / tr, 100 * m / tr
            denom = pdi + mdi
            dx.append(0.0 if denom == 0 else 100 * abs(pdi-mdi) / denom)
    if len(dx) < period:
        raise ValueError("Not enough data to calculate ADX.")
    value = sum(dx[:period]) / period
    for x in dx[period:]:
        value = (value * (period - 1) + x) / period
    return value

def calculate_indicators(candles: Sequence[dict]) -> IndicatorSnapshot:
    if len(candles) < 220:
        raise ValueError("At least 220 candles are required for EMA 200 and indicator warm-up.")
    opens = [float(c["open"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    if any(not (lo <= min(op, cl) <= max(op, cl) <= hi) for op, hi, lo, cl in zip(opens, highs, lows, closes)):
        raise ValueError("Each candle must have valid OHLC values.")
    ema9, ema21, ema50, ema200 = (_ema(closes, p)[-1] for p in (9, 21, 50, 200))
    fast, slow = _ema(closes, 12), _ema(closes, 26)
    macd_series = [a-b for a, b in zip(fast, slow)]
    macd_signal = _ema(macd_series, 9)[-1]
    window = closes[-20:]
    mean = sum(window) / 20
    variance = sum((x-mean)**2 for x in window) / 20
    sd = variance ** 0.5
    return IndicatorSnapshot(
        close=closes[-1], ema9=ema9, ema21=ema21, ema50=ema50, ema200=ema200,
        rsi14=_rsi(closes), macd=macd_series[-1], macd_signal=macd_signal,
        adx14=_adx(highs, lows, closes), bb_upper=mean+2*sd, bb_middle=mean,
        bb_lower=mean-2*sd, atr14=_atr(highs, lows, closes),
    )
