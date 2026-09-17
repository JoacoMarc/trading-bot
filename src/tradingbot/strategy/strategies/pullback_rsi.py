"""Retrocesos en tendencia, spec pullback-rsi-v1.md."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Self

from pydantic import Field, model_validator

from tradingbot.domain.enums import ExitReason, SignalAction
from tradingbot.domain.errors import ConfigError
from tradingbot.domain.orders import Signal
from tradingbot.domain.timeframe import Timeframe
from tradingbot.indicators.core import FloatArray, atr, ema, rsi
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


class PullbackRsiParams(StrategyParams):
    rsi_entry: int = Field(default=10, ge=1, le=49)
    rsi_exit: int = Field(default=70, ge=50, le=99)
    stop_atr_mult: float = Field(default=2.5, gt=0, le=10)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.rsi_entry >= self.rsi_exit:
            raise ValueError("rsi_entry debe ser menor que rsi_exit")
        return self


@register
class PullbackRsi(Strategy):
    name = "pullback_rsi"
    Params = PullbackRsiParams
    params: PullbackRsiParams

    @property
    def longest_period(self) -> int:
        return 202

    @classmethod
    def search_space(cls) -> Mapping[str, ParamRange]:
        return {
            "rsi_entry": IntRange(8, 12, 1),
            "rsi_exit": IntRange(56, 84, 1),
            "stop_atr_mult": FloatRange(2.0, 3.0, 0.1),
        }

    def compute_indicators(self, ohlcv: OhlcvArrays) -> dict[str, FloatArray]:
        if ohlcv.timeframe is not Timeframe.H4:
            raise ConfigError("pullback_rsi v1 exige timeframe 4h")
        return {
            "ema": ema(ohlcv.close, 200),
            "rsi": rsi(ohlcv.close, 2),
            "atr": atr(ohlcv.high, ohlcv.low, ohlcv.close, 14),
        }

    def on_candle(self, ctx: StrategyContext) -> Signal:
        p = self.params
        current, previous = ctx.value("rsi"), ctx.prev("rsi")
        if ctx.position is not None:
            tf = ctx.candle.timeframe.ms
            entry_bar = ctx.position.entry_time // tf * tf
            expired = ctx.open_time + tf >= entry_bar + 48 * 3_600_000
            if expired or (math.isfinite(current) and current >= p.rsi_exit):
                return Signal(
                    action=SignalAction.EXIT_LONG,
                    pair=ctx.pair,
                    open_time=ctx.open_time,
                    exit_reason=ExitReason.SIGNAL,
                    note="plazo 48h" if expired else "rebote RSI",
                )
            return Signal.hold(ctx.pair, ctx.open_time)
        average, volatility = ctx.value("ema"), ctx.value("atr")
        if not all(math.isfinite(v) for v in (current, previous, average, volatility)):
            return Signal.hold(ctx.pair, ctx.open_time, note="warmup")
        if ctx.close <= average or not previous <= p.rsi_entry < current:
            return Signal.hold(ctx.pair, ctx.open_time)
        distance = self.to_price(p.stop_atr_mult * volatility)
        stop = ctx.candle.close - distance
        if distance <= 0 or stop <= 0:
            return Signal.hold(ctx.pair, ctx.open_time, note="ATR inválido")
        return Signal(
            action=SignalAction.ENTER_LONG,
            pair=ctx.pair,
            open_time=ctx.open_time,
            stop_price=stop,
            strength=100 - previous,
            note="recuperación RSI en tendencia",
        )
