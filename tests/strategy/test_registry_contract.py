"""Contrato entre config, registro y warmup, y validaciones del contexto."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.factories import make_series
from tradingbot.config import StrategyConfig
from tradingbot.domain import ConfigError
from tradingbot.strategy import (
    OhlcvArrays,
    Strategy,
    StrategyContext,
    StrategyParams,
    build_strategy,
    effective_warmup,
)
from tradingbot.strategy.strategies import EmaTrend


def test_context_bars_since_exit_validation() -> None:
    arrays = OhlcvArrays.from_candles(make_series(n=3))
    with pytest.raises(ValueError, match="bars_since_exit"):
        StrategyContext(ohlcv=arrays, indicators={}, index=0, bars_since_exit=-1)
    ctx = StrategyContext(ohlcv=arrays, indicators={}, index=0, bars_since_exit=0)
    assert ctx.bars_since_exit == 0


class _LowMultiplierParams(StrategyParams):
    warmup_multiplier: int = 2


class _LowMultiplier(EmaTrend):
    name = "low_mult_tst"
    Params = _LowMultiplierParams  # type: ignore[assignment]

    @property
    def longest_period(self) -> int:
        return 10


def test_warmup_multiplier_below_minimum_is_rejected() -> None:
    strategy = _LowMultiplier.__new__(_LowMultiplier)
    strategy.params = _LowMultiplierParams()  # type: ignore[assignment]
    with pytest.raises(ValueError, match="warmup_multiplier"):
        _ = strategy.warmup_candles


def test_config_warmup_can_only_extend_strategy_warmup() -> None:
    base = {"name": "ema_trend", "pairs": ["BTC/USDT"]}
    with pytest.raises(ConfigError, match="menor que el mínimo"):
        build_strategy(StrategyConfig(**base, warmup_candles=100))
    strategy = build_strategy(StrategyConfig(**base, warmup_candles=1500))
    assert strategy.warmup_candles == 1200
    assert effective_warmup(StrategyConfig(**base, warmup_candles=1500), strategy) == 1500
    assert effective_warmup(StrategyConfig(**base), strategy) == 1200
    assert effective_warmup(StrategyConfig(**base, warmup_candles=1200), strategy) == 1200


def test_to_price_can_round_to_zero() -> None:
    # Por eso ema_trend valida la distancia ya redondeada antes de construir la señal.
    assert Strategy.to_price(3e-9) == Decimal("0.0")
    assert Strategy.to_price(26568.056417384) == Decimal("26568.05641738")
