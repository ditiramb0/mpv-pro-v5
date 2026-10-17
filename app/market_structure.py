from __future__ import annotations

from typing import Sequence


def analyze_market_structure(candles: Sequence[dict], swing_window: int = 3, max_patterns: int = 10) -> dict:
    """Heuristic market-structure scan for swings, BOS/CHoCH, FVGs, order blocks and sweeps.

    Pivot swings require bars on both sides, so the newest swing can only be confirmed
    after swing_window later candles. Definitions are explicit heuristics, not a
    universal or predictive interpretation of market structure.
    """
    if swing_window < 1 or swing_window > 10:
        raise ValueError("swing_window must be between 1 and 10.")
    if max_patterns < 1 or max_patterns > 50:
        raise ValueError("max_patterns must be between 1 and 50.")
    if len(candles) < swing_window * 2 + 5:
        raise ValueError(f"At least {swing_window * 2 + 5} candles are required.")

    rows = []
    for candle in candles:
        try:
            op, hi, lo, cl = (float(candle[k]) for k in ("open", "high", "low", "close"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Each candle must contain numeric open, high, low and close.") from exc
        if min(op, hi, lo, cl) <= 0 or lo > min(op, cl) or hi < max(op, cl) or lo > hi:
            raise ValueError("Each candle must have valid positive OHLC values.")
        rows.append({"open": op, "high": hi, "low": lo, "close": cl})

    highs = [c["high"] for c in rows]
    lows = [c["low"] for c in rows]
    closes = [c["close"] for c in rows]
    pivots_high = []
    pivots_low = []
    for i in range(swing_window, len(rows) - swing_window):
        left_h = highs[i - swing_window:i]
        right_h = highs[i + 1:i + swing_window + 1]
        left_l = lows[i - swing_window:i]
        right_l = lows[i + 1:i + swing_window + 1]
        if highs[i] > max(left_h) and highs[i] >= max(right_h):
            pivots_high.append({"index": i, "price": highs[i]})
        if lows[i] < min(left_l) and lows[i] <= min(right_l):
            pivots_low.append({"index": i, "price": lows[i]})

    last_high = pivots_high[-1] if pivots_high else None
    last_low = pivots_low[-1] if pivots_low else None
    previous_high = pivots_high[-2] if len(pivots_high) >= 2 else None
    previous_low = pivots_low[-2] if len(pivots_low) >= 2 else None
    latest_close = closes[-1]

    higher_highs = bool(previous_high and last_high and last_high["price"] > previous_high["price"])
    higher_lows = bool(previous_low and last_low and last_low["price"] > previous_low["price"])
    lower_highs = bool(previous_high and last_high and last_high["price"] < previous_high["price"])
    lower_lows = bool(previous_low and last_low and last_low["price"] < previous_low["price"])
    prior_trend = "bullish" if higher_highs and higher_lows else "bearish" if lower_highs and lower_lows else "undetermined"

    bullish_bos = bool(last_high and latest_close > last_high["price"])
    bearish_bos = bool(last_low and latest_close < last_low["price"])
    bullish_sweep = bool(last_low and lows[-1] < last_low["price"] and latest_close > last_low["price"])
    bearish_sweep = bool(last_high and highs[-1] > last_high["price"] and latest_close < last_high["price"])
    bullish_choch = bearish_bos and prior_trend == "bullish"
    bearish_choch = bullish_bos and prior_trend == "bearish"

    fvgs = []
    for i in range(max(2, len(rows) - 100), len(rows)):
        if lows[i] > highs[i - 2]:
            fvgs.append({"type": "bullish", "from_index": i - 2, "to_index": i, "lower": highs[i - 2], "upper": lows[i]})
        if highs[i] < lows[i - 2]:
            fvgs.append({"type": "bearish", "from_index": i - 2, "to_index": i, "lower": highs[i], "upper": lows[i - 2]})

    order_blocks = []
    if bullish_bos and last_high:
        for i in range(len(rows) - 2, max(-1, len(rows) - 22), -1):
            if rows[i]["close"] < rows[i]["open"]:
                order_blocks.append({"type": "bullish", "index": i, "lower": rows[i]["low"], "upper": rows[i]["high"], "trigger": "bullish_bos"})
                break
    if bearish_bos and last_low:
        for i in range(len(rows) - 2, max(-1, len(rows) - 22), -1):
            if rows[i]["close"] > rows[i]["open"]:
                order_blocks.append({"type": "bearish", "index": i, "lower": rows[i]["low"], "upper": rows[i]["high"], "trigger": "bearish_bos"})
                break

    return {
        "latest_close": latest_close,
        "prior_swing_trend": prior_trend,
        "swings": {
            "highs": pivots_high[-max_patterns:],
            "lows": pivots_low[-max_patterns:],
            "last_high": last_high,
            "last_low": last_low,
        },
        "events": {
            "bullish_bos": bullish_bos,
            "bearish_bos": bearish_bos,
            "bullish_choch": bullish_choch,
            "bearish_choch": bearish_choch,
            "bullish_liquidity_sweep": bullish_sweep,
            "bearish_liquidity_sweep": bearish_sweep,
        },
        "fair_value_gaps": fvgs[-max_patterns:],
        "order_blocks": order_blocks,
        "methodology_note": "Swing pivots use a symmetric lookback/lookforward window; FVGs use three-candle gaps; order blocks are the nearest opposite-colour candle before a detected close-based BOS. These are heuristic labels, not validated trading signals.",
    }
