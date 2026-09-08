"""Velas y barras (sección transversal de velas del mismo cierre)."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe


class Candle(BaseModel):
    """Vela OHLCV cerrada. Precios en `Decimal` porque alimentan equity y `ref_price`."""

    model_config = ConfigDict(frozen=True)

    pair: Pair
    timeframe: Timeframe
    open_time: int = Field(ge=0)
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        self.timeframe.check_aligned(self.open_time)
        if self.low > self.high:
            msg = f"low {self.low} > high {self.high}"
            raise ValueError(msg)
        if not (self.low <= self.open <= self.high):
            msg = f"open {self.open} fuera de [{self.low}, {self.high}]"
            raise ValueError(msg)
        if not (self.low <= self.close <= self.high):
            msg = f"close {self.close} fuera de [{self.low}, {self.high}]"
            raise ValueError(msg)
        return self

    @property
    def close_time(self) -> int:
        """Último milisegundo de la vela (inclusive)."""
        return self.timeframe.close_time(self.open_time)

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open

    @property
    def price_range(self) -> Decimal:
        return self.high - self.low


class Bar(BaseModel):
    """Todas las velas de un mismo cierre, para todos los pares del universo.

    Tolera pares faltantes (huecos de datos): el `Engine` simplemente no evalúa ese par en
    este cierre. Las velas se iteran en orden alfabético de par para que el procesamiento
    sea determinístico (ADR-0002).
    """

    model_config = ConfigDict(frozen=True)

    timeframe: Timeframe
    open_time: int = Field(ge=0)
    candles: Mapping[Pair, Candle]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        self.timeframe.check_aligned(self.open_time)
        if not self.candles:
            msg = "un Bar necesita al menos una vela"
            raise ValueError(msg)
        for pair, candle in self.candles.items():
            if candle.pair != pair:
                msg = f"clave {pair} no coincide con la vela de {candle.pair}"
                raise ValueError(msg)
            if candle.timeframe is not self.timeframe:
                msg = f"vela de {pair} en {candle.timeframe}, Bar en {self.timeframe}"
                raise ValueError(msg)
            if candle.open_time != self.open_time:
                msg = f"vela de {pair} abre en {candle.open_time}, Bar en {self.open_time}"
                raise ValueError(msg)
        return self

    @classmethod
    def from_candles(cls, candles: list[Candle] | tuple[Candle, ...]) -> Bar:
        """Construye un Bar a partir de velas del mismo cierre."""
        if not candles:
            msg = "un Bar necesita al menos una vela"
            raise ValueError(msg)
        first = candles[0]
        by_pair = {c.pair: c for c in candles}
        if len(by_pair) != len(candles):
            duplicated = sorted(
                {c.pair.symbol for c in candles if sum(1 for o in candles if o.pair == c.pair) > 1}
            )
            msg = f"velas duplicadas para el mismo cierre: {', '.join(duplicated)}"
            raise ValueError(msg)
        return cls(timeframe=first.timeframe, open_time=first.open_time, candles=by_pair)

    @property
    def close_time(self) -> int:
        return self.timeframe.close_time(self.open_time)

    @property
    def pairs(self) -> tuple[Pair, ...]:
        """Pares presentes, en orden alfabético."""
        return tuple(sorted(self.candles))

    def get(self, pair: Pair) -> Candle | None:
        return self.candles.get(pair)

    def iter_candles(self) -> Iterator[Candle]:
        """Velas en orden alfabético de par."""
        for pair in self.pairs:
            yield self.candles[pair]

    def __len__(self) -> int:
        return len(self.candles)
