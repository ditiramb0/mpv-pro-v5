from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def order_payload(order_id):
    return {
        "ticker": "EURUSD",
        "market": "forex",
        "side": "BUY",
        "entry": 100,
        "stop_loss": 95,
        "equity": 10000,
        "risk_percent": 1,
        "client_order_id": order_id,
    }


def create_and_lose(client, order_id):
    created = client.post("/paper/orders", json=order_payload(order_id))
    assert created.status_code == 200
    order = created.json()["order"]
    closed = client.post(f"/paper/orders/{order['order_id']}/close", json={"close_price": 95})
    assert closed.status_code == 200
    assert closed.json()["order"]["pnl_estimate"] == -100


def test_emergency_halt_blocks_new_paper_orders(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "emergency_halt", True)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'halt.db'}")
    with TestClient(app) as client:
        blocked = client.post("/paper/orders", json=order_payload("halted-order"))
        status = client.get("/risk/status?equity=10000")

    assert blocked.status_code == 423
    assert status.status_code == 200
    assert status.json()["emergency_halt"] is True
    assert status.json()["new_paper_orders_blocked"] is True
    assert status.json()["block_reason"] == "emergency_halt"


def test_daily_loss_limit_blocks_new_paper_orders(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "emergency_halt", False)
    monkeypatch.setattr(settings, "max_daily_loss_percent", 1.0)
    monkeypatch.setattr(settings, "max_consecutive_losses", 5)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'daily-loss.db'}")
    with TestClient(app) as client:
        create_and_lose(client, "daily-loss-1")
        status = client.get("/risk/status?equity=10000")
        blocked = client.post("/paper/orders", json=order_payload("daily-loss-2"))

    assert status.json()["risk_state"]["daily_loss_limit_reached"] is True
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["risk_state"]["daily_loss_limit_reached"] is True


def test_consecutive_loss_limit_blocks_new_paper_orders(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "emergency_halt", False)
    monkeypatch.setattr(settings, "max_daily_loss_percent", 10.0)
    monkeypatch.setattr(settings, "max_consecutive_losses", 2)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'streak-loss.db'}")
    with TestClient(app) as client:
        create_and_lose(client, "streak-loss-1")
        create_and_lose(client, "streak-loss-2")
        status = client.get("/risk/status?equity=10000")
        blocked = client.post("/paper/orders", json=order_payload("streak-loss-3"))

    assert status.json()["risk_state"]["consecutive_losses"] == 2
    assert status.json()["risk_state"]["consecutive_loss_limit_reached"] is True
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["risk_state"]["consecutive_loss_limit_reached"] is True
