"""Contrato de estrategia: `Strategy`, `StrategyParams`, `OhlcvArrays` y `StrategyContext`.

Una estrategia es determinística y sin estado propio: recibe velas **cerradas** como arrays,
precomputa sus indicadores una vez por par (`compute_indicators`) y decide por vela con
`on_candle(ctx)`, donde `ctx` solo expone datos hasta la vela actual (vista truncada, ADR-0002).
El mismo código corre en backtest (indicadores precomputados sobre toda la serie) y en live
(recomputados sobre la ventana de warmup); `validation/equivalence.py` verifica que den lo mismo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, ClassVar, Self

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from tradingbot.domain.candle import Candle
from tradingbot.domain.errors import DomainError
from tradingbot.domain.money import to_decimal
from tradingbot.domain.orders import Signal
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import Position
from tradingbot.domain.timeframe import Timeframe
from tradingbot.indicators.core import FloatArray

IntArray = NDArray[np.int64]
DEFAULT_WARMUP_MULTIPLIER = 6
MIN_WARMUP_MULTIPLIER = 5  # PLAN §2.2: warmup ≥ 5 × período más largo


class StrategyParams(BaseModel):
    """Base de los parámetros de una estrategia: inmutables y sin claves desconocidas."""

    model_config = ConfigDict(frozen=True, extra="forbid")


@dataclass(frozen=True, slots=True)
class IntRange:
    """Rango entero a optimizar (ADR-0008), inclusive, con paso."""

    low: int
    high: int
    step: int = 1


@dataclass(frozen=True, slots=True)
class FloatRange:
    """Rango real a optimizar, inclusive, cuantizado al paso (≤ 3 decimales)."""

    low: float
    high: float
    step: float


@dataclass(frozen=True, slots=True)
class Choice:
    """Parámetro categórico a optimizar."""

    options: tuple[Any, ...]


ParamRange = IntRange | FloatRange | Choice


class OhlcvArrays:
    """Velas cerradas de un par en orden temporal, como arrays float64 más las `Candle` originales.

    Es la única frontera Decimal → float del proyecto (ADR-0003): los indicadores trabajan sobre
    estos arrays y las decisiones de dinero vuelven a `Decimal` con `to_decimal`.
    """

    __slots__ = (
        "candles",
        "close",
        "high",
        "low",
        "open",
        "open_time",
        "pair",
        "timeframe",
        "volume",
    )

    def __init__(
        self,
        pair: Pair,
        timeframe: Timeframe,
        candles: tuple[Candle, ...],
        open_time: IntArray,
        open: FloatArray,
        high: FloatArray,
        low: FloatArray,
        close: FloatArray,
        volume: FloatArray,
    ) -> None:
        self.pair = pair
        self.timeframe = timeframe
        self.candles = candles
        self.open_time = open_time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

    @classmethod
    def from_candles(cls, candles: Sequence[Candle]) -> OhlcvArrays:
        if not candles:
            msg = "OhlcvArrays necesita al menos una vela"
            raise DomainError(msg)
        first = candles[0]
        for candle in candles:
            if candle.pair != first.pair or candle.timeframe is not first.timeframe:
                msg = (
                    f"velas de {candle.pair} {candle.timeframe.value} mezcladas con "
                    f"{first.pair} {first.timeframe.value}"
                )
                raise DomainError(msg)
        open_time = np.fromiter((c.open_time for c in candles), dtype=np.int64, count=len(candles))
        if np.any(np.diff(open_time) <= 0):
            msg = "las velas deben estar en orden temporal estricto, sin duplicados"
            raise DomainError(msg)

        def column(attr: str) -> FloatArray:
            return np.fromiter(
                (float(getattr(c, attr)) for c in candles), dtype=np.float64, count=len(candles)
            )

        return cls(
            pair=first.pair,
            timeframe=first.timeframe,
            candles=tuple(candles),
            open_time=open_time,
            open=column("open"),
            high=column("high"),
            low=column("low"),
            close=column("close"),
            volume=column("volume"),
        )

    def __len__(self) -> int:
        return int(self.open_time.size)

    def slice(self, start: int, stop: int) -> OhlcvArrays:
        """Sub-rango `[start, stop)`: los arrays son vistas; la tupla de velas copia referencias."""
        if not (0 <= start < stop <= len(self)):
            msg = f"rango [{start}, {stop}) inválido para {len(self)} velas"
            raise ValueError(msg)
        return OhlcvArrays(
            pair=self.pair,
            timeframe=self.timeframe,
            candles=self.candles[start:stop],
            open_time=self.open_time[start:stop],
            open=self.open[start:stop],
            high=self.high[start:stop],
            low=self.low[start:stop],
            close=self.close[start:stop],
            volume=self.volume[start:stop],
        )


class StrategyContext:
    """Lo que la estrategia ve al cierre de la vela `index`: nada posterior.

    Guarda los arrays completos (precomputados) pero solo expone valores y vistas hasta `index`.
    `equity` y `cash` en Decimal. `bars_since_exit` sirve para cooldowns: vale 0 en la vela cuyo
    cierre sigue inmediatamente al fill de la última salida en el par, suma 1 por vela cerrada
    y es None si nunca hubo salida. Todo broker (simulado, paper, live) debe respetar esa
    definición para no romper la paridad en una vela.
    """

    __slots__ = (
        "_indicators",
        "_ohlcv",
        "bars_since_exit",
        "cash",
        "equity",
        "index",
        "position",
    )

    def __init__(
        self,
        *,
        ohlcv: OhlcvArrays,
        indicators: Mapping[str, FloatArray],
        index: int,
        position: Position | None = None,
        equity: Decimal = Decimal(0),
        cash: Decimal = Decimal(0),
        bars_since_exit: int | None = None,
    ) -> None:
        if not (0 <= index < len(ohlcv)):
            msg = f"index {index} fuera de rango para {len(ohlcv)} velas"
            raise ValueError(msg)
        for name, array in indicators.items():
            if array.shape != ohlcv.open_time.shape:
                msg = f"indicador {name!r} con {array.size} valores para {len(ohlcv)} velas"
                raise ValueError(msg)
        if position is not None and position.pair != ohlcv.pair:
            msg = f"posición de {position.pair} en contexto de {ohlcv.pair}"
            raise ValueError(msg)
        if bars_since_exit is not None and bars_since_exit < 0:
            msg = f"bars_since_exit negativo: {bars_since_exit}"
            raise ValueError(msg)
        self._ohlcv = ohlcv
        self._indicators = dict(indicators)
        self.index = index
        self.position = position
        self.equity = equity
        self.cash = cash
        self.bars_since_exit = bars_since_exit

    @property
    def pair(self) -> Pair:
        return self._ohlcv.pair

    @property
    def timeframe(self) -> Timeframe:
        return self._ohlcv.timeframe

    @property
    def candle(self) -> Candle:
        """Vela actual con precios exactos en Decimal."""
        return self._ohlcv.candles[self.index]

    @property
    def open_time(self) -> int:
        return int(self._ohlcv.open_time[self.index])

    @property
    def close(self) -> float:
        return float(self._ohlcv.close[self.index])

    @property
    def candles(self) -> OhlcvArrays:
        """Velas cerradas hasta la actual inclusive (vista, sin copiar)."""
        return self._ohlcv.slice(0, self.index + 1)

    def has(self, name: str) -> bool:
        return name in self._indicators

    def series(self, name: str) -> FloatArray:
        """Serie del indicador hasta la vela actual inclusive (vista)."""
        return self._indicators[name][: self.index + 1]

    def value(self, name: str) -> float:
        """Valor del indicador en la vela actual (puede ser NaN durante el warmup)."""
        return float(self._indicators[name][self.index])

    def prev(self, name: str, back: int = 1) -> float:
        """Valor `back` velas atrás; NaN si no existe."""
        if back < 1:
            msg = f"back debe ser >= 1, recibido {back}"
            raise ValueError(msg)
        position = self.index - back
        if position < 0:
            return float("nan")
        return float(self._indicators[name][position])


class Strategy(ABC):
    """Base de toda estrategia. Las subclases se registran con `@register` (ver `registry.py`).

    - `name`: identificador (≤ 12 chars, snake_case) usado en config y en el `client_order_id`.
    - `Params`: modelo pydantic de parámetros; `params` es la instancia validada.
    - `longest_period`: período más largo de sus indicadores; `warmup_candles` lo multiplica.
    """

    name: ClassVar[str]
    Params: ClassVar[type[StrategyParams]] = StrategyParams
    recursive_indicators: ClassVar[bool] = False

    def __init__(self, params: StrategyParams | Mapping[str, Any] | None = None) -> None:
        if isinstance(params, StrategyParams):
            if not isinstance(params, self.Params):
                msg = (
                    f"{type(self).__name__} espera {self.Params.__name__}, "
                    f"recibió {type(params).__name__}"
                )
                raise TypeError(msg)
            self.params = params
        else:
            self.params = self.Params.model_validate(dict(params or {}))

    @classmethod
    def from_params(cls, **params: Any) -> Self:
        return cls(cls.Params.model_validate(params))

    @property
    @abstractmethod
    def longest_period(self) -> int:
        """Período más largo entre los indicadores que usa."""

    @property
    def warmup_multiplier(self) -> int:
        value = int(getattr(self.params, "warmup_multiplier", DEFAULT_WARMUP_MULTIPLIER))
        if value < MIN_WARMUP_MULTIPLIER:
            msg = f"warmup_multiplier debe ser >= {MIN_WARMUP_MULTIPLIER}, recibido {value}"
            raise ValueError(msg)
        return value

    @property
    def warmup_candles(self) -> int:
        """Velas cerradas necesarias antes de la primera decisión (≥ 5 × período más largo)."""
        return self.warmup_multiplier * self.longest_period

    @abstractmethod
    def compute_indicators(self, ohlcv: OhlcvArrays) -> dict[str, FloatArray]:
        """Indicadores vectorizados sobre velas cerradas; cada array tiene `len(ohlcv)` valores."""

    @abstractmethod
    def on_candle(self, ctx: StrategyContext) -> Signal:
        """Decisión al cierre de la vela `ctx.index`, solo con lo que `ctx` expone."""

    def trailing_stop(self, ctx: StrategyContext) -> Decimal | None:
        """Nivel de stop deseado para la posición abierta; el `PositionManager` solo lo sube."""
        return None

    def indicator_step(
        self, state: Mapping[str, Any], high: float, low: float, close: float
    ) -> tuple[dict[str, Any], dict[str, float]]:
        """Paso puro de indicadores con checkpoint externo (ADR-0014)."""
        raise NotImplementedError("esta estrategia no usa indicadores recursivos persistidos")

    @classmethod
    def search_space(cls) -> Mapping[str, ParamRange]:
        """Parámetros a optimizar y sus rangos (ADR-0008); vacío = no se optimiza."""
        return {}

    @staticmethod
    def to_price(value: float) -> Decimal:
        """float del indicador → Decimal de precio (8 decimales, como Binance)."""
        return to_decimal(round(value, 8))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.params!r})"
