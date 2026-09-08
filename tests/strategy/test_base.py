from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import numpy as np
import pytest
from pydantic import ValidationError

from tests.factories import BTC, ETH, T0, d, make_candle, make_position, make_series
from tradingbot.config import StrategyConfig
from tradingbot.domain import ConfigError, DomainError, Signal, Timeframe
from tradingbot.indicators import FloatArray
from tradingbot.strategy import (
    OhlcvArrays,
    Strategy,
    StrategyContext,
    StrategyParams,
    available_strategies,
    build_strategy,
    get_strategy_class,
    register,
)
from tradingbot.strategy.strategies import EmaTrend, EmaTrendParams


def test_ohlcv_arrays_from_candles_and_slices() -> None:
    candles = make_series(n=6)
    arrays = OhlcvArrays.from_candles(candles)
    assert len(arrays) == 6
    assert arrays.pair == BTC
    assert arrays.timeframe is Timeframe.H4
    assert arrays.open_time.dtype == np.int64
    assert arrays.close.dtype == np.float64
    np.testing.assert_array_equal(arrays.close, [101, 102, 103, 104, 105, 106])
    view = arrays.slice(2, 5)
    assert len(view) == 3
    assert view.candles[0] is candles[2]
    assert np.shares_memory(view.close, arrays.close)
    with pytest.raises(ValueError, match="inválido"):
        arrays.slice(3, 3)


def test_ohlcv_arrays_rejects_mixed_or_unordered_candles() -> None:
    with pytest.raises(DomainError, match="al menos una vela"):
        OhlcvArrays.from_candles([])
    with pytest.raises(DomainError, match="mezcladas"):
        OhlcvArrays.from_candles(
            [make_candle(pair=BTC), make_candle(pair=ETH, open_time=T0 + Timeframe.H4.ms)]
        )
    with pytest.raises(DomainError, match="orden temporal"):
        OhlcvArrays.from_candles(
            [make_candle(open_time=T0 + Timeframe.H4.ms), make_candle(open_time=T0)]
        )
    with pytest.raises(DomainError, match="orden temporal"):
        OhlcvArrays.from_candles([make_candle(), make_candle()])


def test_context_only_exposes_data_up_to_index() -> None:
    arrays = OhlcvArrays.from_candles(make_series(n=10))
    indicator = np.arange(10, dtype=np.float64)
    ctx = StrategyContext(
        ohlcv=arrays,
        indicators={"x": indicator},
        index=4,
        equity=Decimal(1000),
        cash=Decimal(500),
    )
    assert ctx.pair == BTC
    assert ctx.timeframe is Timeframe.H4
    assert ctx.index == 4
    assert ctx.open_time == T0 + 4 * Timeframe.H4.ms
    assert ctx.close == 105.0
    assert ctx.candle.close == d("105")
    assert ctx.value("x") == 4.0
    assert ctx.prev("x") == 3.0
    assert ctx.prev("x", back=4) == 0.0
    assert np.isnan(ctx.prev("x", back=5))
    np.testing.assert_array_equal(ctx.series("x"), [0, 1, 2, 3, 4])
    assert len(ctx.candles) == 5
    assert ctx.has("x")
    assert not ctx.has("y")
    with pytest.raises(ValueError, match="back"):
        ctx.prev("x", back=0)


def test_context_validation() -> None:
    arrays = OhlcvArrays.from_candles(make_series(n=5))
    with pytest.raises(ValueError, match="fuera de rango"):
        StrategyContext(ohlcv=arrays, indicators={}, index=5)
    with pytest.raises(ValueError, match="valores para"):
        StrategyContext(ohlcv=arrays, indicators={"x": np.zeros(3)}, index=0)
    with pytest.raises(ValueError, match="posición de"):
        StrategyContext(ohlcv=arrays, indicators={}, index=0, position=make_position(pair=ETH))


class _Params(StrategyParams):
    period: int = 3


class _Dummy(Strategy):
    name = "dummy_test"
    Params = _Params
    params: _Params

    @property
    def longest_period(self) -> int:
        return self.params.period

    def compute_indicators(self, ohlcv: OhlcvArrays) -> dict[str, FloatArray]:
        return {"close": ohlcv.close.copy()}

    def on_candle(self, ctx: StrategyContext) -> Signal:
        return Signal.hold(ctx.pair, ctx.open_time)


@pytest.fixture(autouse=True, scope="module")
def _register_dummy() -> Iterator[None]:
    """Registra `_Dummy` solo mientras corre este módulo; no debe filtrarse a otros tests."""
    from tradingbot.strategy import registry

    register(_Dummy)
    yield
    registry._REGISTRY.pop("dummy_test", None)


def test_registry_and_builder() -> None:
    assert "ema_trend" in available_strategies()
    assert "dummy_test" in available_strategies()
    assert get_strategy_class("ema_trend") is EmaTrend
    strategy = build_strategy(
        StrategyConfig(
            name="ema_trend", pairs=["BTC/USDT"], params={"ema_fast": 10, "ema_slow": 30}
        )
    )
    assert isinstance(strategy, EmaTrend)
    assert strategy.params.ema_fast == 10
    assert strategy.warmup_candles == 6 * 200
    assert repr(strategy).startswith("EmaTrend(")
    with pytest.raises(ConfigError, match="desconocida"):
        get_strategy_class("nope")
    with pytest.raises(ConfigError, match="parámetros inválidos"):
        build_strategy(
            StrategyConfig(name="ema_trend", pairs=["BTC/USDT"], params={"ema_fast": 500})
        )


def test_register_rejects_bad_or_duplicate_names() -> None:
    with pytest.raises(ValueError, match="snake_case"):
        register(type("Bad", (_Dummy,), {"name": "Bad-Name"}))
    with pytest.raises(ValueError, match="ya registrada"):
        register(type("Other", (_Dummy,), {"name": "dummy_test"}))
    assert register(_Dummy) is _Dummy  # re-registrar la misma clase es idempotente


def test_strategy_params_handling() -> None:
    dummy = _Dummy({"period": 5})
    assert dummy.params.period == 5
    assert dummy.warmup_candles == 6 * 5
    assert _Dummy.from_params(period=2).longest_period == 2
    assert _Dummy().params.period == 3
    assert (
        _Dummy().trailing_stop(
            StrategyContext(
                ohlcv=OhlcvArrays.from_candles(make_series(n=3)), indicators={}, index=0
            )
        )
        is None
    )
    with pytest.raises(TypeError, match="espera _Params"):
        _Dummy(EmaTrendParams())
    with pytest.raises(ValidationError):
        _Dummy({"periodo": 5})
    assert Strategy.to_price(26568.056417384) == Decimal("26568.05641738")
