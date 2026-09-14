"""Protecciones dinámicas del `RiskManager` (ADR-0007).

Solo bloquean **entradas**; ninguna toca una salida (regla dura 7). El estado vive en memoria
por proceso: en backtest arranca vacío con la corrida; en paper/live se reconstruye en la Fase 7.

- Pérdida diaria (día UTC): equity contra el último snapshot del día anterior. Al alcanzar el
  límite no hay entradas hasta el primer `Bar` del día siguiente.
- Circuit breaker por drawdown desde el pico de equity: sin entradas. En backtest reanuda solo
  cuando el DD vuelve por debajo de `drawdown_resume_pct` (mitad del umbral por defecto) o tras
  `drawdown_pause_days` días frenado, re-basando el pico en la equity actual (en cash el DD no se
  mueve: sin plazo el halt sería permanente). En paper/live solo reanuda `resume()`, que re-basa.
- Pausa tras N pérdidas seguidas: `pause_candles_after_losses` bars sin entradas.
- Cooldown por par tras una salida perdedora por stop o trailing: `cooldown_candles_after_stop`
  bars sin entradas en ese par, con la semántica de `bars_since_exit` (el bar del fill = 0).
- Kill switch: archivo `STOP` (o comando) = sin entradas; con `flatten` el Engine cierra todo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from tradingbot.config.models import RiskConfig
from tradingbot.domain.candle import Candle
from tradingbot.domain.enums import ExitReason
from tradingbot.domain.money import ZERO
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import Trade
from tradingbot.risk.market_filter import MarketFilter
from tradingbot.risk.sizing import ReasonCode

MS_PER_DAY = 86_400_000
PROTECTION_TRIGGERED = "protection_triggered"
PROTECTION_CLEARED = "protection_cleared"


@dataclass(frozen=True, slots=True)
class KillSwitchState:
    active: bool = False
    flatten: bool = False


class KillSwitch(Protocol):
    def poll(self) -> KillSwitchState: ...


class FileKillSwitch:
    """Archivo en disco: si existe, sin entradas; si contiene `flatten`, además se cierra todo.

    Fail-safe: si el archivo no se puede consultar (`OSError`), se responde `active=True` sin
    flatten. Ante la duda no se abren posiciones; las salidas nunca dependen de esto.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.last_error: str | None = None

    def poll(self) -> KillSwitchState:
        try:
            if not self.path.exists():
                self.last_error = None
                return KillSwitchState()
            text = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            self.last_error = str(exc)
            return KillSwitchState(active=True, flatten=False)
        self.last_error = None
        return KillSwitchState(active=True, flatten="flatten" in text.lower())

    def activate(self, *, flatten: bool = False) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("flatten\n" if flatten else "stop\n", encoding="utf-8")

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


@dataclass(frozen=True, slots=True)
class ProtectionEvent:
    ts: int
    kind: str
    reason: ReasonCode
    detail: str = ""
    pair: Pair | None = None


@dataclass(frozen=True, slots=True)
class Block:
    reason: ReasonCode
    detail: str = ""


def _pct(value: Decimal) -> str:
    return f"{value * 100:.2f} %"


