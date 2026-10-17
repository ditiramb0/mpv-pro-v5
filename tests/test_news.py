from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.news import _sentiment


def test_sentiment_uses_transparent_keyword_heuristic():
    result = _sentiment("Bitcoin rally and strong adoption, but risk remains")
    assert result["positive_terms"] == 3
    assert result["negative_terms"] == 1
    assert result["label"] == "positive"


def test_news_endpoint_requires_provider_key(monkeypatch):
    monkeypatch.setattr(settings, "finnhub_api_key", "")
    with TestClient(app) as client:
        response = client.get("/news/sentiment?ticker=BTCUSDT&market=crypto")
    assert response.status_code == 503
    assert "FINNHUB_API_KEY" in response.json()["detail"]


def test_news_endpoint_scores_provider_response(monkeypatch):
    monkeypatch.setattr(settings, "finnhub_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return [{
                "headline": "Bitcoin rallies on strong adoption",
                "summary": "Market sentiment improves as inflows rise.",
                "source": "Test Source",
                "url": "https://example.com/news",
                "datetime": 1792195200,
            }]

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.news.httpx.AsyncClient", FakeAsyncClient)
    with TestClient(app) as client:
        response = client.get("/news/sentiment?ticker=BTCUSDT&market=crypto&limit=5")

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "Finnhub"
    assert data["article_count"] == 1
    assert data["matched_headlines_count"] == 1
    assert data["sentiment"]["label"] == "positive"
    assert "keyword-count heuristic" in data["sentiment_method"]
