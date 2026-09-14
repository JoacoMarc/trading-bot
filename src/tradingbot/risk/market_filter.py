"""Filtro de mercado a nivel cartera (ADR-0009).

Habilita las entradas solo si el cierre **diario** del par de referencia (BTC/USDT) está sobre su
EMA(200) diaria y su retorno a 30 días es positivo. Es una protección del `RiskManager`: solo
bloquea entradas; las salidas y los stops siguen su curso. Se alimenta con las velas cerradas del
timeframe del `Engine` y toma como cierre diario el último cierre de cada día UTC; el estado cambia
una vez por día, con días completos (sin lookahead). Mientras la EMA o el momentum no estén
definidos, el filtro se considera habilitado: sin información no se bloquea.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tradingbot.config.models import MarketFilterConfig
from tradingbot.domain.candle import Candle
from tradingbot.domain.pair import Pair

MS_PER_DAY = 86_400_000


@dataclass(frozen=True, slots=True)
class MarketState:
    """Estado al cierre de un día UTC completo."""

    day: int
    close: Decimal
    ema: float | None
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
        ema = "EMA indefinida" if self.ema is None else f"EMA {self.ema:.2f}"
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
        self._current_day: int | None = None
        self._current_close: Decimal | None = None
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
        """Días completos evaluados sin EMA o momentum definidos (el filtro quedó habilitado)."""
        return self._undefined_days

    def on_candle(self, candle: Candle) -> bool:
        """Vela cerrada del par de referencia. Devuelve True si cambió el estado (nuevo día)."""
        if candle.pair != self._pair:
            return False
        day = candle.close_time // MS_PER_DAY
        changed = False
        if self._current_day is None:
            self._current_day = day
        elif day != self._current_day:
            if self._current_close is not None:
                before = self.enabled
                self._commit_day(self._current_day, self._current_close)
                changed = self.enabled != before
            self._current_day = day
        self._current_close = candle.close
        return changed

    def _commit_day(self, day: int, close: Decimal) -> None:
        value = float(close)
        self._closes.append(value)
        n = self._cfg.ema_days
        if len(self._closes) == n:
            self._ema = sum(self._closes) / n  # semilla SMA, como en indicators/
        elif len(self._closes) > n and self._ema is not None:
            alpha = 2.0 / (n + 1)
            self._ema = alpha * value + (1.0 - alpha) * self._ema
        m = self._cfg.momentum_days
        momentum = self._closes[-1] / self._closes[-1 - m] - 1.0 if len(self._closes) > m else None
        self._state = MarketState(day, close, self._ema, momentum)
        if not self._state.defined:
            self._undefined_days += 1

    def status(self) -> dict[str, str]:
        state = self._state
        return {
            "market_filter": "habilitado" if self.enabled else "deshabilitado",
            "reference": self._pair.symbol,
            "detail": "" if state is None else state.describe(),
            "undefined_days": str(self._undefined_days),
        }
