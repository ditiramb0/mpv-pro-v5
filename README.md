# MPV PRO V5

Automated trading system project with TradingView signals, risk management, and a fixed 1:3 risk-to-reward target.

## Status

Initial project setup. Live order execution is not enabled. Validate all strategies with historical backtests and paper trading before considering live use.

## Planned components

- TradingView webhook receiver
- Risk and position-size calculations
- Stop-loss and take-profit planning with a 1:3 risk-to-reward ratio
- Duplicate-alert protection and audit logs
- News sentiment integration (external service required)
- Broker/exchange execution adapter (not yet configured)

## Safety

Never commit API keys or secrets. Use environment variables or a secrets manager. This project does not guarantee trading profits.
