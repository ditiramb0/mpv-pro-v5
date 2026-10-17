from datetime import datetime, timezone, timedelta

import pytest

from app.binance_scanner import _parse_klines


def test_parse_klines_validates_and_sorts():
    start = datetime.now(timezone.utc) - timedelta(hours=5)
    rows = []
    for i in (1, 0):
        ts = int((start + timedelta(hours=i)).timestamp() * 1000)
        rows.append([ts, "100", "105", "95", "102", "1000"])
    candles = _parse_klines(rows, "1h")
    assert len(candles) == 2
    assert candles[0]["close"] == 102.0
    assert candles[0]["timestamp"] < candles[1]["timestamp"]


def test_parse_klines_rejects_invalid_ohlc():
    ts = int((datetime.now(timezone.utc) - timedelta(hours=5)).timestamp() * 1000)
    with pytest.raises(ValueError, match="invalid OHLC"):
        _parse_klines([[ts, "100", "90", "95", "102", "1000"]], "1h")


def test_parse_klines_rejects_unknown_interval():
    with pytest.raises(ValueError, match="Only 1h and 4h"):
        _parse_klines([], "15m")
