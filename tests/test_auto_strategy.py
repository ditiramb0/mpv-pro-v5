import math

from fastapi.testclient import TestClient

from app.main import app


def candles(count=240, falling=False):
    rows = []
    for i in range(count):
        close = (200 - i * 0.2 - 1.5 * math.sin(i * 0.5 + 3.0)) if falling else (100 + i * 0.2 + 1.5 * math.sin(i * 0.5 + 3.0))
        opened = close + 0.05 if falling else close - 0.05
        rows.append({
            "timestamp": f"2020-01-{(i % 28) + 1:02d}T00:00:00+00:00",
            "open": opened,
            "high": close + 0.25,
            "low": close - 0.25,
            "close": close,
        })
    return rows


def test_auto_evaluate_fetches_three_timeframes_and_returns_aligned_signal(monkeypatch):
    calls = []

    async def fake_fetch_candles(ticker, market, timeframe, limit=220):
        calls.append((ticker, market, timeframe, limit))
        return {
            "provider": "mock",
            "ticker": ticker,
            "market": market,
            "timeframe": timeframe,
            "count": 240,
            "candles": candles(),
        }

    monkeypatch.setattr("app.main.fetch_candles", fake_fetch_candles)
    with TestClient(app) as client:
        response = client.get("/strategy/auto-evaluate?ticker=BTCUSDT&market=crypto&style=day_trading")

    assert response.status_code == 200
    data = response.json()
    assert data["signal"] == "BUY"
    assert data["alignment"] == "aligned"
    assert set(data["evaluations"]) == {"entry", "confirmation", "context"}
    assert len(calls) == 3
    assert all(call[3] == 220 for call in calls)
    assert data["live_execution_enabled"] is False
    plan = data["trade_plan"]
    assert plan["side"] == "BUY"
    assert plan["stop_loss"] < plan["entry"] < plan["take_profit"]
    assert abs((plan["take_profit"] - plan["entry"]) / (plan["entry"] - plan["stop_loss"]) - 3) < 1e-8


def test_auto_evaluate_returns_hold_when_timeframes_disagree(monkeypatch):
    async def fake_fetch_candles(ticker, market, timeframe, limit=220):
        is_context = timeframe == "15m"
        rows = candles(falling=is_context)
        return {"provider": "mock", "ticker": ticker, "market": market,
                "timeframe": timeframe, "count": len(rows), "candles": rows}

    monkeypatch.setattr("app.main.fetch_candles", fake_fetch_candles)
    with TestClient(app) as client:
        response = client.get("/strategy/auto-evaluate?ticker=BTCUSDT&market=crypto&style=scalping")

    assert response.status_code == 200
    assert response.json()["signal"] == "HOLD"
    assert response.json()["alignment"] == "mixed_or_no_signal"
    assert response.json()["trade_plan"] is None
