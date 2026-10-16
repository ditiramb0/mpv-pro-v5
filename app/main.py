from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from app.config import settings
from app.storage import initialize_database, recent_signals, save_signal

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield

app = FastAPI(
    title="MPV PRO V5",
    version="0.2.0",
    description="Trading signal intake and risk-planning API. Live orders are disabled.",
    lifespan=lifespan,
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
    # Send the secret in the x-mpv-webhook-secret header, not in the JSON body.
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
    take_profit = request.entry + take_profit_distance if request.side == "BUY" else request.entry - take_profit_distance
    risk_amount = request.equity * request.risk_percent / 100.0
    # Generic estimate only: instrument multipliers, tick/pip value, fees and lot rules are excluded.
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
        "note": "Estimate only; adapt quantity for the instrument's contract specifications and trading costs.",
    }

@app.post("/webhook/tradingview")
def tradingview_webhook(
    signal: TradingViewSignal,
    x_mpv_webhook_secret: str | None = Header(default=None),
):
    expected = settings.tradingview_webhook_secret
    if not expected:
        raise HTTPException(status_code=503, detail="Webhook secret is not configured.")
    if not x_mpv_webhook_secret or not hmac.compare_digest(x_mpv_webhook_secret, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook secret.")
    try:
        inserted = save_signal(signal)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "accepted": True,
        "duplicate": not inserted,
        "signal_id": signal.signal_id,
        "ticker": signal.ticker,
        "action": signal.action,
        "timeframe": signal.timeframe,
        "execution": "disabled",
        "mode": "paper_only",
    }

@app.get("/signals")
def get_signals(limit: int = Query(default=50, ge=1, le=200)):
    return {"signals": recent_signals(limit=limit), "live_execution_enabled": False}
