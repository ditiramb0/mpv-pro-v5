from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_buy_take_profit_uses_fixed_three_to_one_ratio():
    response = client.post("/risk/calculate", json={
        "side": "BUY", "entry": 100, "stop_loss": 95,
        "equity": 10000, "risk_percent": 1
    })
    assert response.status_code == 200
    data = response.json()
    assert data["take_profit"] == 115
    assert data["risk_reward_ratio"] == "1:3"
    assert data["risk_amount"] == 100

def test_sell_take_profit_uses_fixed_three_to_one_ratio():
    response = client.post("/risk/calculate", json={
        "side": "SELL", "entry": 100, "stop_loss": 105,
        "equity": 10000, "risk_percent": 1
    })
    assert response.status_code == 200
    assert response.json()["take_profit"] == 85

def test_buy_rejects_stop_above_entry():
    response = client.post("/risk/calculate", json={
        "side": "BUY", "entry": 100, "stop_loss": 101, "equity": 10000
    })
    assert response.status_code == 422
