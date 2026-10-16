from __future__ import annotations

from typing import Literal

TradingStyle = Literal["scalping", "day_trading", "swing_trading"]

TIMEFRAME_PROFILES: dict[str, dict] = {
    "scalping": {
        "entry_timeframes": ["1m", "5m"],
        "confirmation_timeframes": ["5m", "15m"],
        "context_timeframes": ["15m", "1h"],
        "notes": "Sensitive to spread, execution latency and fees; validate costs carefully.",
    },
    "day_trading": {
        "entry_timeframes": ["5m", "15m"],
        "confirmation_timeframes": ["15m", "1h"],
        "context_timeframes": ["1h", "4h"],
        "notes": "Designed for intraday research; avoid assuming signals carry across sessions.",
    },
    "swing_trading": {
        "entry_timeframes": ["1h", "4h"],
        "confirmation_timeframes": ["4h", "1d"],
        "context_timeframes": ["1d", "1w"],
        "notes": "Wider holding periods require overnight/weekend gap and funding considerations.",
    },
}

def get_timeframe_profile(style: TradingStyle) -> dict:
    profile = TIMEFRAME_PROFILES[style]
    return {"style": style, **profile}
