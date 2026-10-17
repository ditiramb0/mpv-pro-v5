from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def payload():
    return {
        "ticker": "BTCUSDT",
        "market": "crypto",
        "side": "BUY",
        "entry": 100,
        "stop_loss": 95,
        "equity": 10000,
        "risk_percent": 1,
        "client_order_id": "paper-order-001",
    }


def test_paper_order_is_persisted_and_uses_fixed_three_to_one_target(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'paper.db'}")
    with TestClient(app) as client:
        response = client.post("/paper/orders", json=payload())
        listed = client.get("/paper/orders")

    assert response.status_code == 200
    data = response.json()
    assert data["created"] is True
    assert data["duplicate"] is False
    assert data["order"]["take_profit"] == 115
    assert data["order"]["risk_amount"] == 100
    assert data["order"]["quantity_estimate"] == 20
    assert data["live_execution_enabled"] is False
    assert len(listed.json()["orders"]) == 1


def test_paper_order_id_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'paper.db'}")
    with TestClient(app) as client:
        first = client.post("/paper/orders", json=payload())
        changed = payload()
        changed["entry"] = 110
        second = client.post("/paper/orders", json=changed)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["order"]["entry"] == 100


def test_paper_order_can_be_closed_once(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'paper.db'}")
    with TestClient(app) as client:
        created = client.post("/paper/orders", json=payload())
        order_id = created.json()["order"]["order_id"]
        closed = client.post(f"/paper/orders/{order_id}/close", json={"close_price": 110})
        repeated = client.post(f"/paper/orders/{order_id}/close", json={"close_price": 112})

    assert closed.status_code == 200
    assert closed.json()["order"]["status"] == "closed"
    assert closed.json()["order"]["pnl_estimate"] == 200
    assert repeated.status_code == 409


def test_paper_order_rejects_wrong_stop_side(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'paper.db'}")
    invalid = payload()
    invalid["stop_loss"] = 105
    with TestClient(app) as client:
        response = client.post("/paper/orders", json=invalid)
    assert response.status_code == 422