class Protections:
    """Máquina de estado de las protecciones. El `Engine` la alimenta; `RiskManager` la consulta."""

    def __init__(self, config: RiskConfig, *, auto_resume: bool = True) -> None:
        self._cfg = config
        self._auto_resume = auto_resume
        self._bar = 0
        self._ts = 0
        self._day: int | None = None
        self._day_start_equity: Decimal | None = None
        self._last_equity: Decimal | None = None
        self._peak: Decimal | None = None
        self._daily_halt_day: int | None = None
        self._drawdown_halted = False
        self._halt_ts: int | None = None
        self._loss_streak = 0
        self._pause_until: int | None = None
        self._pair_cooldown_until: dict[Pair, int] = {}
        self._kill = KillSwitchState()
        self._events: list[ProtectionEvent] = []
        self.market_filter: MarketFilter | None = (
            MarketFilter(config.market_filter) if config.market_filter.enabled else None
        )

    # ------------------------------------------------------------- estado

    @property
    def drawdown_halted(self) -> bool:
        return self._drawdown_halted

    @property
    def daily_halted(self) -> bool:
        return self._daily_halt_day is not None and self._daily_halt_day == self._day

    @property
    def losses_paused(self) -> bool:
        return self._pause_until is not None and self._bar < self._pause_until

    @property
    def kill_switch(self) -> KillSwitchState:
        return self._kill

    @property
    def flatten_requested(self) -> bool:
        return self._kill.active and self._kill.flatten

    @property
    def peak_equity(self) -> Decimal | None:
        return self._peak

    @property
    def drawdown(self) -> Decimal:
        if self._peak is None or self._peak <= ZERO or self._last_equity is None:
            return ZERO
        return (self._peak - self._last_equity) / self._peak

    def status(self) -> dict[str, str]:
        """Resumen serializable (status.json, Fase 7)."""
        return {
            "drawdown_halted": str(self._drawdown_halted),
            "daily_halted": str(self.daily_halted),
            "losses_paused": str(self.losses_paused),
            "kill_switch": "flatten" if self.flatten_requested else str(self._kill.active),
            "peak_equity": "" if self._peak is None else str(self._peak),
            "drawdown": str(self.drawdown),
            "halted_since": "" if self._halt_ts is None else str(self._halt_ts),
            "day_start_equity": ""
            if self._day_start_equity is None
            else str(self._day_start_equity),
            "loss_streak": str(self._loss_streak),
            "pairs_in_cooldown": ", ".join(sorted(p.symbol for p in self._pair_cooldown_until)),
            "market_filter": (
                "off"
                if self.market_filter is None
                else self.market_filter.status()["market_filter"]
            ),
        }

    # ------------------------------------------------------------- alimentación

    def on_bar(self, bar_index: int, ts: int) -> None:
        """Primer paso de cada `Bar`: avanza el reloj y vence cooldowns y pausas."""
        self._bar = bar_index
        self._ts = ts
        for pair, until in list(self._pair_cooldown_until.items()):
            if bar_index >= until:
                del self._pair_cooldown_until[pair]
                self._emit(PROTECTION_CLEARED, ReasonCode.PAIR_COOLDOWN, "cooldown cumplido", pair)
        if self._pause_until is not None and bar_index >= self._pause_until:
            self._pause_until = None
            self._loss_streak = 0  # la pausa reinicia la racha
            self._emit(PROTECTION_CLEARED, ReasonCode.CONSECUTIVE_LOSSES, "pausa cumplida")

    def on_equity(self, ts: int, equity: Decimal) -> None:
        """Tras el mark-to-market: pérdida diaria y drawdown."""
        day = ts // MS_PER_DAY
        if self._day is None:
            self._day_start_equity = equity
        elif day != self._day:
            self._day_start_equity = self._last_equity if self._last_equity is not None else equity
            if self._daily_halt_day is not None and self._daily_halt_day < day:
                self._daily_halt_day = None
                self._emit(PROTECTION_CLEARED, ReasonCode.DAILY_LOSS_LIMIT, "nuevo día UTC")
        self._day = day
        self._ts = ts
        self._last_equity = equity
        self._check_daily_loss(equity)
        self._check_drawdown(equity)

    def on_trade_closed(self, trade: Trade) -> None:
        """Tras cada round trip: racha de pérdidas y cooldown por salida perdedora."""
        ts = trade.exit_time
        losing = trade.pnl < ZERO
        self._loss_streak = self._loss_streak + 1 if losing else 0
        limit = self._cfg.pause_after_consecutive_losses
        if limit is not None and self._loss_streak >= limit and not self.losses_paused:
            candles = self._cfg.pause_candles_after_losses
            self._pause_until = self._bar + candles
            self._loss_streak = 0
            self._emit(
                PROTECTION_TRIGGERED,
                ReasonCode.CONSECUTIVE_LOSSES,
                f"{limit} pérdidas seguidas; sin entradas por {candles} velas",
                ts=ts,
            )
        cooldown = self._cfg.cooldown_candles_after_stop
        stopped_out = losing and trade.exit_reason in {ExitReason.STOP, ExitReason.TRAILING}
        if cooldown > 0 and stopped_out:
            self._pair_cooldown_until[trade.pair] = self._bar + cooldown
            self._emit(
                PROTECTION_TRIGGERED,
                ReasonCode.PAIR_COOLDOWN,
                f"{trade.exit_reason.value} perdedor en {trade.pair.symbol}; "
                f"sin entradas en el par por {cooldown} velas",
                trade.pair,
                ts=ts,
            )

    def on_reference_candle(self, candle: Candle) -> None:
        """Vela cerrada del par de referencia del filtro de mercado (ADR-0009)."""
        if self.market_filter is None or not self.market_filter.on_candle(candle):
            return
        state = self.market_filter.state
        detail = "" if state is None else state.describe()
        if self.market_filter.enabled:
            self._emit(
                PROTECTION_CLEARED,
                ReasonCode.MARKET_FILTER,
                f"mercado habilitado: {detail}",
                ts=candle.close_time,
            )
        else:
            self._emit(
                PROTECTION_TRIGGERED,
                ReasonCode.MARKET_FILTER,
                f"mercado deshabilitado: {detail}",
                ts=candle.close_time,
            )

    def set_kill_switch(self, state: KillSwitchState) -> None:
        if state.active and not self._kill.active:
            detail = "flatten: cerrar todo" if state.flatten else "sin nuevas entradas"
            self._emit(PROTECTION_TRIGGERED, ReasonCode.KILL_SWITCH, detail)
        elif state.active and state.flatten and not self._kill.flatten:
            self._emit(PROTECTION_TRIGGERED, ReasonCode.KILL_SWITCH, "flatten: cerrar todo")
        elif state.active and not state.flatten and self._kill.flatten:
            self._emit(
                PROTECTION_CLEARED,
                ReasonCode.KILL_SWITCH,
                "flatten retirado; sigue sin nuevas entradas",
            )
        elif not state.active and self._kill.active:
            self._emit(PROTECTION_CLEARED, ReasonCode.KILL_SWITCH, "kill switch retirado")
        self._kill = state

    def resume(self) -> None:
        """Reanudación manual (paper/live): inmediata y re-basa el pico en la equity actual."""
        if self._drawdown_halted:
            self._clear_drawdown(
                "reanudación manual; pico re-basado en la equity actual", rebase=True
            )

    # ------------------------------------------------------------- consulta

    def global_block(self) -> Block | None:
        """Motivo por el que hoy no se abre ninguna posición, o `None`."""
        if self._kill.active:
            detail = "flatten" if self._kill.flatten else "sin nuevas entradas"
            return Block(ReasonCode.KILL_SWITCH, detail)
        if self._drawdown_halted:
            resume = self._cfg.effective_drawdown_resume_pct
            level = "" if resume is None else f"; reanuda bajo {_pct(resume)}"
            return Block(
                ReasonCode.DRAWDOWN_HALT,
                f"drawdown {_pct(self.drawdown)} desde el pico {self._peak}{level}",
            )
        if self.daily_halted:
            return Block(ReasonCode.DAILY_LOSS_LIMIT, "límite diario alcanzado (día UTC)")
        if self.losses_paused:
            return Block(ReasonCode.CONSECUTIVE_LOSSES, f"pausa hasta el bar {self._pause_until}")
        if self.market_filter is not None and not self.market_filter.enabled:
            state = self.market_filter.state
            return Block(
                ReasonCode.MARKET_FILTER,
                "" if state is None else f"{self.market_filter.pair.symbol}: {state.describe()}",
            )
        return None

    def pair_block(self, pair: Pair) -> Block | None:
        until = self._pair_cooldown_until.get(pair)
        if until is not None and self._bar < until:
            return Block(ReasonCode.PAIR_COOLDOWN, f"cooldown tras stop hasta el bar {until}")
        return None

    def pop_events(self) -> list[ProtectionEvent]:
        events, self._events = self._events, []
        return events

    # ------------------------------------------------------------- internos

    def _check_daily_loss(self, equity: Decimal) -> None:
        limit = self._cfg.daily_loss_limit_pct
        base = self._day_start_equity
        if limit is None or base is None or base <= ZERO or self.daily_halted:
            return
        loss = (base - equity) / base
        if loss >= limit:
            self._daily_halt_day = self._day
            self._emit(
                PROTECTION_TRIGGERED,
                ReasonCode.DAILY_LOSS_LIMIT,
                f"pérdida diaria {_pct(loss)} >= {_pct(limit)}; "
                "sin entradas hasta el próximo día UTC",
            )

    def _check_drawdown(self, equity: Decimal) -> None:
        self._peak = equity if self._peak is None else max(self._peak, equity)
        limit = self._cfg.max_drawdown_pct
        if limit is None or self._peak <= ZERO:
            return
        dd = (self._peak - equity) / self._peak
        if not self._drawdown_halted:
            if dd >= limit:
                self._drawdown_halted = True
                self._halt_ts = self._ts
                self._emit(
                    PROTECTION_TRIGGERED,
                    ReasonCode.DRAWDOWN_HALT,
                    f"drawdown {_pct(dd)} >= {_pct(limit)} desde el pico {self._peak}",
                )
            return
        if not self._auto_resume:
            return  # paper/live: solo `resume()` manual
        resume = self._cfg.effective_drawdown_resume_pct
        if resume is not None and dd <= resume:
            self._clear_drawdown(
                f"drawdown {_pct(dd)} <= {_pct(resume)}; reanudación automática", rebase=False
            )
            return
        days = self._cfg.drawdown_pause_days
        if days is None or self._halt_ts is None:
            return
        if self._ts - self._halt_ts >= days * MS_PER_DAY:
            self._clear_drawdown(
                f"{days} días frenado sin recuperar el DD; pico re-basado en {equity}",
                rebase=True,
            )

    def _clear_drawdown(self, detail: str, *, rebase: bool) -> None:
        self._drawdown_halted = False
        self._halt_ts = None
        if rebase and self._last_equity is not None:
            self._peak = self._last_equity
        self._emit(PROTECTION_CLEARED, ReasonCode.DRAWDOWN_HALT, detail)

    def _emit(
        self,
        kind: str,
        reason: ReasonCode,
        detail: str,
        pair: Pair | None = None,
        *,
        ts: int | None = None,
    ) -> None:
        self._events.append(
            ProtectionEvent(self._ts if ts is None else ts, kind, reason, detail, pair)
        )
