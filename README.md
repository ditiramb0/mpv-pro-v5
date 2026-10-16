# MPV PRO V5

MPV PRO V5 is an in-progress research and trading-systems project for **forex and cryptocurrency**. Current code provides a FastAPI backend for risk planning, indicator calculations, a baseline trend signal, and authenticated TradingView signal intake.

## Current capabilities

- `GET /` and `GET /health`: status endpoints.
- `POST /risk/calculate`: stop-loss / take-profit planning with a fixed 1:3 risk-to-reward target.
- `POST /strategy/evaluate`: evaluates supplied OHLC candles with EMA 9/21/50/200, RSI, MACD, ADX, Bollinger Bands, and ATR, then returns a transparent baseline trend signal.
- `POST /webhook/tradingview`: authenticated signal intake.
- `GET /signals`: recent stored signals.
- SQLite persistence and duplicate `signal_id` protection.
- GitHub Actions runs pytest on pushes and pull requests.
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

Open `/docs` on the local server to explore the API. Run tests with `pytest -q`.

## Strategy endpoint

Send `market` (`forex` or `crypto`), `ticker`, `timeframe`, and at least 220 chronological OHLC candles to `POST /strategy/evaluate`. Candle objects use numeric `open`, `high`, `low`, and `close` values.

The current baseline requires aligned EMAs, MACD direction, an RSI range, and ADX trend strength. It returns BUY, SELL, or HOLD and an ATR-based stop/target distance at 1:3. Bollinger Bands are calculated and returned as context, but are not currently used as a signal condition.

## Webhook

Send JSON with `ticker`, `market` (`forex` or `crypto`), `action` (`BUY` or `SELL`), `timeframe`, `signal_id`, and optional `entry` / `stop_loss`. Put the configured secret in the `x-mpv-webhook-secret` header. Never commit real secrets.

## Important limitations

This is not yet a complete trading bot. The strategy is an unvalidated research baseline, not a promise of profitability. Historical backtesting, realistic spread/fees/slippage, multi-timeframe confirmation, order-block/FVG/liquidity logic, news sentiment, and broker/exchange execution are not implemented. The generic quantity estimate does not account for contract multipliers, tick/pip value, lot size, account currency, or trading costs. Backtest and paper-trade before considering live use.

## Next

1. Verify CI tests and correct any failures.
2. Add historical backtesting with fees, spread, slippage, drawdown and walk-forward evaluation.
3. Add multi-timeframe confirmation and price-action modules.
4. Integrate news sentiment through a separately configured provider.
5. Add a broker/exchange adapter only after choosing a provider and defining safety controls.
