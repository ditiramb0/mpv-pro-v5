from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import settings


INTERVALS = {
    "1m": ("1min", timedelta(minutes=1)),
    "5m": ("5min", timedelta(minutes=5)),
    "15m": ("15min", timedelta(minutes=15)),
    "30m": ("30min", timedelta(minutes=30)),
    "1h": ("1h", timedelta(hours=1)),
    "2h": ("2h", timedelta(hours=2)),
    "4h": ("4h", timedelta(hours=4)),
    "1d": ("1day", timedelta(days=1)),
    "1w": ("1week", timedelta(weeks=1)),
}


def normalize_symbol(ticker: str, market: str) -> str:
    symbol = ticker.strip().upper().replace(" ", "")
    if "/" in symbol:
        parts = symbol.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("Ticker pair must use BASE/QUOTE format.")
        return f"{parts[0]}/{parts[1]}"
    if market == "forex" and len(symbol) == 6 and symbol.isalpha():
        return f"{symbol[:3]}/{symbol[3:]}"
    if market == "crypto":
        for quote in ("USDT", "USDC", "USD", "BTC", "ETH", "EUR"):
            if symbol.endswith(quote) and len(symbol) > len(quote):
                return f"{symbol[:-len(quote)]}/{quote}"
    raise ValueError("Use a supported pair such as EUR/USD or BTC/USD.")


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


async def fetch_candles(ticker: str, market: str, timeframe: str, limit: int = 220) -> dict[str, Any]:
    if not settings.twelve_data_api_key:
        raise RuntimeError("TWELVE_DATA_API_KEY is not configured.")
    if timeframe not in INTERVALS:
        raise ValueError(f"Unsupported timeframe: {timeframe}.")
    if not 15 <= limit <= 1000:
        raise ValueError("limit must be between 15 and 1000.")

    symbol = normalize_symbol(ticker, market)
    provider_interval, duration = INTERVALS[timeframe]
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": symbol,
                "interval": provider_interval,
                "outputsize": limit,
                "timezone": "UTC",
                "apikey": settings.twelve_data_api_key,
            },
        )
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, dict) or payload.get("status") == "error":
        message = payload.get("message", "Unexpected response") if isinstance(payload, dict) else "Unexpected response"
        raise ValueError(f"Twelve Data error: {message}")
    values = payload.get("values")
    if not isinstance(values, list):
        raise ValueError("Twelve Data response did not contain candle values.")

    now = datetime.now(timezone.utc)
    candles = []
    for row in values:
        try:
            opened = _parse_timestamp(str(row["datetime"]))
            candle = {
                "timestamp": opened.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Twelve Data returned a malformed candle.") from exc
        if min(candle["open"], candle["high"], candle["low"], candle["close"]) <= 0:
            raise ValueError("Twelve Data returned non-positive OHLC values.")
        if candle["low"] > min(candle["open"], candle["close"]) or candle["high"] < max(candle["open"], candle["close"]) or candle["low"] > candle["high"]:
            raise ValueError("Twelve Data returned invalid OHLC values.")
        # Exclude an unfinished current candle to reduce repainting/look-ahead risk.
        if opened + duration <= now:
            candles.append(candle)

    candles.sort(key=lambda candle: candle["timestamp"])
    if not candles:
        raise ValueError("No completed candles were returned for this symbol and timeframe.")
    return {
        "provider": "Twelve Data",
        "ticker": symbol,
        "market": market,
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
        "note": "Only completed candles are returned. Provider coverage, history depth, plan limits, and licensing vary by symbol and account.",
    }
