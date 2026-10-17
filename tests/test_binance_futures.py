import pytest

from app.binance_futures import _fetch_futures_symbol


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    async def get(self, url, params):
        if url.endswith("/fapi/v1/premiumIndex"):
            return FakeResponse({
                "markPrice": "101", "indexPrice": "100",
                "lastFundingRate": "0.0001", "nextFundingTime": "1792200000000",
            })
        if url.endswith("/fapi/v1/openInterest"):
            return FakeResponse({"openInterest": "1234.5"})
        if url.endswith("/fapi/v1/ticker/24hr"):
            return FakeResponse({"priceChangePercent": "2.5", "quoteVolume": "987654"})
        raise AssertionError(f"Unexpected URL: {url}")


@pytest.mark.asyncio
async def test_futures_context_parses_public_metrics():
    result = await _fetch_futures_symbol(FakeClient(), "BTCUSDT")
    assert result["symbol"] == "BTCUSDT"
    assert result["mark_price"] == 101
    assert result["mark_index_basis_percent"] == 1.0
    assert result["last_funding_percent"] == 0.01
    assert result["open_interest_contracts"] == 1234.5
    assert result["price_change_24h_percent"] == 2.5
    assert result["quote_volume_24h_usdt"] == 987654
