from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.indicators import calculate_indicators
from app.strategy import evaluate_trend

@dataclass
class Trade:
    side: str
    entry_index: int
    exit_index: int
    entry: float
    exit: float
    stop_loss: float
    take_profit: float
    pnl: float
    exit_reason: str

def run_backtest(
    candles: Sequence[dict],
    *,
    warmup: int = 220,
    risk_reward: float = 3.0,
    atr_stop_multiple: float = 1.5,
    fee_rate: float = 0.0005,
    slippage_rate: float = 0.0002,
) -> dict:
    """Educational close-to-close baseline, long/short one position at a time.

    Signal uses data through candle i; entry occurs at candle i+1 open.
    If both stop and target are touched in one candle, stop is assumed first.
    Fees/slippage are simple proportional price-cost estimates, not broker-specific.
    """
    if len(candles) < warmup + 2:
        raise ValueError(f"At least {warmup + 2} candles are required.")
    if fee_rate < 0 or slippage_rate < 0 or risk_reward <= 0 or atr_stop_multiple <= 0:
        raise ValueError("Costs must be non-negative and risk parameters positive.")
    trades: list[Trade] = []
    equity_curve = [1.0]
    i = warmup
    while i < len(candles) - 1:
        snapshot = calculate_indicators(candles[: i + 1])
        decision = evaluate_trend(snapshot)
        side = decision["action"]
        if side not in ("BUY", "SELL"):
            equity_curve.append(equity_curve[-1])
            i += 1
            continue
        entry_i = i + 1
        raw_entry = float(candles[entry_i]["open"])
        entry = raw_entry * (1 + slippage_rate if side == "BUY" else 1 - slippage_rate)
        distance = snapshot.atr14 * atr_stop_multiple
        if distance <= 0:
            i += 1
            continue
        stop = entry - distance if side == "BUY" else entry + distance
        target = entry + distance * risk_reward if side == "BUY" else entry - distance * risk_reward
        exit_price, exit_i, reason = float(candles[-1]["close"]), len(candles)-1, "end_of_data"
        for j in range(entry_i, len(candles)):
            high, low = float(candles[j]["high"]), float(candles[j]["low"])
            if side == "BUY":
                if low <= stop:
                    exit_price, exit_i, reason = stop, j, "stop_loss"
                    break
                if high >= target:
                    exit_price, exit_i, reason = target, j, "take_profit"
                    break
            else:
                if high >= stop:
                    exit_price, exit_i, reason = stop, j, "stop_loss"
                    break
                if low <= target:
                    exit_price, exit_i, reason = target, j, "take_profit"
                    break
        exit_price = exit_price * (1 - slippage_rate if side == "BUY" else 1 + slippage_rate)
        gross_return = (exit_price - entry) / entry if side == "BUY" else (entry - exit_price) / entry
        net_return = gross_return - fee_rate * 2
        trades.append(Trade(side, entry_i, exit_i, entry, exit_price, stop, target, net_return, reason))
        equity_curve.append(equity_curve[-1] * (1 + net_return))
        i = max(exit_i + 1, entry_i + 1)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    peak, max_drawdown = 1.0, 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak:
            max_drawdown = max(max_drawdown, (peak-equity)/peak)
    return {
        "trade_count": len(trades),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "net_return": equity_curve[-1] - 1.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0),
        "max_drawdown": max_drawdown,
        "equity_curve": equity_curve,
        "trades": [t.__dict__ for t in trades],
        "assumptions": {
            "risk_reward": risk_reward,
            "atr_stop_multiple": atr_stop_multiple,
            "fee_rate_per_side": fee_rate,
            "slippage_rate_per_side": slippage_rate,
            "same_candle_stop_target_rule": "stop_loss_first",
            "sizing": "unit notional; results are not account-specific",
        },
        "warning": "Research approximation only. Validate data quality, costs, gaps, funding, lot sizes, and out-of-sample performance before any use.",
    }
