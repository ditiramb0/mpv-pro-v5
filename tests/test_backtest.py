import pytest
from app.backtest import run_backtest

def test_backtest_requires_warmup_history():
    with pytest.raises(ValueError):
        run_backtest([{"open": 1, "high": 1.1, "low": .9, "close": 1}] * 10)
