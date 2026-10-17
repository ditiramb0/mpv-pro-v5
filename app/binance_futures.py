from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

BASE_URL = "https://fapi.binance.com"
DEFAULT_FUTURES_SYMBOLS = ["BTCUSDT", "ETHUSDT", "FETUSDT", "RENDERUSDT", "NEARUSDT", "SUIUSDT", "AKTUSDT"]


async def _get_json(client: httpx.AsyncClient, path: str, params: dict[str, str]) -> Any:
    response = await client.get(f"{BASE_URL}{path}", params=params)
    response.raise_for_status()
    return response.json()


async def _fetch_futures_symbol(client: httpx.AsyncClient, symbol: str) -> dict[str, Any]:
    premium, interest, ticker = await asyncio.gather(
        _get_json(client, "/fapi/v1/premiumIndex", {"symbol": symbol}),
        _get_json(client, "/fapi/v1/openInterest", {"symbol": symbol}),
        _get_json(client, "/fapi/v1/ticker/24hr", {"symbol": symbol}),
    )
    if not all(isinstance(item, dict) for item in (premium, interest, ticker)):
        raise ValueError("Unexpected Binance USDⓈ-M Futures response shape.")
    mark_price = float(premium["markPrice"])
    index_price = float(premium["indexPrice"])
    funding_rate = float(premium["lastFundingRate"])
    open_interest = float(interest["openInterest"])
    change_percent = float(ticker["priceChangePercent"])
    quote_volume = float(ticker["quoteVolume"])
    if mark_price <= 0 or index_price <= 0 or open_interest < 0 or quote_volume < 0:
        raise ValueError("Binance returned invalid Futures market metrics.")
    next_funding_ms = int(premium.get("nextFundingTime", 0))
    return {
        "symbol": symbol,
        "mark_price": mark_price,
        "index_price": index_price,
        "mark_index_basis_percent": round((mark_price / index_price - 1) * 100, 5),
        "last_funding_rate": funding_rate,
        "last_funding_percent": round(funding_rate * 100, 5),
        "open_interest_contracts": open_interest,
        "price_change_24h_percent": round(change_percent, 3),
        "quote_volume_24h_usdt": quote_volume,
        "next_funding_time": datetime.fromtimestamp(next_funding_ms / 1000, tz=timezone.utc).isoformat() if next_funding_ms else None,
    }


async def scan_binance_futures_context(symbols: list[str] | None = None) -> dict[str, Any]:
    """Read-only public USDⓈ-M Futures context; no keys, balances, or orders."""
    requested = symbols or DEFAULT_FUTURES_SYMBOLS
    normalized = list(dict.fromkeys(s.upper().strip() for s in requested))
    if not normalized or len(normalized) > 20:
        raise ValueError("Supply between 1 and 20 symbols.")
    for symbol in normalized:
        if not symbol.isalnum() or len(symbol) < 5 or len(symbol) > 20:
            raise ValueError(f"Invalid Binance symbol: {symbol!r}.")
    results, errors = [], []
    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "MPV-PRO-V5-futures-context/1.0"}) as client:
        for symbol in normalized:
            try:
                results.append(await _fetch_futures_symbol(client, symbol))
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                errors.append({"symbol": symbol, "error": str(exc)[:240]})
    results.sort(key=lambda item: abs(item["last_funding_rate"]), reverse=True)
    return {
        "provider": "Binance USDⓈ-M Futures public market data",
        "mode": "READ_ONLY_CONTEXT",
        "symbols_requested": normalized,
        "results": results,
        "errors": errors,
        "authenticated": False,
        "live_execution_enabled": False,
        "warning": "Funding, mark price, open interest and volume are context metrics, not standalone trading signals. Public endpoints do not connect a demo account or place orders. Futures are high risk.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
