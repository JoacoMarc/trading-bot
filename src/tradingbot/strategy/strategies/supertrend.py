"""Cambio de dirección Supertrend, spec supertrend-v1.md."""

from __future__ import annotations

import math
from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from tradingbot.domain.enums import ExitReason, SignalAction
from tradingbot.domain.errors import ConfigError
from tradingbot.domain.orders import Signal
from tradingbot.indicators.core import FloatArray
from tradingbot.indicators.supertrend import supertrend, supertrend_step
from tradingbot.strategy.base import (
    FloatRange,
    IntRange,
    OhlcvArrays,
    ParamRange,
    Strategy,
    StrategyContext,
    StrategyParams,
)
from tradingbot.strategy.registry import register


class SupertrendParams(StrategyParams):
    atr_period: int = Field(default=10, ge=2, le=100)
    multiplier: float = Field(default=3.0, gt=0, le=10)
    stop_atr_mult: float = Field(default=3.0, gt=0, le=10)
    bars_per_day: Literal[6, 24] = 6


@register
class Supertrend(Strategy):
    name = "supertrend"
    Params = SupertrendParams
    params: SupertrendParams
    recursive_indicators = True

    @property
    def longest_period(self) -> int:
        return max(202 * self.params.bars_per_day // 6, 2 * self.params.atr_period, 28)

    @classmethod
    def search_space(cls) -> Mapping[str, ParamRange]:
        return {
            "atr_period": IntRange(8, 12, 1),
            "multiplier": FloatRange(2.4, 3.6, 0.1),
            "stop_atr_mult": FloatRange(2.4, 3.6, 0.1),
        }

    def compute_indicators(self, ohlcv: OhlcvArrays) -> dict[str, FloatArray]:
        if ohlcv.timeframe.ms * self.params.bars_per_day != 86_400_000:
            raise ConfigError("bars_per_day no coincide con timeframe")
        return supertrend(
            ohlcv.high, ohlcv.low, ohlcv.close, self.params.atr_period, self.params.multiplier
        )

    def indicator_step(
        self, state: Mapping[str, Any], high: float, low: float, close: float
    ) -> tuple[dict[str, Any], dict[str, float]]:
        return supertrend_step(
            state, high, low, close, self.params.atr_period, self.params.multiplier
        )

    def on_candle(self, ctx: StrategyContext) -> Signal:
        direction = ctx.value("direction")
        if ctx.position is not None:
            if direction == -1:
                return Signal(
                    action=SignalAction.EXIT_LONG,
                    pair=ctx.pair,
                    open_time=ctx.open_time,
                    exit_reason=ExitReason.SIGNAL,
                    note="Supertrend bajista",
                )
            return Signal.hold(ctx.pair, ctx.open_time)
        volatility, line = ctx.value("atr_stop"), ctx.value("line")
        if not (
            direction == 1
            and ctx.prev("direction") == -1
            and ctx.candle.volume > 0
            and math.isfinite(volatility)
            and volatility > 0
            and math.isfinite(line)
        ):
            return Signal.hold(ctx.pair, ctx.open_time)
        distance = self.to_price(self.params.stop_atr_mult * volatility)
        stop = ctx.candle.close - distance
        if distance <= 0 or stop <= 0:
            return Signal.hold(ctx.pair, ctx.open_time, note="stop inválido")
        return Signal(
            action=SignalAction.ENTER_LONG,
            pair=ctx.pair,
            open_time=ctx.open_time,
            stop_price=stop,
            strength=(ctx.close - line) / volatility,
            note="cambio alcista Supertrend",
        )

    def trailing_stop(self, ctx: StrategyContext) -> Decimal | None:
        value = ctx.value("atr_stop")
        if ctx.position is None or not math.isfinite(value) or value <= 0:
            return None
        distance = self.to_price(self.params.stop_atr_mult * value)
        stop = ctx.position.highest_close_since_entry - distance
        return stop if distance > 0 and stop > 0 else None
