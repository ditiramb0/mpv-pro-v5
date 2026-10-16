# MPV PRO V5

MPV PRO V5 is an in-progress trading-systems project. Current code provides a FastAPI backend for risk planning and authenticated TradingView signal intake.

## Current capabilities

- `GET /` and `GET /health`: status endpoints.
- `POST /risk/calculate`: stop-loss / take-profit planning with a fixed 1:3 risk-to-reward target.
- `POST /webhook/tradingview`: authenticated signal intake.
- `GET /signals`: recent stored signals.
- SQLite persistence and duplicate `signal_id` protection.
- Live order execution is deliberately disabled.

## Run locally

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set a unique `TRADINGVIEW_WEBHOOK_SECRET` in `.env`, then run:

```bash
uvicorn app.main:app --reload
```

Open `/docs` on the local server to explore the API. Run tests with `pytest`.

## Webhook

Send JSON with `ticker`, `action` (`BUY` or `SELL`), `timeframe`, `signal_id`, and optional `entry` / `stop_loss`. Put the configured secret in the `x-mpv-webhook-secret` header. Never commit real secrets.

## Important limitations

This is not yet a complete trading bot. The quantity estimate in the risk endpoint is generic and does not account for instrument contract multipliers, pip/tick value, lot size, fees, spread, or slippage. The signal endpoint stores signals but does not execute trades. No strategy has been validated for profitability. Backtest with realistic costs and paper-trade before any live use.

## Planned next

1. Expand tests and validate instrument-specific sizing.
2. Add a strategy/signal engine and historical backtesting.
3. Add multi-timeframe confirmation and technical indicators.
4. Integrate news sentiment through a separately configured provider.
5. Add broker/exchange adapter only after choosing a provider and defining safety controls.
