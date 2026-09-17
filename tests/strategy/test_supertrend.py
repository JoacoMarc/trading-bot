from __future__ import annotations

import json

import numpy as np
import pytest

from tests.factories import BTC, T0, make_candle
from tests.strategy.test_candidates import context, position
from tradingbot.domain import Bar, SignalAction, Timeframe
from tradingbot.domain.errors import DataError
from tradingbot.engine.series import RollingSeries
from tradingbot.indicators.supertrend import supertrend
from tradingbot.strategy import OhlcvArrays
from tradingbot.strategy.strategies import Supertrend
from tradingbot.validation.equivalence import assert_equivalent


def test_manual_fixture_with_equalities() -> None:
    close = np.array([10, 10, 10, 11, 12, 13, 12, 11, 10, 9], dtype=float)
    values = supertrend(close + 1, close - 1, close, 2, 1)
    assert np.isnan(values["line"][:2]).all()
    np.testing.assert_array_equal(values["upper"][2:], [12, 12, 12, 12, 14, 13, 12, 11])
    np.testing.assert_array_equal(values["lower"][2:], [8, 9, 10, 11, 11, 11, 11, 7])
    np.testing.assert_array_equal(values["direction"][2:], [-1, -1, -1, 1, 1, 1, -1, -1])


def test_persistent_direction_window_restart_and_duplicate() -> None:
    closes = [10, 10, 10, 11, 12, 13] + [13] * 100
    candles = [
        make_candle(
            open_time=T0 + i * Timeframe.H4.ms,
            open=str(c),
            close=str(c),
            high=str(c + 1),
            low=str(c - 1),
        )
        for i, c in enumerate(closes)
    ]
    strategy = Supertrend.from_params(atr_period=2, multiplier=1)
    rolling = RollingSeries(strategy, {BTC: candles[:6]}, window=20)
    full = strategy.compute_indicators(OhlcvArrays.from_candles(candles))
    for i, candle in enumerate(candles[6:], 6):
        if i == 60:
            saved = json.loads(json.dumps(rolling.checkpoint(), allow_nan=False))
            rolling = RollingSeries(
                strategy, {BTC: rolling.history(BTC)}, window=20, checkpoints=saved
            )
        bar = Bar.from_candles([candle])
        result = rolling.at(BTC, bar)
        assert result is not None
        again = rolling.at(BTC, bar)
        assert again is not None
        for key, expected in full.items():
            np.testing.assert_equal(result.indicators[key][-1], expected[i])
            np.testing.assert_array_equal(result.indicators[key], again.indicators[key])
    assert full["direction"][-1] == 1
    # El caso adversarial demuestra que recomputar sin checkpoint cambiaría la señal.
    fresh = strategy.compute_indicators(OhlcvArrays.from_candles(candles[-20:]))
    assert fresh["direction"][-1] == -1
    with pytest.raises(DataError, match="incompatible"):
        RollingSeries(
            Supertrend(), {BTC: rolling.history(BTC)}, window=20, checkpoints=rolling.checkpoint()
        )


def test_entry_exit_and_stops() -> None:
    strategy = Supertrend()
    values: dict[str, list[float]] = {"direction": [-1, 1], "line": [105, 95], "atr_stop": [2, 2]}
    signal = strategy.on_candle(context(values))
    assert signal.action is SignalAction.ENTER_LONG
    assert str(signal.stop_price) == "94.0"
    values["direction"] = [1, 1]
    assert strategy.on_candle(context(values)).action is SignalAction.HOLD
    values["direction"] = [-1, -1]
    values["atr_stop"] = [np.nan, np.nan]
    assert (
        strategy.on_candle(context(values, position=position(strategy.name))).action
        is SignalAction.EXIT_LONG
    )
    assert strategy.trailing_stop(context(values, position=position(strategy.name))) is None


def test_equivalence_with_checkpoint_and_future(
    btc_2023: OhlcvArrays, eth_2023: OhlcvArrays
) -> None:
    for arrays in (btc_2023, eth_2023):
        assert_equivalent(Supertrend(), arrays, samples=12)
    assert Supertrend.from_params(bars_per_day=24).warmup_candles >= 4848
