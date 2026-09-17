"""Rupturas de canales anteriores a la vela actual, spec donchian-v1.md."""

from __future__ import annotations

import math
from collections.abc import Mapping
from decimal import Decimal
from typing import Self

import numpy as np
from pydantic import Field, model_validator

from tradingbot.domain.enums import ExitReason, SignalAction
from tradingbot.domain.errors import ConfigError
from tradingbot.domain.orders import Signal
from tradingbot.domain.timeframe import Timeframe
from tradingbot.indicators.core import FloatArray, atr, highest, lowest
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


class DonchianParams(StrategyParams):
    entry_period: int = Field(default=60, ge=2, le=500)
    exit_period: int = Field(default=20, ge=1, le=499)
    atr_mult: float = Field(default=3.0, gt=0, le=10)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.exit_period >= self.entry_period:
            raise ValueError("exit_period debe ser menor que entry_period")
        return self


@register
class Donchian(Strategy):
    name = "donchian"
    Params = DonchianParams
    params: DonchianParams

    @property
    def longest_period(self) -> int:
        return max(202, self.params.entry_period + 1)

    @classmethod
    def search_space(cls) -> Mapping[str, ParamRange]:
        return {
            "entry_period": IntRange(48, 72, 1),
            "exit_period": IntRange(16, 24, 1),
            "atr_mult": FloatRange(2.4, 3.6, 0.1),
        }

    def compute_indicators(self, ohlcv: OhlcvArrays) -> dict[str, FloatArray]:
        if ohlcv.timeframe is not Timeframe.H4:
            raise ConfigError("donchian v1 exige timeframe 4h")

        def lag(values: FloatArray) -> FloatArray:
            result = np.full(len(values), np.nan)
            result[1:] = values[:-1]
            return result

        return {
            "upper": lag(highest(ohlcv.high, self.params.entry_period)),
            "lower": lag(lowest(ohlcv.low, self.params.exit_period)),
            "atr": atr(ohlcv.high, ohlcv.low, ohlcv.close, 14),
        }

    def on_candle(self, ctx: StrategyContext) -> Signal:
        if ctx.position is not None:
            lower = ctx.value("lower")
            if math.isfinite(lower) and ctx.close < lower:
                return Signal(
                    action=SignalAction.EXIT_LONG,
                    pair=ctx.pair,
                    open_time=ctx.open_time,
                    exit_reason=ExitReason.SIGNAL,
                    note="ruptura del canal inferior",
                )
            return Signal.hold(ctx.pair, ctx.open_time)
        upper, volatility = ctx.value("upper"), ctx.value("atr")
        if not all(math.isfinite(v) for v in (upper, volatility)) or volatility <= 0:
            return Signal.hold(ctx.pair, ctx.open_time, note="warmup o ATR inválido")
        if ctx.close <= upper:
            return Signal.hold(ctx.pair, ctx.open_time)
        distance = self.to_price(self.params.atr_mult * volatility)
        stop = ctx.candle.close - distance
        if distance <= 0 or stop <= 0:
            return Signal.hold(ctx.pair, ctx.open_time, note="stop inválido")
        return Signal(
            action=SignalAction.ENTER_LONG,
            pair=ctx.pair,
            open_time=ctx.open_time,
            stop_price=stop,
            strength=(ctx.close - upper) / volatility,
            note="ruptura Donchian",
        )

    def trailing_stop(self, ctx: StrategyContext) -> Decimal | None:
        value = ctx.value("atr")
        if ctx.position is None or not math.isfinite(value) or value <= 0:
            return None
        distance = self.to_price(self.params.atr_mult * value)
        level = ctx.position.highest_close_since_entry - distance
        return level if distance > 0 and level > 0 else None
