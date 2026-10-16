# MPV PRO V5

MPV PRO V5 is an in-progress research and trading-systems project for **forex and cryptocurrency**, with separate scalping, day-trading, and swing-trading timeframe profiles.

## Current capabilities

- `GET /` and `GET /health`: status endpoints.
- `GET /timeframes/{style}`: profile for `scalping`, `day_trading`, or `swing_trading`.
- `POST /risk/calculate`: stop-loss / take-profit planning with a fixed 1:3 risk-to-reward target.
- `POST /strategy/evaluate`: evaluates supplied OHLC candles with EMA 9/21/50/200, RSI, MACD, ADX, Bollinger Bands, and ATR, then returns a transparent baseline trend signal.
- `POST /backtest/run`: basic historical candle simulation with configurable proportional fee and slippage assumptions.
- `POST /webhook/tradingview`: authenticated signal intake.
- `GET /signals`: recent stored signals.
- SQLite persistence and duplicate `signal_id` protection.
- GitHub Actions workflow configured to run pytest on pushes and pull requests.
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

## Trading styles

- **Scalping:** entry 1m/5m; confirmation 5m/15m; context 15m/1h.
- **Day trading:** entry 5m/15m; confirmation 15m/1h; context 1h/4h.
- **Swing trading:** entry 1h/4h; confirmation 4h/1d; context 1d/1w.

These are configuration profiles, not proof that the strategy performs well on each timeframe. Scalping is especially sensitive to spread, fees, latency and slippage.

## Strategy endpoint

Send `market` (`forex` or `crypto`), `ticker`, `timeframe`, and at least 220 chronological OHLC candles to `POST /strategy/evaluate`. Candle objects use numeric `open`, `high`, `low`, and `close` values.

The baseline requires aligned EMAs, MACD direction, an RSI range, and ADX trend strength. It returns BUY, SELL, or HOLD and an ATR-based stop/target distance at 1:3. Bollinger Bands are calculated and returned as context, but are not currently used as a signal condition.

## Backtest endpoint

Send `market`, `ticker`, `timeframe`, and 222–2000 chronological OHLC candles to `POST /backtest/run`. Optional `fee_rate` and `slippage_rate` are proportional assumptions per side.

This is a research prototype, not an exchange-grade backtester. It uses unit-notional trades, a simplified cost model, and assumes the stop is hit first if stop and target are both touched within one candle. It does not model actual instrument contract sizes, funding, spread changes, gaps, order-book execution or account-currency conversion.

## Webhook

Send JSON with `ticker`, `market` (`forex` or `crypto`), `action` (`BUY` or `SELL`), `timeframe`, `signal_id`, and optional `entry` / `stop_loss`. Put the configured secret in the `x-mpv-webhook-secret` header. Never commit real secrets.

## Important limitations

The strategy is an unvalidated research baseline, not a promise of profitability. Tests have been added but should be confirmed in a successful CI run. Advanced market structure (BOS/CHoCH, order blocks, FVG, liquidity sweeps), reliable multi-timeframe signal confirmation, news sentiment, and broker/exchange execution are not implemented. The generic quantity estimate does not account for contract multipliers, tick/pip value, lot size, account currency, or trading costs. Backtest and paper-trade before considering live use.


## Deployment preparation (Railway / Docker)

A Railway-compatible Docker deployment configuration is included. The container listens on the platform-provided `PORT` and exposes `/health` for health checks.

Before deploying:
1. Set `TRADINGVIEW_WEBHOOK_SECRET` to a long, random secret in the hosting provider's environment variables.
2. Mount a persistent volume at `/data` and set `DATABASE_URL=sqlite:////data/mpv_pro_v5.db`. Without persistent storage, SQLite signal history may be lost when the service is replaced or redeployed.
3. Keep live execution disabled. This version accepts and stores authenticated TradingView signals; it does not place broker/exchange orders.
4. After deployment, verify `/health`, `/docs`, webhook authentication, duplicate-signal handling, and signal persistence.

Do not put secrets in the repository or Docker image. The `.dockerignore` excludes local environment files and database files from the image build context.

**Deployment status:** configuration only. A hosting account, persistent volume, environment variables, and public service URL must be configured in the hosting dashboard before this can be considered deployed.
