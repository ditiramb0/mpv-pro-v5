from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings


POSITIVE_TERMS = {
    "adoption", "approval", "approved", "beat", "bullish", "gain", "gains",
    "growth", "inflow", "inflows", "outperform", "positive", " rally",
    "rally", "rallies", "rebound", "recovery", "record", "rise", "rises",
    "strong", "surge", "surged", "upgrade", "upgraded", "buy",
}
NEGATIVE_TERMS = {
    "ban", "bearish", "crash", "crashed", "decline", "declines", "downgrade",
    "downgraded", "drop", "drops", "exploit", "fall", "falls", "fraud",
    "hack", "hacked", "lawsuit", "liquidation", "loss", "losses", "negative",
    "outflow", "outflows", "probe", "rejection", "risk", "sell", "selloff",
    "weak",
}

ASSET_ALIASES = {
    "BTC": ["bitcoin", "btc"],
    "ETH": ["ethereum", "ether", "eth"],
    "SOL": ["solana", "sol"],
    "XRP": ["ripple", "xrp"],
    "ADA": ["cardano", "ada"],
    "DOGE": ["dogecoin", "doge"],
    "BNB": ["binance coin", "bnb"],
    "LTC": ["litecoin", "ltc"],
    "AVAX": ["avalanche", "avax"],
}


def _sentiment(text: str) -> dict[str, Any]:
    tokens = re.findall(r"[a-z]+(?:-[a-z]+)?", text.lower())
    positive = sum(token in POSITIVE_TERMS for token in tokens)
    negative = sum(token in NEGATIVE_TERMS for token in tokens)
    total = positive + negative
    score = (positive - negative) / total if total else 0.0
    label = "positive" if score >= 0.15 else "negative" if score <= -0.15 else "neutral"
    return {"label": label, "score": round(score, 4), "positive_terms": positive, "negative_terms": negative}


def _ticker_keywords(ticker: str, market: str) -> list[str]:
    normalized = re.sub(r"[^A-Z]", "", ticker.upper())
    if market == "crypto":
        for symbol, aliases in ASSET_ALIASES.items():
            if normalized.startswith(symbol):
                return aliases
        return [normalized.lower()] if normalized else []
    if len(normalized) == 6:
        currency_names = {
            "EUR": ["euro", "eur"], "USD": ["dollar", "usd", "federal reserve", "fed"],
            "GBP": ["sterling", "pound", "gbp", "bank of england"],
            "JPY": ["yen", "jpy", "bank of japan"], "CHF": ["franc", "chf"],
            "CAD": ["canadian dollar", "cad", "bank of canada"],
            "AUD": ["australian dollar", "aud", "reserve bank of australia"],
            "NZD": ["new zealand dollar", "nzd", "reserve bank of new zealand"],
        }
        base, quote = normalized[:3], normalized[3:]
        return list(dict.fromkeys(currency_names.get(base, [base.lower()]) + currency_names.get(quote, [quote.lower()])))
    return [normalized.lower()] if normalized else []


async def fetch_news_sentiment(ticker: str, market: str, limit: int = 20) -> dict[str, Any]:
    """Fetch Finnhub category headlines and score them with a small transparent word list."""
    if not settings.finnhub_api_key:
        raise RuntimeError("FINNHUB_API_KEY is not configured.")
    category = "crypto" if market == "crypto" else "forex"
    url = "https://finnhub.io/api/v1/news"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            url,
            params={"category": category},
            headers={"X-Finnhub-Token": settings.finnhub_api_key},
        )
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, list):
        raise ValueError("News provider returned an unexpected response.")
    keywords = _ticker_keywords(ticker, market)
    matched = [
        item for item in payload
        if any(keyword in f"{item.get('headline', '')} {item.get('summary', '')}".lower() for keyword in keywords)
    ]
    used_fallback = not matched
    selected = (matched if matched else payload)[:limit]
    articles = []
    all_text = []
    for item in selected:
        headline = str(item.get("headline") or "")
        summary = str(item.get("summary") or "")
        article_sentiment = _sentiment(f"{headline}. {summary}")
        all_text.append(f"{headline}. {summary}")
        timestamp = item.get("datetime")
        published_at = datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if isinstance(timestamp, (int, float)) else None
        articles.append({
            "headline": headline,
            "summary": summary,
            "source": item.get("source"),
            "url": item.get("url"),
            "published_at": published_at,
            "sentiment": article_sentiment,
        })

    combined = _sentiment(" ".join(all_text))
    return {
        "ticker": ticker.upper(),
        "market": market,
        "provider": "Finnhub",
        "category": category,
        "sentiment": combined,
        "article_count": len(articles),
        "matched_headlines_count": len(matched),
        "used_category_fallback": used_fallback,
        "sentiment_method": "transparent keyword-count heuristic; not a trained language model and not a trading recommendation",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
    }
