"""`regime_bh` v1: BTC long mientras el régimen diario está encendido, en cash cuando se apaga.

Spec: `docs/strategy/regime-bh-v1.md` (ADR-0010). Evaluada al cierre de cada vela del timeframe
con **días UTC completos**: el régimen del día D es `cierre_diario(D) > SMA(sma_days)` de cierres
diarios y retorno a `momentum_days` > 0. Se conoce al cerrar la última vela del día
(23:59:59.999) y la orden sale al open siguiente; las velas intermedias usan el último día
completo. Entrada: régimen encendido y sin posición (re-entra tras un stop mientras siga
encendido). Salida: régimen apagado (`SIGNAL`). Stop de seguridad `stop_pct` bajo el fill, sin
trailing. El tamaño lo fija el `RiskManager` en modo `fraction`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from decimal import Decimal

import numpy as np
from pydantic import Field

from tradingbot.domain.enums import ExitReason, SignalAction
from tradingbot.domain.errors import ConfigError
from tradingbot.domain.orders import Signal
from tradingbot.indicators.core import FloatArray, sma
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

MS_PER_DAY = 86_400_000


class RegimeBhParams(StrategyParams):
    sma_days: int = Field(default=200, ge=2, le=400)  # mínimos bajos para tests
    momentum_days: int = Field(default=30, ge=1, le=200)
    stop_pct: float = Field(default=0.20, ge=0.02, le=0.5)
    bars_per_day: int = Field(default=6, ge=1, le=1440)  # 4h -> 6, 1h -> 24


@register
class RegimeBh(Strategy):
    name = "regime_bh"
    Params = RegimeBhParams
    params: RegimeBhParams

    @property
    def longest_period(self) -> int:
        p = self.params
        return (max(p.sma_days, p.momentum_days) + 2) * p.bars_per_day

    @property
    def warmup_candles(self) -> int:
        """SMA y retorno tienen memoria finita: la ventana reproduce la serie exacta (ADR-0010)."""
        return self.longest_period

    @classmethod
    def search_space(cls) -> Mapping[str, ParamRange]:
        return {
            "sma_days": IntRange(150, 250, 10),
            "momentum_days": IntRange(20, 45, 5),
            "stop_pct": FloatRange(0.10, 0.30, 0.05),
        }

    def compute_indicators(self, ohlcv: OhlcvArrays) -> dict[str, FloatArray]:
        p = self.params
        tf_ms = ohlcv.timeframe.ms
        if tf_ms * p.bars_per_day != MS_PER_DAY:
            msg = (
                f"bars_per_day={p.bars_per_day} no corresponde al timeframe "
                f"{ohlcv.timeframe.value} ({MS_PER_DAY // tf_ms} velas por día)"
            )
            raise ConfigError(msg)
        close_time = ohlcv.open_time + tf_ms - 1
        n = len(ohlcv.close)
        nan = np.full(n, np.nan)
        # Última vela de cada día UTC completo (cierra a las 23:59:59.999).
        last_of_day = np.flatnonzero(close_time % MS_PER_DAY == MS_PER_DAY - 1)
        if last_of_day.size == 0:
            return {
                "regime": nan,
                "sma": nan.copy(),
                "momentum": nan.copy(),
                "daily_close": nan.copy(),
            }
        daily_close = ohlcv.close[last_of_day]
        daily_sma = sma(daily_close, p.sma_days)
        momentum = np.full(daily_close.shape, np.nan)
        m = p.momentum_days
        if daily_close.size > m:
            momentum[m:] = daily_close[m:] / daily_close[:-m] - 1.0
        undefined = np.isnan(daily_sma) | np.isnan(momentum)
        regime_daily = np.where(
            undefined, np.nan, ((daily_close > daily_sma) & (momentum > 0)).astype(np.float64)
        )
        # Cada vela toma el último día completo cerrado hasta su propio cierre (inclusive).
        position = np.searchsorted(close_time[last_of_day], close_time, side="right") - 1
        valid = position >= 0
        safe = np.clip(position, 0, None)

        def mapped(daily: FloatArray) -> FloatArray:
            return np.where(valid, daily[safe], np.nan)

        return {
            "regime": mapped(regime_daily),
            "sma": mapped(daily_sma),
            "momentum": mapped(momentum),
            "daily_close": mapped(daily_close),
        }

    def on_candle(self, ctx: StrategyContext) -> Signal:
        regime = ctx.value("regime")
        if math.isnan(regime):
            return Signal.hold(ctx.pair, ctx.open_time, note="warmup")
        on = regime >= 0.5
        if ctx.position is not None:
            if not on:
                return Signal(
                    action=SignalAction.EXIT_LONG,
                    pair=ctx.pair,
                    open_time=ctx.open_time,
                    exit_reason=ExitReason.SIGNAL,
                    note="régimen apagado",
                )
            return Signal.hold(ctx.pair, ctx.open_time)
        if not on:
            return Signal.hold(ctx.pair, ctx.open_time, note="régimen apagado")
        stop = ctx.candle.close * (Decimal(1) - Decimal(str(self.params.stop_pct)))
        momentum = ctx.value("momentum")
        return Signal(
            action=SignalAction.ENTER_LONG,
            pair=ctx.pair,
            open_time=ctx.open_time,
            stop_price=stop,
            strength=momentum,
            note=f"régimen encendido, momentum {momentum * 100:+.2f} %",
        )

    def trailing_stop(self, ctx: StrategyContext) -> Decimal | None:
        return None
