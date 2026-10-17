from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.indicators import calculate_indicators
from app.strategy import evaluate_trend

BASE_URL = "https://api.binance.com/api/v3/klines"
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "FETUSDT", "RENDERUSDT", "NEARUSDT", "SUIUSDT", "AKTUSDT"]


def _parse_klines(rows: list[list[Any]], interval: str) -> list[dict[str, Any]]:
    durations = {"1h": 3600, "4h": 14400}
    if interval not in durations:
        raise ValueError("Only 1h and 4h intervals are supported.")
    candles = []
    for row in rows:
        candle = {
            "timestamp": datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc).isoformat(),
            "open": float(row[1]), "high": float(row[2]),
            "low": float(row[3]), "close": float(row[4]),
        }
        if min(candle["open"], candle["high"], candle["low"], candle["close"]) <= 0:
            raise ValueError("Binance returned non-positive OHLC values.")
        if candle["low"] > min(candle["open"], candle["close"]) or candle["high"] < max(candle["open"], candle["close"]) or candle["low"] > candle["high"]:
            raise ValueError("Binance returned invalid OHLC values.")
        candles.append(candle)
    candles.sort(key=lambda c: c["timestamp"])
    now = datetime.now(timezone.utc).timestamp()
    return [
        c for c in candles
        if datetime.fromisoformat(c["timestamp"]).timestamp() + durations[interval] <= now
    ]


async def _fetch_symbol(client: httpx.AsyncClient, symbol: str, interval: str) -> list[dict[str, Any]]:
    response = await client.get(BASE_URL, params={"symbol": symbol, "interval": interval, "limit": 240})
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"Unexpected Binance kline response for {symbol} {interval}.")
    candles = _parse_klines(payload, interval)
    if len(candles) < 220:
        raise ValueError(f"Only {len(candles)} completed candles for {symbol} {interval}; 220 required.")
    return candles


async def scan_binance_demo(symbols: list[str] | None = None) -> dict[str, Any]:
    """Read-only Binance Spot market scanner. It never signs requests or places orders."""
    requested = symbols or DEFAULT_SYMBOLS
    normalized = list(dict.fromkeys(s.upper().strip() for s in requested))
    if not normalized or len(normalized) > 20:
        raise ValueError("Supply between 1 and 20 symbols.")
    for symbol in normalized:
        if not symbol.isalnum() or len(symbol) < 5 or len(symbol) > 20:
            raise ValueError(f"Invalid Binance symbol: {symbol!r}.")
    results, errors = [], []
    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "MPV-PRO-V5-demo-scanner/1.0"}) as client:
        for symbol in normalized:
            try:
                hourly, four_hour = await asyncio.gather(
                    _fetch_symbol(client, symbol, "1h"),
                    _fetch_symbol(client, symbol, "4h"),
                )
                h, h4 = calculate_indicators(hourly), calculate_indicators(four_hour)
                sig1, sig4 = evaluate_trend(h), evaluate_trend(h4)
                change_24h = (hourly[-1]["close"] / hourly[-25]["close"] - 1) * 100
                aligned = sig1["action"] == sig4["action"] and sig1["action"] in ("BUY", "SELL")
                score = (2 if aligned and sig1["action"] == "BUY" else -2 if aligned and sig1["action"] == "SELL" else 0) + (1 if h.close > h.ema200 else -1) + max(-1, min(1, change_24h / 10))
                results.append({
                    "symbol": symbol, "price": h.close,
                    "change_24h_percent": round(change_24h, 3),
                    "rsi14_1h": round(h.rsi14, 2), "adx14_1h": round(h.adx14, 2),
                    "signal_1h": sig1["action"], "signal_4h": sig4["action"],
                    "signal": sig1["action"] if aligned else "HOLD",
                    "rotation_score": round(score, 3),
                    "last_completed_1h_candle": hourly[-1]["timestamp"],
                    "last_completed_4h_candle": four_hour[-1]["timestamp"],
                })
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                errors.append({"symbol": symbol, "error": str(exc)[:240]})
    results.sort(key=lambda item: item["rotation_score"], reverse=True)
    return {
        "provider": "Binance public Spot market data",
        "mode": "READ_ONLY_DEMO_RESEARCH",
        "symbols_requested": normalized, "results": results, "errors": errors,
        "live_execution_enabled": False, "authenticated": False,
        "warning": "This is public market data, not an authenticated Binance demo account. No account balance is read and no order is placed. Signals are research only; profitability is not implied.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
