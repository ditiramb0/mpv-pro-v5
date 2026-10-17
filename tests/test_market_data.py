from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.market_data import normalize_symbol


def test_normalize_common_forex_and_crypto_symbols():
    assert normalize_symbol("EURUSD", "forex") == "EUR/USD"
    assert normalize_symbol("BTCUSDT", "crypto") == "BTC/USDT"
    assert normalize_symbol("ETH/USD", "crypto") == "ETH/USD"


def test_market_data_endpoint_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "twelve_data_api_key", "")
    with TestClient(app) as client:
        response = client.get("/market-data/candles?ticker=EURUSD&market=forex")
    assert response.status_code == 503
    assert "TWELVE_DATA_API_KEY" in response.json()["detail"]


def test_market_data_endpoint_returns_sorted_completed_candles(monkeypatch):
    monkeypatch.setattr(settings, "twelve_data_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "meta": {"symbol": "EUR/USD"},
                "values": [
                    {"datetime": "2020-01-01 02:00:00", "open": "1.2", "high": "1.3", "low": "1.1", "close": "1.25"},
                    {"datetime": "2020-01-01 01:00:00", "open": "1.1", "high": "1.25", "low": "1.0", "close": "1.2"},
                ],
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            assert kwargs["params"]["symbol"] == "EUR/USD"
            assert kwargs["params"]["interval"] == "1h"
            return FakeResponse()

    monkeypatch.setattr("app.market_data.httpx.AsyncClient", FakeAsyncClient)
    with TestClient(app) as client:
        response = client.get("/market-data/candles?ticker=EURUSD&market=forex&timeframe=1h&limit=15")

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "Twelve Data"
    assert data["ticker"] == "EUR/USD"
    assert data["count"] == 2
    assert data["candles"][0]["timestamp"] < data["candles"][1]["timestamp"]
    assert data["candles"][1]["close"] == 1.25


def test_market_data_endpoint_handles_provider_error(monkeypatch):
    monkeypatch.setattr(settings, "twelve_data_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "error", "message": "Invalid symbol"}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.market_data.httpx.AsyncClient", FakeAsyncClient)
    with TestClient(app) as client:
        response = client.get("/market-data/candles?ticker=EURUSD&market=forex&timeframe=1h&limit=15")

    assert response.status_code == 422
    assert "Twelve Data error" in response.json()["detail"]
