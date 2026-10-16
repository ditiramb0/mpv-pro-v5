from app.timeframes import get_timeframe_profile

def test_all_styles_have_entry_confirmation_and_context_timeframes():
    for style in ("scalping", "day_trading", "swing_trading"):
        profile = get_timeframe_profile(style)
        assert profile["entry_timeframes"]
        assert profile["confirmation_timeframes"]
        assert profile["context_timeframes"]
