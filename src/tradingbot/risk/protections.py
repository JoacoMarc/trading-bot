"""Protecciones dinámicas del `RiskManager` (ADR-0007).

Solo bloquean **entradas**; ninguna toca una salida (regla dura 7). El estado vive en memoria
por proceso: en backtest arranca vacío con la corrida; en paper/live se reconstruye en la Fase 7.

- Pérdida diaria (día UTC): equity contra el último snapshot del día anterior. Al alcanzar el
  límite no hay entradas hasta el primer `Bar` del día siguiente.
- Circuit breaker por drawdown desde el pico de equity: sin entradas. Reanuda por **plazo**
  (`drawdown_pause_days`, re-basando el pico en la equity actual) en todos los modos: es una
  regla de reloj determinística y la misma que validó el walk-forward (en cash el DD no se mueve:
  sin plazo el halt sería permanente). Reanuda por **nivel** (`drawdown_resume_pct`) solo con
  `auto_resume` (backtest). `resume()` manual reanuda siempre y re-basa (archivo `RESUME`).
- Pausa tras N pérdidas seguidas: `pause_candles_after_losses` bars sin entradas.
- Cooldown por par tras una salida perdedora por stop o trailing: `cooldown_candles_after_stop`
  bars sin entradas en ese par, con la semántica de `bars_since_exit` (el bar del fill = 0).
- Kill switch: archivo `STOP` (o comando) = sin entradas; con `flatten` el Engine cierra todo.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

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

    def consume_resume(self) -> bool:
        """True si el operador pidió reanudar el circuit breaker (se consume una vez)."""
        ...


class FileKillSwitch:
    """Archivo en disco: si existe, sin entradas; si contiene `flatten`, además se cierra todo.

    Fail-safe: si el archivo no se puede consultar (`OSError`), se responde `active=True` sin
    flatten. Ante la duda no se abren posiciones; las salidas nunca dependen de esto.
    Al lado vive `RESUME` (`tradingbot resume --breaker`): el `Engine` lo consume una vez por
    `Bar` y reanuda el circuit breaker (ADR-0011).
    """

    def __init__(self, path: Path, resume_path: Path | None = None) -> None:
        self.path = path
        self.resume_path = resume_path if resume_path is not None else path.parent / "RESUME"
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

    def request_resume(self) -> None:
        """Pide la reanudación manual del circuit breaker (archivo `RESUME`)."""
        self.resume_path.parent.mkdir(parents=True, exist_ok=True)
        self.resume_path.write_text("resume\n", encoding="utf-8")

    def consume_resume(self) -> bool:
        """True (y borra el archivo) si hay una reanudación pedida. Fail-safe: False."""
        try:
            if not self.resume_path.exists():
                return False
            self.resume_path.unlink()
        except OSError as exc:
            self.last_error = str(exc)
            return False
        return True


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
        filter_cfg = config.market_filter
        self.market_filter: MarketFilter | None = (
            MarketFilter(filter_cfg)
            if filter_cfg.enabled and not filter_cfg.benchmark_only
            else None
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

    # ------------------------------------------------------------- persistencia (ADR-0011)

    def to_state(self) -> dict[str, Any]:
        """Todo lo que hace falta para reanudar tras un reinicio sin perder el pico ni los halts."""

        def dec(value: Decimal | None) -> str | None:
            return None if value is None else str(value)

        return {
            "bar": self._bar,
            "ts": self._ts,
            "day": self._day,
            "day_start_equity": dec(self._day_start_equity),
            "last_equity": dec(self._last_equity),
            "peak": dec(self._peak),
            "daily_halt_day": self._daily_halt_day,
            "drawdown_halted": self._drawdown_halted,
            "halt_ts": self._halt_ts,
            "loss_streak": self._loss_streak,
            "pause_until": self._pause_until,
            "pair_cooldown_until": {p.symbol: u for p, u in self._pair_cooldown_until.items()},
            "market_filter": None if self.market_filter is None else self.market_filter.to_state(),
        }

    def restore(self, state: Mapping[str, Any]) -> None:
        """Inverso de `to_state`. El kill switch no se persiste: se vuelve a leer del archivo."""

        def dec(value: Any) -> Decimal | None:
            return None if value is None else Decimal(str(value))

        def opt_int(value: Any) -> int | None:
            return None if value is None else int(value)

        self._bar = int(state.get("bar", 0))
        self._ts = int(state.get("ts", 0))
        self._day = opt_int(state.get("day"))
        self._day_start_equity = dec(state.get("day_start_equity"))
        self._last_equity = dec(state.get("last_equity"))
        self._peak = dec(state.get("peak"))
        self._daily_halt_day = opt_int(state.get("daily_halt_day"))
        self._drawdown_halted = bool(state.get("drawdown_halted", False))
        self._halt_ts = opt_int(state.get("halt_ts"))
        self._loss_streak = int(state.get("loss_streak", 0))
        self._pause_until = opt_int(state.get("pause_until"))
        self._pair_cooldown_until = {
            Pair.parse(symbol): int(until)
            for symbol, until in dict(state.get("pair_cooldown_until", {})).items()
        }
        filter_state = state.get("market_filter")
        if self.market_filter is not None and filter_state is not None:
            self.market_filter.restore(filter_state)

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

    def on_trade_closed(self, trade: Trade, *, bar_index: int | None = None) -> None:
        """Tras cada round trip: racha de pérdidas y cooldown por salida perdedora.

        `bar_index` es la vela a la que pertenece el fill (en paper el fill llega fuera del ciclo
        del `Bar`, ADR-0011); por defecto la vela actual.
        """
        bar = self._bar if bar_index is None else bar_index
        ts = trade.exit_time
        losing = trade.pnl < ZERO
        self._loss_streak = self._loss_streak + 1 if losing else 0
        limit = self._cfg.pause_after_consecutive_losses
        if limit is not None and self._loss_streak >= limit and not self.losses_paused:
            candles = self._cfg.pause_candles_after_losses
            self._pause_until = bar + candles
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
            self._pair_cooldown_until[trade.pair] = bar + cooldown
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
        resume = self._cfg.effective_drawdown_resume_pct
        if self._auto_resume and resume is not None and dd <= resume:
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
