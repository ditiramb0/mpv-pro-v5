import math

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.market_structure import analyze_market_structure


def rising_candles(count=240):
    candles = []
    for i in range(count):
        close = 100 + i * 0.2 + 1.5 * math.sin(i * 0.5 + 3.0)
        candles.append({
            "open": close - 0.05,
            "high": close + 0.25,
            "low": close - 0.25,
            "close": close,
        })
    return candles


def falling_candles(count=240):
    candles = []
    for i in range(count):
        close = 200 - i * 0.2 - 1.5 * math.sin(i * 0.5 + 3.0)
        candles.append({
            "open": close + 0.05,
            "high": close + 0.25,
            "low": close - 0.25,
            "close": close,
        })
    return candles


def test_market_structure_returns_documented_fields():
    data = analyze_market_structure(rising_candles(), swing_window=3)
    assert "swings" in data
    assert "events" in data
    assert "fair_value_gaps" in data
    assert "order_blocks" in data
    assert "heuristic" in data["methodology_note"]


def test_market_structure_rejects_invalid_ohlc():
    candles = rising_candles(20)
    candles[5] = {"open": 10, "high": 9, "low": 8, "close": 10}
    with pytest.raises(ValueError):
        analyze_market_structure(candles)


def test_market_structure_endpoint_rejects_too_few_candles():
    with TestClient(app) as client:
        response = client.post("/market-structure/analyze", json={
            "market": "crypto",
            "ticker": "BTCUSDT",
            "timeframe": "1h",
            "candles": rising_candles(10),
        })
    assert response.status_code == 422


def test_multi_timeframe_requires_directional_alignment():
    with TestClient(app) as client:
        response = client.post("/strategy/multi-timeframe", json={
            "market": "crypto",
            "ticker": "BTCUSDT",
            "entry_timeframe": "5m",
            "confirmation_timeframe": "15m",
            "context_timeframe": "1h",
            "entry_candles": rising_candles(),
            "confirmation_candles": rising_candles(),
            "context_candles": falling_candles(),
        })
    assert response.status_code == 200
    data = response.json()
    assert data["signal"] == "HOLD"
    assert data["alignment"] == "mixed_or_no_signal"
    assert data["live_execution_enabled"] is False


def test_multi_timeframe_returns_signal_when_all_three_align():
    with TestClient(app) as client:
        response = client.post("/strategy/multi-timeframe", json={
            "market": "crypto",
            "ticker": "BTCUSDT",
            "entry_timeframe": "5m",
            "confirmation_timeframe": "15m",
            "context_timeframe": "1h",
            "entry_candles": rising_candles(),
            "confirmation_candles": rising_candles(),
            "context_candles": rising_candles(),
        })
    assert response.status_code == 200
    data = response.json()
    assert data["signal"] == "BUY"
    assert data["alignment"] == "aligned"
    assert data["risk_reward_ratio"] == "1:3"
