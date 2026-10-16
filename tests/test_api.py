from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def rising_candles(count=240):
    candles = []
    for i in range(count):
        close = 100 + i * 0.2
        candles.append({
            "open": close - 0.05,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
        })
    return candles


def test_health_endpoint_reports_version():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_strategy_endpoint_returns_explicit_baseline_result():
    with TestClient(app) as client:
        response = client.post("/strategy/evaluate", json={
            "market": "crypto",
            "ticker": "BTCUSDT",
            "timeframe": "1h",
            "candles": rising_candles(),
        })
    assert response.status_code == 200
    data = response.json()
    assert data["market"] == "crypto"
    assert data["ticker"] == "BTCUSDT"
    assert data["signal"]["action"] in {"BUY", "SELL", "HOLD"}
    assert data["signal"]["risk_reward_ratio"] == "1:3"
    assert data["live_execution_enabled"] is False


def test_timeframe_profiles_cover_all_styles():
    with TestClient(app) as client:
        for style in ("scalping", "day_trading", "swing_trading"):
            response = client.get(f"/timeframes/{style}")
            assert response.status_code == 200
            data = response.json()
            assert data["style"] == style
            assert data["entry_timeframes"]
            assert data["confirmation_timeframes"]
            assert data["context_timeframes"]


def test_backtest_endpoint_returns_cost_assumptions_and_warning():
    with TestClient(app) as client:
        response = client.post("/backtest/run", json={
            "market": "forex",
            "ticker": "EURUSD",
            "timeframe": "1h",
            "candles": rising_candles(),
            "fee_rate": 0.0001,
            "slippage_rate": 0.0001,
        })
    assert response.status_code == 200
    data = response.json()
    assert "trade_count" in data
    assert "net_return" in data
    assert data["assumptions"]["risk_reward"] == 3.0
    assert "Research approximation" in data["warning"]


def test_webhook_requires_secret_and_deduplicates_signals(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "tradingview_webhook_secret", "test-secret")
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'signals.db'}")
    payload = {
        "ticker": "BTCUSDT",
        "market": "crypto",
        "action": "BUY",
        "timeframe": "15m",
        "signal_id": "test-signal-001",
        "entry": 65000,
        "stop_loss": 64000,
    }
    with TestClient(app) as client:
        denied = client.post("/webhook/tradingview", json=payload)
        assert denied.status_code == 401

        first = client.post(
            "/webhook/tradingview",
            json=payload,
            headers={"x-mpv-webhook-secret": "test-secret"},
        )
        second = client.post(
            "/webhook/tradingview",
            json=payload,
            headers={"x-mpv-webhook-secret": "test-secret"},
        )
        listed = client.get("/signals")

    assert first.status_code == 200
    assert first.json()["duplicate"] is False
    assert first.json()["execution"] == "disabled"
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert len(listed.json()["signals"]) == 1
