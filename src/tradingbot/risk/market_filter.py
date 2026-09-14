"""Filtro de mercado a nivel cartera (ADR-0009).

Habilita las entradas solo si el cierre **diario** del par de referencia (BTC/USDT) está sobre su
media diaria (EMA sembrada con SMA, o SMA con `average: sma`) y su retorno a N días es positivo. Es
una protección del `RiskManager`: solo bloquea entradas; las salidas y los stops siguen su curso.
Se alimenta con las velas cerradas del timeframe del `Engine` y toma como cierre diario la vela
que cierra a las 23:59:59.999 UTC: el estado cambia al cerrar esa vela, con días completos y sin
lookahead, con la misma definición que usa `regime_bh` (ADR-0010). Un día sin esa vela no se
comete. Mientras la media o el momentum no estén definidos, el filtro se considera habilitado:
sin información no se bloquea.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from tradingbot.config.models import MarketFilterConfig
from tradingbot.domain.candle import Candle
from tradingbot.domain.pair import Pair

MS_PER_DAY = 86_400_000


def closes_utc_day(close_time: int) -> bool:
    """True si la vela es la última de su día UTC (cierra a las 23:59:59.999)."""
    return close_time % MS_PER_DAY == MS_PER_DAY - 1


@dataclass(frozen=True, slots=True)
class MarketState:
    """Estado al cierre de un día UTC completo."""

    day: int
    close: Decimal
    ema: float | None  # media diaria (EMA o SMA según la config)
    momentum: float | None  # retorno a `momentum_days`

    @property
    def defined(self) -> bool:
        return self.ema is not None and self.momentum is not None

    @property
    def enabled(self) -> bool:
        if self.ema is None or self.momentum is None:
            return True
        return float(self.close) > self.ema and self.momentum > 0

    def describe(self) -> str:
        ema = "media indefinida" if self.ema is None else f"media {self.ema:.2f}"
        mom = (
            "momentum indefinido"
            if self.momentum is None
            else f"momentum {self.momentum * 100:+.2f} %"
        )
        return f"cierre diario {self.close} vs {ema}, {mom}"


class MarketFilter:
    def __init__(self, config: MarketFilterConfig) -> None:
        self._cfg = config
        self._pair = config.reference_pair
        self._closes: list[float] = []
        self._ema: float | None = None
        self._state: MarketState | None = None
        self._undefined_days = 0

    @property
    def pair(self) -> Pair:
        return self._pair

    @property
    def state(self) -> MarketState | None:
        return self._state

    @property
    def enabled(self) -> bool:
        return True if self._state is None else self._state.enabled

    @property
    def undefined_days(self) -> int:
        """Días completos evaluados sin media o momentum definidos (el filtro quedó habilitado)."""
        return self._undefined_days

    def on_candle(self, candle: Candle) -> bool:
        """Vela cerrada del par de referencia. Devuelve True si cambió el estado (cerró un día)."""
        if candle.pair != self._pair or not closes_utc_day(candle.close_time):
            return False
        before = self.enabled
        self._commit_day(candle.close_time // MS_PER_DAY, candle.close)
        return self.enabled != before

    def _commit_day(self, day: int, close: Decimal) -> None:
        value = float(close)
        self._closes.append(value)
        n = self._cfg.ema_days
        if self._cfg.average == "sma":
            self._ema = sum(self._closes[-n:]) / n if len(self._closes) >= n else None
        elif len(self._closes) == n:
            self._ema = sum(self._closes) / n  # semilla SMA, como en indicators/
        elif len(self._closes) > n and self._ema is not None:
            alpha = 2.0 / (n + 1)
            self._ema = alpha * value + (1.0 - alpha) * self._ema
        m = self._cfg.momentum_days
        momentum = self._closes[-1] / self._closes[-1 - m] - 1.0 if len(self._closes) > m else None
        self._state = MarketState(day, close, self._ema, momentum)
        if not self._state.defined:
            self._undefined_days += 1

    def to_state(self) -> dict[str, Any]:
        """Estado serializable para reanudar sin re-sembrar (ADR-0011)."""
        s = self._state
        return {
            "closes": list(self._closes),
            "ema": self._ema,
            "undefined_days": self._undefined_days,
            "state": None
            if s is None
            else {"day": s.day, "close": str(s.close), "ema": s.ema, "momentum": s.momentum},
        }

    def restore(self, state: Mapping[str, Any]) -> None:
        self._closes = [float(v) for v in state.get("closes", [])]
        ema = state.get("ema")
        self._ema = None if ema is None else float(ema)
        self._undefined_days = int(state.get("undefined_days", 0))
        raw = state.get("state")
        self._state = (
            None
            if raw is None
            else MarketState(
                day=int(raw["day"]),
                close=Decimal(str(raw["close"])),
                ema=None if raw.get("ema") is None else float(raw["ema"]),
                momentum=None if raw.get("momentum") is None else float(raw["momentum"]),
            )
        )

    def status(self) -> dict[str, str]:
        state = self._state
        return {
            "market_filter": "habilitado" if self.enabled else "deshabilitado",
            "reference": self._pair.symbol,
            "detail": "" if state is None else state.describe(),
            "undefined_days": str(self._undefined_days),
        }
