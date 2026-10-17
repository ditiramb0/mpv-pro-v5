# MPV PRO V5

MPV PRO V5 is a forex and cryptocurrency trading-research API. It supports indicator-based baseline signals, multi-timeframe direction checks, heuristic market-structure analysis, risk planning, historical candle backtests, authenticated TradingView signal intake, and a persistent simulated paper-order ledger.

**Current mode: research / paper-only. Live broker or exchange order execution is not implemented or enabled.** No strategy is guaranteed to be profitable.

## API endpoints

- `GET /` and `GET /health`: service status and version.
- `GET /timeframes/{style}`: profiles for `scalping`, `day_trading`, and `swing_trading`.
- `POST /risk/calculate`: stop-loss / take-profit planning with fixed 1:3 risk-to-reward.
- `POST /strategy/evaluate`: EMA 9/21/50/200, RSI, MACD, ADX, Bollinger Bands, and ATR; returns a transparent baseline BUY/SELL/HOLD.
- `POST /strategy/multi-timeframe`: evaluates separate entry, confirmation, and context candle sets; returns BUY/SELL only when all three baseline signals agree, otherwise HOLD.
- `POST /market-structure/analyze`: heuristic swing highs/lows, BOS/CHoCH events, fair-value gaps, simple order-block candidates, and liquidity sweeps.
- `POST /backtest/run`: historical candle simulation with configurable proportional fee and slippage assumptions.
- `POST /paper/orders`: create a persistent simulated order with a 1:3 target and estimated position size.
- `GET /paper/orders`: list simulated orders.
- `POST /paper/orders/{order_id}/close`: manually close a simulated order at a supplied price and estimate gross P&L.
- `POST /webhook/tradingview`: authenticated signal intake with duplicate `signal_id` protection.
- `GET /signals`: recent stored TradingView signals.
- SQLite persistence and GitHub Actions tests.

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

Open `/docs` on the local server to explore and call the API. Run tests with:

```bash
python -m pytest -q
```

## Trading styles

- **Scalping:** entry 1m/5m; confirmation 5m/15m; context 15m/1h.
- **Day trading:** entry 5m/15m; confirmation 15m/1h; context 1h/4h.
- **Swing trading:** entry 1h/4h; confirmation 4h/1d; context 1d/1w.

These are configuration profiles, not evidence of strategy performance. Scalping is especially sensitive to spread, fees, latency, and slippage.

## Strategy notes

The baseline requires aligned EMAs, MACD direction, an RSI range, and ADX trend strength. It returns BUY, SELL, or HOLD and an ATR-based stop/target distance at 1:3. Bollinger Bands are calculated as context but are not currently a signal condition.

The multi-timeframe endpoint expects three separately supplied, chronological candle arrays for the same instrument. It does **not** resample candles, fetch market data, or verify timestamps/freshness. Supply correctly aligned datasets. All three signal directions must agree before it returns BUY or SELL.

## Market structure notes

The structure endpoint uses transparent heuristics: swing pivots need bars on both sides, FVGs are three-candle gaps, and order-block candidates are the nearest opposite-colour candle before a close-based break of structure. BOS, CHoCH, FVGs, order blocks, and liquidity sweeps are interpreted differently by different traders; these labels are not validated entry signals and may require tuning.

## Paper-order ledger

Paper orders are stored in SQLite, support client-provided idempotency keys, calculate a 1:3 target, and can be manually closed to estimate gross P&L. This ledger does **not** connect to a live price feed, automatically trigger stops/targets, deduct costs, or send orders to a broker. Position sizing is an estimate and does not account for instrument contract multipliers, pip/tick values, or account-currency conversion.

## Backtest limitations

Send 222–2000 chronological OHLC candles to `POST /backtest/run`. Optional `fee_rate` and `slippage_rate` are proportional assumptions per side.

This is a research prototype, not an exchange-grade backtester. It uses unit-notional trades and a simplified cost model. If stop and target are both touched in one candle, it assumes the stop is hit first. It does not model actual instrument contract sizes, funding, changing spreads, gaps, order-book execution, or account-currency conversion. Profit factor is reported as undefined when there are no gross losses rather than returning a non-JSON infinity.

## TradingView webhook

Send JSON with `ticker`, `market` (`forex` or `crypto`), `action` (`BUY` or `SELL`), `timeframe`, `signal_id`, and optional `entry` / `stop_loss`. Put the configured secret in the `x-mpv-webhook-secret` header. Never commit real secrets.

Webhook signals are stored, deduplicated, and returned for review. They do not create orders.

## Deployment preparation (Railway / Docker)

A Railway-compatible Docker configuration is included. The container listens on the platform-provided `PORT` and exposes `/health` for health checks.

Before deploying:
1. Set `TRADINGVIEW_WEBHOOK_SECRET` to a long, random secret in the hosting provider's environment variables.
2. Mount a persistent volume at `/data` and set `DATABASE_URL=sqlite:////data/mpv_pro_v5.db`. Without persistent storage, SQLite history may be lost when the service is replaced or redeployed.
3. Keep live execution disabled.
4. After deployment, verify `/health`, `/docs`, webhook authentication, duplicate-signal handling, and paper-order persistence.

Do not put secrets in the repository or Docker image. The `.dockerignore` excludes local environment files and database files from the image build context.

## Remaining before a production-ready system

- Verify the latest CI run, including tests and Docker image build.
- Add an approved market-data source and timestamp validation.
- Add a selected news provider and a clearly labelled sentiment method.
- Add broker-specific adapters, protective-order verification, and operational risk controls.
- Run realistic out-of-sample backtests and paper-trade for an extended period.
- Configure hosting, persistent storage, secrets, and uptime monitoring.

A broker/exchange has not been selected. Real-money execution should not be enabled until a specific platform is chosen, its test environment is validated, and order sizing/stop behaviour is verified. No API key or secret should ever be committed to this repository.

**Deployment status:** configuration only; this repository is not yet a deployed public service.
