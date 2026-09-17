"""Reglas congeladas, bordes temporales y paridad de las candidatas."""

from __future__ import annotations

import numpy as np
import pytest

from tests.factories import BTC, T0, d, make_candle
from tradingbot.domain import Position, SignalAction, Timeframe
from tradingbot.strategy import OhlcvArrays, StrategyContext
from tradingbot.strategy.base import Strategy
from tradingbot.strategy.strategies import Donchian, PullbackRsi
from tradingbot.validation.equivalence import assert_equivalent


def context(
    values: dict[str, list[float]],
    *,
    position: Position | None = None,
    index: int = 1,
    close: str = "100",
) -> StrategyContext:
    candles = [
        make_candle(
            open_time=T0 + i * Timeframe.H4.ms, open=close, high="110", low="90", close=close
        )
        for i in range(index + 1)
    ]
    indicators = {k: np.array(v, dtype=float) for k, v in values.items()}
    return StrategyContext(
        ohlcv=OhlcvArrays.from_candles(candles),
        indicators=indicators,
        index=index,
        position=position,
    )


def position(strategy: str, entry: int = T0) -> Position:
    return Position(
        pair=BTC,
        strategy=strategy,
        qty=d("1"),
        entry_price=d("100"),
        entry_time=entry,
        stop_price=d("80"),
        highest_close_since_entry=d("120"),
        client_order_id="entry-test",
    )


def test_pullback_cross_threshold_ranking_and_initial_stop() -> None:
    strategy = PullbackRsi()
    values: dict[str, list[float]] = {"rsi": [10, 11], "ema": [90, 90], "atr": [2, 2]}
    signal = strategy.on_candle(context(values))
    assert signal.action is SignalAction.ENTER_LONG
    assert signal.stop_price == d("95")
    assert signal.strength == 90
    values["rsi"] = [5, 11]
    assert strategy.on_candle(context(values)).strength == 95
    values["rsi"] = [10, 10]
    assert strategy.on_candle(context(values)).action is SignalAction.HOLD
    values["rsi"] = [11, 12]
    assert strategy.on_candle(context(values)).action is SignalAction.HOLD
    values["rsi"] = [5, 11]
    values["ema"] = [100, 100]
    assert strategy.on_candle(context(values)).action is SignalAction.HOLD


def test_pullback_exit_does_not_need_atr_and_timeout_survives_serialization() -> None:
    strategy = PullbackRsi()
    values: dict[str, list[float]] = {"rsi": [50, 70], "ema": [np.nan, np.nan], "atr": [0, 0]}
    assert (
        strategy.on_candle(context(values, position=position(strategy.name))).action
        is SignalAction.EXIT_LONG
    )
    original = position(strategy.name, T0 + 10_000)
    restored = Position.model_validate_json(original.model_dump_json())
    # Cierre de la vela 11 = 48h, aunque el fill llegó unos segundos después del open.
    for index, expected in ((10, SignalAction.HOLD), (11, SignalAction.EXIT_LONG)):
        ctx = context({"rsi": [np.nan] * (index + 1)}, index=index, position=restored)
        assert strategy.on_candle(ctx).action is expected


def test_donchian_excludes_current_candle_and_requires_strict_breakout() -> None:
    strategy = Donchian.from_params(entry_period=3, exit_period=2)
    candles = [
        make_candle(
            open_time=T0 + i * Timeframe.H4.ms,
            open="100",
            close="100",
            high=str(101 + i),
            low=str(90 - i),
        )
        for i in range(5)
    ]
    series = strategy.compute_indicators(OhlcvArrays.from_candles(candles))
    assert np.isnan(series["upper"][2])
    assert series["upper"][3] == 103  # high actual = 104
    assert series["lower"][3] == 88
    values: dict[str, list[float]] = {"upper": [100, 100], "lower": [90, 90], "atr": [2, 2]}
    assert strategy.on_candle(context(values)).action is SignalAction.HOLD
    signal = strategy.on_candle(context(values, close="101"))
    assert signal.action is SignalAction.ENTER_LONG
    assert signal.stop_price == d("95")
    assert signal.strength == 0.5


def test_donchian_exit_without_atr_and_chandelier() -> None:
    strategy = Donchian()
    p = position(strategy.name)
    values: dict[str, list[float]] = {"lower": [101, 101], "atr": [np.nan, np.nan]}
    assert strategy.on_candle(context(values, position=p)).action is SignalAction.EXIT_LONG
    assert strategy.trailing_stop(context(values, position=p)) is None
    values["atr"] = [2, 2]
    assert strategy.trailing_stop(context(values, position=p)) == d("114")


@pytest.mark.parametrize("strategy", [PullbackRsi(), Donchian()])
def test_candidates_no_lookahead_and_rolling_equivalence(
    strategy: Strategy, btc_2023: OhlcvArrays, eth_2023: OhlcvArrays
) -> None:
    assert strategy.warmup_candles >= 202 * 6
    for series in (btc_2023, eth_2023):
        assert_equivalent(strategy, series)
