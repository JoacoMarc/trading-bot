"""Comandos del bot (ADR-0012): texto plano a partir del estado de la sesión.

Funciones puras sobre un `CommandBackend` (lo implementa `PaperSession`), así se prueban sin
Telegram. Los comandos de control usan los mismos archivos que la CLI (`tradingbot stop|resume`:
`logs/STOP`, `logs/RESUME`) y el `Engine` los consume en el próximo cierre; `/stop flatten` exige
confirmar con `si` dentro de `confirm_window_s`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from tradingbot.domain.money import ZERO
from tradingbot.domain.orders import Fill
from tradingbot.domain.positions import PortfolioSnapshot, Trade
from tradingbot.persistence.store import EventRecord
from tradingbot.risk.protections import FileKillSwitch

MS_PER_DAY = 86_400_000
CONFIRM_WORDS = frozenset({"si", "sí", "yes"})
DEFAULT_TRADES = 10

HELP = """Comandos:
/status - resumen del bot
/balance - cash, equity, dust
/positions - posiciones abiertas
/trades [n] - ultimos n trades cerrados (default 10)
/profit - PnL realizado y no realizado
/daily - resumen de las ultimas 24 h
/health - heartbeat, tareas, errores
/pause - sin entradas nuevas (kill switch)
/resume [breaker] - retira el kill switch; con breaker reanuda el circuit breaker
/stop [flatten] - como /pause; con flatten vende todo (pide confirmacion)
/help - esta ayuda"""


class CommandBackend(Protocol):
    """Lo que los comandos leen de la sesión (y el interruptor que escriben)."""

    def status_payload(self, phase: str = "corriendo") -> dict[str, Any]: ...

    def trades(self) -> Sequence[Trade]: ...

    def fills(self) -> Sequence[Fill]: ...

    def events(self) -> Sequence[EventRecord]: ...

    def snapshots(self) -> Sequence[PortfolioSnapshot]: ...

    def now_ms(self) -> int: ...

    def stale_for_ms(self) -> int: ...

    @property
    def kill_switch(self) -> FileKillSwitch: ...

    @property
    def initial_cash(self) -> Decimal: ...


# ------------------------------------------------------------------ formato


def money(value: object) -> str:
    return f"{Decimal(str(value)):,.2f}"


def pct(fraction: Decimal) -> str:
    return f"{fraction * 100:+.2f} %"


def dd_pct(fraction: Decimal) -> str:
    """Drawdown sin signo: `1.91 %` (un DD no es un retorno)."""
    return f"{fraction * 100:.2f} %"


def _dec(value: object, default: Decimal = ZERO) -> Decimal:
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except ArithmeticError:
        return default


def active_protections(protections: Mapping[str, Any]) -> list[str]:
    """Nombres legibles de las protecciones activas (`Protections.status()`)."""
    active: list[str] = []
    if protections.get("drawdown_halted") == "True":
        active.append(f"circuit breaker (DD {dd_pct(_dec(protections.get('drawdown')))})")
    if protections.get("daily_halted") == "True":
        active.append("perdida diaria")
    if protections.get("losses_paused") == "True":
        active.append("pausa por perdidas seguidas")
    kill = str(protections.get("kill_switch", "False"))
    if kill == "flatten":
        active.append("kill switch (flatten)")
    elif kill == "True":
        active.append("kill switch")
    cooldown = str(protections.get("pairs_in_cooldown", ""))
    if cooldown:
        active.append(f"cooldown {cooldown}")
    market = str(protections.get("market_filter", "off"))
    if market not in ("off", "habilitado", "solo benchmark"):
        active.append(f"filtro de mercado {market}")
    return active


class CommandService:
    def __init__(
        self,
        backend: CommandBackend,
        *,
        timezone: str = "UTC",
        confirm_window_s: int = 60,
    ) -> None:
        self._b = backend
        self._tz = ZoneInfo(timezone)
        self._tz_name = timezone
        self._window_ms = confirm_window_s * 1000
        self._flatten_until: int | None = None

    # ------------------------------------------------------------- despacho

    def handle(self, text: str) -> str:
        parts = text.strip().split()
        if not parts:
            return HELP
        head, *args = parts
        head = head.lower().split("@", 1)[0]  # `/status@mi_bot` en grupos
        if head in CONFIRM_WORDS:
            return self.confirm()
        if not head.startswith("/"):
            return "no entendi; /help muestra los comandos"
        name = head[1:]
        if name == "status":
            return self.status()
        if name == "balance":
            return self.balance()
        if name == "positions":
            return self.positions()
        if name == "trades":
            last = int(args[0]) if args and args[0].isdigit() and int(args[0]) > 0 else None
            return self.trades(last or DEFAULT_TRADES)
        if name == "profit":
            return self.profit()
        if name == "daily":
            return self.daily()
        if name == "health":
            return self.health()
        if name == "pause":
            return self.pause()
        if name == "resume":
            return self.resume(breaker=bool(args) and args[0].lower() == "breaker")
        if name == "stop":
            return self.stop(flatten=bool(args) and args[0].lower() == "flatten")
        if name in ("help", "start"):
            return HELP
        return f"comando desconocido: {head}\n{HELP}"

    # ------------------------------------------------------------- lectura

    def _local(self, ts_ms: object) -> str:
        try:
            ts = int(str(ts_ms))
        except (TypeError, ValueError):
            return "-"
        return (
            datetime.fromtimestamp(ts / 1000, tz=UTC).astimezone(self._tz).strftime("%d/%m %H:%M")
        )

    def _position_lines(self, payload: Mapping[str, Any]) -> list[str]:
        lines: list[str] = []
        for p in payload.get("positions") or []:
            qty = _dec(p.get("qty"))
            entry = _dec(p.get("entry_price"))
            mark = p.get("mark")
            pnl = p.get("unrealized_pnl")
            stop = _dec(p.get("stop_price"))
            line = f"{p.get('pair')}: {qty} @ {money(entry)}"
            if mark is not None:
                line += f", mark {money(mark)}"
            if pnl is not None and entry > ZERO and qty > ZERO:
                line += f", pnl {money(pnl)} ({pct(_dec(pnl) / (entry * qty))})"
            line += f", stop {money(stop)}"
            if entry > ZERO:
                line += f" ({pct((stop - entry) / entry)})"
            if not p.get("stop_published", True):
                line += " SIN STOP PUBLICADO"
            lines.append(line)
        return lines

    def status(self) -> str:
        s = self._b.status_payload()
        equity = _dec(s.get("equity"))
        initial = self._b.initial_cash
        ret = (
            ""
            if initial <= ZERO
            else f" ({pct((equity - initial) / initial)} desde {money(initial)})"
        )
        tf_ms = int(s.get("timeframe_ms") or 0)
        last = s.get("last_bar_open_time")
        next_close = "-" if last is None or not tf_ms else self._local(int(last) + 2 * tf_ms)
        lines = [
            f"{s.get('mode', '-')} {s.get('strategy', '-')} {s.get('timeframe', '-')} "
            f"{', '.join(s.get('pairs') or [])} - {s.get('phase', '-')}",
            f"equity {money(equity)}{ret} - cash {money(_dec(s.get('cash')))}",
        ]
        positions = self._position_lines(s)
        lines.extend(positions or ["sin posiciones"])
        pending = s.get("pending_orders") or []
        if pending:
            lines.append(f"ordenes pendientes: {', '.join(pending)}")
        lines.append(
            f"ultima vela {self._local(last)} - proximo cierre {next_close} ({self._tz_name})"
        )
        active = active_protections(s.get("protections") or {})
        lines.append(f"protecciones: {', '.join(active) if active else 'ninguna activa'}")
        return "\n".join(lines)

    def balance(self) -> str:
        s = self._b.status_payload()
        cash = _dec(s.get("cash"))
        equity = _dec(s.get("equity"))
        invested = ZERO
        unrealized = ZERO
        for p in s.get("positions") or []:
            if p.get("mark") is not None:
                invested += _dec(p.get("qty")) * _dec(p.get("mark"))
            unrealized += _dec(p.get("unrealized_pnl"))
        lines = [
            f"cash {money(cash)}",
            f"invertido {money(invested)} (pnl no realizado {money(unrealized)})",
            f"equity {money(equity)}",
        ]
        dust = s.get("dust") or {}
        if dust:
            lines.append("dust: " + ", ".join(f"{k} {v}" for k, v in dust.items()))
        return "\n".join(lines)

    def positions(self) -> str:
        lines = self._position_lines(self._b.status_payload())
        return "\n".join(lines) if lines else "sin posiciones abiertas"

    def trades(self, last: int = DEFAULT_TRADES) -> str:
        rows = list(self._b.trades())[-last:]
        if not rows:
            return "sin trades cerrados"
        lines = [
            f"{self._local(t.entry_time)} -> {self._local(t.exit_time)} {t.pair.symbol} "
            f"{t.exit_reason.value} pnl {money(t.pnl)} ({pct(t.pnl_pct)})"
            for t in rows
        ]
        total = sum((t.pnl for t in rows), ZERO)
        lines.append(f"{len(rows)} trades, pnl {money(total)}")
        return "\n".join(lines)

    def profit(self) -> str:
        s = self._b.status_payload()
        trades = list(self._b.trades())
        realized = sum((t.pnl for t in trades), ZERO)
        unrealized = sum((_dec(p.get("unrealized_pnl")) for p in s.get("positions") or []), ZERO)
        fees = sum((f.fee_in_quote() for f in self._b.fills()), ZERO)
        equity = _dec(s.get("equity"))
        initial = self._b.initial_cash
        lines = [
            f"equity {money(equity)} vs inicial {money(initial)}: "
            f"{money(equity - initial)}"
            + ("" if initial <= ZERO else f" ({pct((equity - initial) / initial)})"),
            f"realizado {money(realized)} en {len(trades)} trades - "
            f"no realizado {money(unrealized)}",
            f"fees pagadas {money(fees)}",
        ]
        if trades:
            wins = [t for t in trades if t.is_winner]
            gross_win = sum((t.pnl for t in wins), ZERO)
            gross_loss = -sum((t.pnl for t in trades if not t.is_winner), ZERO)
            pf = "inf" if gross_loss == ZERO else f"{gross_win / gross_loss:.2f}"
            lines.append(f"win rate {len(wins) / len(trades) * 100:.0f} % - profit factor {pf}")
        return "\n".join(lines)

    def daily(self) -> str:
        """Resumen de las últimas 24 h (lo manda el resumen diario y `/daily`)."""
        s = self._b.status_payload()
        now = self._b.now_ms()
        since = now - MS_PER_DAY
        equity = _dec(s.get("equity"))
        base, base_label = self._equity_at(since)
        protections = s.get("protections") or {}
        trades = [t for t in self._b.trades() if t.exit_time >= since]
        fills = [f for f in self._b.fills() if f.fill_ts >= since]
        events = [e for e in self._b.events() if e.ts >= since]
        lines = [f"resumen 24 h ({self._local(now)} {self._tz_name})"]
        if base is None:
            lines.append(f"equity {money(equity)}")
        else:
            change = equity - base
            lines.append(
                f"equity {money(equity)}: {money(change)}"
                + ("" if base <= ZERO else f" ({pct(change / base)})")
                + f" {base_label}"
            )
        peak = _dec(protections.get("peak_equity"))
        if peak > ZERO:
            lines.append(
                f"drawdown {dd_pct(_dec(protections.get('drawdown')))} desde el pico {money(peak)}"
            )
        positions = self._position_lines(s)
        lines.extend(positions or ["sin posiciones"])
        if trades:
            lines.append(
                f"{len(trades)} trades cerrados, pnl {money(sum((t.pnl for t in trades), ZERO))}"
            )
        else:
            lines.append("sin trades cerrados")
        if fills:
            fees = sum((f.fee_in_quote() for f in fills), ZERO)
            avg = sum((f.shortfall_bps for f in fills), ZERO) / len(fills)
            lines.append(f"{len(fills)} fills, fees {money(fees)}, shortfall medio {avg:+.1f} bps")
        kinds = Counter(e.kind for e in events)
        if kinds:
            lines.append("eventos: " + ", ".join(f"{k} x{n}" for k, n in sorted(kinds.items())))
        active = active_protections(protections)
        if active:
            lines.append("protecciones: " + ", ".join(active))
        errors = _dec((s.get("stats") or {}).get("price_errors", 0))
        if errors > ZERO:
            lines.append(f"errores de precio acumulados: {errors}")
        return "\n".join(lines)

    def _equity_at(self, ts: int) -> tuple[Decimal | None, str]:
        """Equity base del resumen y su etiqueta.

        El último snapshot en o antes de `ts` ("en 24 h"); si todos son posteriores (arranque
        reciente), el primero, y la etiqueta lo dice en vez de fingir 24 h.
        """
        snapshots = list(self._b.snapshots())
        if not snapshots:
            return None, ""
        before = [snap for snap in snapshots if snap.ts <= ts]
        if before:
            return before[-1].equity, "en 24 h"
        first = snapshots[0]
        return first.equity, f"desde el primer cierre ({self._local(first.ts)})"

    def health(self) -> str:
        s = self._b.status_payload()
        stats = s.get("stats") or {}
        notify = s.get("notify") or {}
        age_s = self._b.stale_for_ms() // 1000
        tf_ms = int(s.get("timeframe_ms") or 0)
        lines = [
            f"fase {s.get('phase', '-')} - version {s.get('bot_version', '-')}"
            f"{' - reanudado desde la DB' if s.get('restored_from_db') else ''}",
            f"ultimo ciclo hace {age_s // 60} min (timeframe {tf_ms // 60_000} min)",
            f"velas {stats.get('bars', 0)}, fills {stats.get('fills', 0)}, "
            f"ticks del watcher {stats.get('watcher_ticks', 0)}, "
            f"errores de precio {stats.get('price_errors', 0)}",
        ]
        stuck = stats.get("stuck_pairs") or []
        if stuck:
            lines.append(f"salidas trabadas: {', '.join(stuck)}")
        pending = s.get("pending_orders") or []
        if pending:
            lines.append(f"ordenes pendientes: {', '.join(pending)}")
        if notify:
            lines.append(
                f"avisos ({notify.get('backend', '-')}): enviados {notify.get('sent', 0)}, "
                f"errores {notify.get('errors', 0)}, descartados {notify.get('dropped', 0)}"
            )
        counts = (s.get("db") or {}).get("counts") or {}
        if counts:
            lines.append("db: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        return "\n".join(lines)

    # ------------------------------------------------------------- control

    def pause(self) -> str:
        self._b.kill_switch.activate(flatten=False)
        return (
            "kill switch activo: sin entradas nuevas desde el proximo cierre; la posicion abierta "
            "sigue con su stop. /resume lo retira."
        )

    def stop(self, *, flatten: bool = False) -> str:
        if not flatten:
            return self.pause()
        self._flatten_until = self._b.now_ms() + self._window_ms
        return (
            "ATENCION: /stop flatten vende TODAS las posiciones a mercado en el proximo cierre. "
            f"Responde `si` en {self._window_ms // 1000} s para confirmar."
        )

    def confirm(self) -> str:
        if self._flatten_until is None:
            return "nada que confirmar"
        if self._b.now_ms() > self._flatten_until:
            self._flatten_until = None
            return "la confirmacion vencio; repeti /stop flatten"
        self._flatten_until = None
        self._b.kill_switch.activate(flatten=True)
        return (
            "flatten pedido: se vende todo a mercado en el proximo cierre y no hay entradas "
            "nuevas. /resume lo retira."
        )

    def resume(self, *, breaker: bool = False) -> str:
        switch = self._b.kill_switch
        lines: list[str] = []
        if breaker:
            switch.request_resume()
            lines.append("reanudacion del circuit breaker pedida (se aplica en el proximo cierre)")
        if switch.path.exists():
            switch.clear()
            lines.append("kill switch retirado: vuelven las entradas")
        else:
            lines.append("no habia kill switch activo")
        return "\n".join(lines)
