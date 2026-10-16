from __future__ import annotations

import os
import hmac
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, model_validator

app = FastAPI(
    title="MPV PRO V5",
    version="0.1.0",
    description="Trading signal intake and risk-planning API. No live orders are placed.",
)

class RiskRequest(BaseModel):
    side: Literal["BUY", "SELL"]
    entry: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    equity: float = Field(gt=0)
    risk_percent: float = Field(default=1.0, gt=0, le=5)

    @model_validator(mode="after")
    def validate_stop_side(self):
        if self.side == "BUY" and self.stop_loss >= self.entry:
            raise ValueError("For BUY, stop_loss must be below entry.")
        if self.side == "SELL" and self.stop_loss <= self.entry:
            raise ValueError("For SELL, stop_loss must be above entry.")
        return self

class TradingViewSignal(BaseModel):
    secret: str
    ticker: str = Field(min_length=1, max_length=40)
    action: Literal["BUY", "SELL"]
    timeframe: str = Field(default="unknown", max_length=20)
    entry: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    signal_id: str = Field(min_length=1, max_length=120)

@app.get("/")
def root():
    return {
        "name": "MPV PRO V5",
        "status": "running",
        "mode": "paper_only",
        "live_execution_enabled": False,
    }

@app.get("/health")
def health():
    return {"ok": True, "version": app.version}

@app.post("/risk/calculate")
def calculate_risk(request: RiskRequest):
    risk_distance = abs(request.entry - request.stop_loss)
    take_profit_distance = risk_distance * 3.0
    take_profit = (
        request.entry + take_profit_distance
        if request.side == "BUY"
        else request.entry - take_profit_distance
    )
    risk_amount = request.equity * request.risk_percent / 100.0
    # Quantity estimate assumes the instrument's P&L per price unit equals quantity.
    # Adapt this for contract multipliers, FX pip value, and exchange lot rules before use.
    quantity_estimate = risk_amount / risk_distance
    return {
        "side": request.side,
        "entry": request.entry,
        "stop_loss": request.stop_loss,
        "take_profit": take_profit,
        "risk_reward_ratio": "1:3",
        "risk_amount": round(risk_amount, 8),
        "risk_percent": request.risk_percent,
        "quantity_estimate": round(quantity_estimate, 8),
        "note": "Estimate only; instrument contract size, fees, slippage and lot rules are not included.",
    }

@app.post("/webhook/tradingview")
def tradingview_webhook(
    signal: TradingViewSignal,
    x_mpv_webhook_secret: str | None = Header(default=None),
):
    expected = os.getenv("TRADINGVIEW_WEBHOOK_SECRET")
    if not expected:
        raise HTTPException(status_code=503, detail="Webhook secret is not configured.")
    supplied = x_mpv_webhook_secret or signal.secret
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook secret.")
    # Do not echo secrets or place orders. Persisting/deduplicating and broker execution
    # will be implemented only after storage and an execution provider are configured.
    return {
        "accepted": True,
        "signal_id": signal.signal_id,
        "ticker": signal.ticker,
        "action": signal.action,
        "timeframe": signal.timeframe,
        "execution": "disabled",
        "mode": "paper_only",
    }
