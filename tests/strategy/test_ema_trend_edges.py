"""Casos de borde de `ema_trend`: sin volatilidad, Decimal exacto, warmup con Wilder."""

from __future__ import annotations

from decimal import Decimal

import numpy as np

from tests.factories import BTC, T0, d, make_candle
from tradingbot.domain import Position, Side, SignalAction, Timeframe, make_client_order_id
from tradingbot.indicators import FloatArray
from tradingbot.strategy import OhlcvArrays, StrategyContext
from tradingbot.strategy.strategies import EmaTrend

SMALL = {
    "ema_fast": 3,
    "ema_slow": 6,
    "ema_regime": 12,
    "adx_period": 3,
    "adx_threshold": 20.0,
    "atr_period": 3,
    "warmup_multiplier": 5,
}


def _two_candle_arrays(close: float) -> OhlcvArrays:
    candles = [
        make_candle(
            open_time=T0 + i * Timeframe.H4.ms,
            open=str(close),
            high=str(close + 1),
            low=str(close - 1),
            close=str(close),
        )
        for i in range(2)
    ]
    return OhlcvArrays.from_candles(candles)


def _bullish_cross_indicators(close: float, atr_value: float) -> dict[str, FloatArray]:
    return {
        "ema_fast": np.array([close - 2.0, close + 1.0]),
        "ema_slow": np.array([close, close]),
        "ema_regime": np.array([close - 10.0, close - 10.0]),
        "adx": np.array([30.0, 30.0]),
        "atr": np.array([atr_value, atr_value]),
    }


def _position(highest: str) -> Position:
    return Position(
        pair=BTC,
        strategy="ema_trend",
        qty=Decimal("1"),
        entry_price=d("95"),
        entry_time=T0,
        stop_price=d("90"),
        highest_close_since_entry=d(highest),
        client_order_id=make_client_order_id("ema_trend", BTC, T0, Side.BUY),
    )


def test_flat_market_without_volatility_holds() -> None:
    """ATR = 0 (o tan chico que redondea a 0): sin stop posible, no hay entrada ni trailing."""
    strategy = EmaTrend.from_params(**SMALL)
    arrays = _two_candle_arrays(100.0)
    for tiny_atr in (0.0, 1e-10):
        indicators = _bullish_cross_indicators(100.0, tiny_atr)
        signal = strategy.on_candle(StrategyContext(ohlcv=arrays, indicators=indicators, index=1))
        assert signal.action is SignalAction.HOLD
        assert "atr" in signal.note
        ctx = StrategyContext(
            ohlcv=arrays, indicators=indicators, index=1, position=_position("100")
        )
        assert strategy.trailing_stop(ctx) is None


def test_stop_and_trailing_are_exact_decimals() -> None:
    strategy = EmaTrend.from_params(**SMALL)
    arrays = _two_candle_arrays(100.0)
    indicators = _bullish_cross_indicators(100.0, 1.0)
    signal = strategy.on_candle(StrategyContext(ohlcv=arrays, indicators=indicators, index=1))
    assert signal.action is SignalAction.ENTER_LONG
    assert signal.stop_price == Decimal("98")  # 100 − 2 × 1.0, sin ruido binario
    assert signal.stop_price < arrays.candles[1].close
    ctx = StrategyContext(ohlcv=arrays, indicators=indicators, index=1, position=_position("120"))
    assert strategy.trailing_stop(ctx) == Decimal("117")  # 120 − 3 × 1.0
    assert (
        strategy.trailing_stop(ctx.__class__(ohlcv=arrays, indicators=indicators, index=1)) is None
    )


def test_trailing_never_returns_non_positive_level() -> None:
    strategy = EmaTrend.from_params(**SMALL)
    arrays = _two_candle_arrays(100.0)
    indicators = _bullish_cross_indicators(100.0, 50.0)  # 3 × 50 > highest
    ctx = StrategyContext(ohlcv=arrays, indicators=indicators, index=1, position=_position("100"))
    assert strategy.trailing_stop(ctx) is None


def test_longest_period_counts_wilder_twice() -> None:
    strategy = EmaTrend.from_params(
        ema_fast=2, ema_slow=3, ema_regime=10, adx_period=2, atr_period=100
    )
    assert strategy.longest_period == 200
    assert strategy.warmup_candles == 1200
    assert EmaTrend.from_params(**SMALL).longest_period == 12
