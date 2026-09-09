"""`ema_trend` v1: seguimiento de tendencia con cruce de EMAs, filtro de régimen y ADX.

Spec: `docs/strategy/ema-trend-v1.md`. Reglas evaluadas al cierre de la vela `t`:
- Régimen: `close > EMA(ema_regime)` habilita entradas (no cierra posiciones).
- Entrada `cross`: EMA rápida cruza sobre la lenta con `ADX > adx_threshold`.
  Entrada `state`: rápida > lenta, ADX sobre el umbral y `cooldown_candles` desde la última salida.
- Stop inicial `close − stop_atr_mult × ATR`; trailing chandelier
  `highest_close_since_entry − trailing_atr_mult × ATR`.
- Salida por señal: rápida cruza bajo la lenta.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from tradingbot.domain.enums import ExitReason, SignalAction
from tradingbot.domain.orders import Signal
from tradingbot.indicators.core import FloatArray, adx, atr, ema
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

EntryMode = Literal["cross", "state"]
_PRECISION_TOLERANCE = 1e-9


class EmaTrendParams(StrategyParams):
    ema_fast: int = Field(default=20, ge=2, le=200)
    ema_slow: int = Field(default=50, ge=3, le=400)
    ema_regime: int = Field(default=200, ge=10, le=1000)
    adx_period: int = Field(default=14, ge=2, le=100)
    adx_threshold: float = Field(default=20.0, ge=0.0, le=100.0)
    atr_period: int = Field(default=14, ge=1, le=100)
    stop_atr_mult: float = Field(default=2.0, gt=0.0, le=10.0)
    trailing_atr_mult: float = Field(default=3.0, gt=0.0, le=10.0)
    entry_mode: EntryMode = "cross"
    cooldown_candles: int = Field(default=2, ge=0, le=50)
    warmup_multiplier: int = Field(default=6, ge=5, le=20)

    @field_validator("adx_threshold", "stop_atr_mult", "trailing_atr_mult")
    @classmethod
    def _max_three_decimals(cls, value: float) -> float:
        # Más precisión que 0.001 es sobreajuste disfrazado de parámetro (freqtrade llegó igual).
        if abs(round(value, 3) - value) > _PRECISION_TOLERANCE:
            msg = f"{value} tiene más de 3 decimales"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _ordered_periods(self) -> Self:
        if not (self.ema_fast < self.ema_slow < self.ema_regime):
            msg = (
                f"se requiere ema_fast < ema_slow < ema_regime, recibido "
                f"{self.ema_fast} / {self.ema_slow} / {self.ema_regime}"
            )
            raise ValueError(msg)
        return self


@register
class EmaTrend(Strategy):
    name = "ema_trend"
    Params = EmaTrendParams
    params: EmaTrendParams

    @property
    def longest_period(self) -> int:
        # Wilder(n) pesa como una EMA(2n−1): ADX y ATR cuentan doble para el warmup.
        p = self.params
        return max(p.ema_regime, p.ema_slow, 2 * p.adx_period, 2 * p.atr_period)

    @classmethod
    def search_space(cls) -> Mapping[str, ParamRange]:
        """Rangos de la spec v1 (`ema-trend-v1.md`); `entry_mode` se itera, no se optimiza."""
        return {
            "ema_fast": IntRange(10, 30, 1),
            "ema_slow": IntRange(40, 100, 5),
            "adx_threshold": FloatRange(15.0, 30.0, 1.0),
            "stop_atr_mult": FloatRange(1.5, 4.0, 0.5),
            "trailing_atr_mult": FloatRange(2.0, 5.0, 0.5),
        }

    def compute_indicators(self, ohlcv: OhlcvArrays) -> dict[str, FloatArray]:
        p = self.params
        return {
            "ema_fast": ema(ohlcv.close, p.ema_fast),
            "ema_slow": ema(ohlcv.close, p.ema_slow),
            "ema_regime": ema(ohlcv.close, p.ema_regime),
            "adx": adx(ohlcv.high, ohlcv.low, ohlcv.close, p.adx_period),
            "atr": atr(ohlcv.high, ohlcv.low, ohlcv.close, p.atr_period),
        }

    def on_candle(self, ctx: StrategyContext) -> Signal:
        p = self.params
        fast, slow = ctx.value("ema_fast"), ctx.value("ema_slow")
        regime, adx_value, atr_value = ctx.value("ema_regime"), ctx.value("adx"), ctx.value("atr")
        if any(math.isnan(v) for v in (fast, slow, regime, adx_value, atr_value)):
            return Signal.hold(ctx.pair, ctx.open_time, note="warmup")

        prev_fast, prev_slow = ctx.prev("ema_fast"), ctx.prev("ema_slow")
        have_prev = not (math.isnan(prev_fast) or math.isnan(prev_slow))
        crossed_up = have_prev and prev_fast <= prev_slow and fast > slow
        crossed_down = have_prev and prev_fast >= prev_slow and fast < slow

        if ctx.position is not None:
            if crossed_down:
                return Signal(
                    action=SignalAction.EXIT_LONG,
                    pair=ctx.pair,
                    open_time=ctx.open_time,
                    exit_reason=ExitReason.SIGNAL,
                    note="ema_fast cruzó bajo ema_slow",
                )
            return Signal.hold(ctx.pair, ctx.open_time)

        if ctx.close <= regime:
            return Signal.hold(ctx.pair, ctx.open_time, note="régimen bajista")
        if adx_value <= p.adx_threshold:
            return Signal.hold(ctx.pair, ctx.open_time, note="sin tendencia (adx)")

        if p.entry_mode == "cross":
            trigger = crossed_up
        else:
            cooled = ctx.bars_since_exit is None or ctx.bars_since_exit >= p.cooldown_candles
            trigger = fast > slow and cooled
        if not trigger:
            return Signal.hold(ctx.pair, ctx.open_time)

        # Stop en Decimal a partir del close exacto: garantiza stop < close y evita un
        # ATR ≈ 0 que dejaría la distancia en cero (sizing indefinido).
        distance = self.to_price(p.stop_atr_mult * atr_value)
        stop = ctx.candle.close - distance
        if distance <= 0 or stop <= 0:
            return Signal.hold(ctx.pair, ctx.open_time, note="sin volatilidad (atr)")
        return Signal(
            action=SignalAction.ENTER_LONG,
            pair=ctx.pair,
            open_time=ctx.open_time,
            stop_price=stop,
            strength=adx_value,
            note=f"{p.entry_mode} adx={adx_value:.1f}",
        )

    def trailing_stop(self, ctx: StrategyContext) -> Decimal | None:
        if ctx.position is None:
            return None
        atr_value = ctx.value("atr")
        if math.isnan(atr_value):
            return None
        distance = self.to_price(self.params.trailing_atr_mult * atr_value)
        if distance <= 0:
            return None
        level = ctx.position.highest_close_since_entry - distance
        return level if level > 0 else None
