"""Comandos del bot (ADR-0012): respuestas en lenguaje llano a partir del estado de la sesión.

Funciones puras sobre un `CommandBackend` (lo implementa `PaperSession`), así se prueban sin
Telegram. Los comandos de control usan los mismos archivos que la CLI (`tradingbot stop|resume`:
`logs/STOP`, `logs/RESUME`) y el `Engine` los consume en la próxima revisión; `/stop flatten`
exige confirmar con `si` dentro de `confirm_window_s`. Los textos vienen de `notify/texts.py`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from tradingbot.domain.money import ZERO
from tradingbot.domain.orders import Fill
from tradingbot.domain.positions import PortfolioSnapshot, Trade
from tradingbot.notify.texts import (
    MS_PER_DAY,
    exit_reason_short,
    mode_label,
    money,
    pct,
    phase_label,
    plain_pct,
    qty_text,
    signed_money,
    tz_label,
    when,
)
from tradingbot.persistence.store import EventRecord
from tradingbot.risk.protections import FileKillSwitch

CONFIRM_WORDS = frozenset({"si", "sí", "yes"})
DEFAULT_TRADES = 10

HELP = """Comandos:
/status - cómo va el bot: cuánto tenés, qué compró, próxima revisión
/balance - efectivo, invertido y total
/positions - lo que tiene comprado y a qué precio vende solo
/trades [n] - últimas n operaciones cerradas (10 si no decís)
/profit - cuánto ganó o perdió desde el inicio
/daily - resumen de las últimas 24 h
/health - estado técnico: última revisión, errores, avisos
/pause - frena las compras nuevas; lo comprado sigue protegido
/resume - vuelve a permitir compras; "/resume breaker" además levanta la pausa por caída fuerte
/stop - igual que /pause; "/stop flatten" vende todo (te pide confirmar con si)
/help - esta ayuda

Glosario: USDT = dólar digital (1 USDT ≈ 1 USD). Total = efectivo + lo comprado a precio de hoy.
Límite de pérdida = precio al que vende solo para no perder más. Revisión = cada cierre de vela
(cada 4 h) el bot mira los precios y decide."""

ACTIVE_PROTECTION_TEXT = {
    "drawdown_halted": "pausa por caída fuerte",
    "daily_halted": "pausa por pérdida diaria",
    "losses_paused": "pausa por pérdidas seguidas",
}


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


def _dec(value: object, default: Decimal = ZERO) -> Decimal:
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except ArithmeticError:
        return default


def _split(symbol: object) -> tuple[str, str]:
    base, _, quote = str(symbol).partition("/")
    return base, quote or "USDT"


def active_protections(protections: Mapping[str, Any]) -> list[str]:
    """Protecciones activas en llano (`Protections.status()`)."""
    active: list[str] = []
    if protections.get("drawdown_halted") == "True":
        active.append(
            f"pausa por caída fuerte (cayó {plain_pct(_dec(protections.get('drawdown')))} "
            "desde el mejor momento)"
        )
    if protections.get("daily_halted") == "True":
        active.append(ACTIVE_PROTECTION_TEXT["daily_halted"])
    if protections.get("losses_paused") == "True":
        active.append(ACTIVE_PROTECTION_TEXT["losses_paused"])
    kill = str(protections.get("kill_switch", "False"))
    if kill == "flatten":
        active.append("pedido de cerrar todo (vende en la próxima revisión)")
    elif kill == "True":
        active.append("pausa manual (no compra)")
    cooldown = str(protections.get("pairs_in_cooldown", ""))
    if cooldown:
        active.append(f"espera tras una pérdida en {cooldown}")
    market = str(protections.get("market_filter", "off"))
    if market not in ("off", "habilitado", "solo benchmark"):
        active.append(f"mercado bajista ({market})")
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
        self._tz_label = tz_label(timezone)
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
            return "No entendí. Mandá /help para ver los comandos."
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
        return f"No conozco el comando {head}.\n{HELP}"

    # ------------------------------------------------------------- lectura

    def _when(self, ts_ms: object) -> str:
        return when(ts_ms, self._tz)

    def _position_lines(self, payload: Mapping[str, Any]) -> list[str]:
        lines: list[str] = []
        for p in payload.get("positions") or []:
            base, quote = _split(p.get("pair"))
            qty = _dec(p.get("qty"))
            entry = _dec(p.get("entry_price"))
            mark = p.get("mark")
            pnl = p.get("unrealized_pnl")
            stop = _dec(p.get("stop_price"))
            line = f"Comprado: {qty_text(qty)} {base} a {money(entry)} {quote}"
            if mark is not None:
                line += f"; hoy vale {money(mark)}"
            if pnl is not None and entry > ZERO and qty > ZERO:
                line += f": vas {signed_money(pnl)} {quote} ({pct(_dec(pnl) / (entry * qty))})"
            line += f". Si baja a {money(stop)}"
            if entry > ZERO:
                line += f" ({pct((stop - entry) / entry)})"
            line += " vende solo."
            if not p.get("stop_published", True):
                line += " ATENCION: el límite de pérdida no está cargado en el exchange."
            lines.append(line)
        return lines

    def status(self) -> str:
        s = self._b.status_payload()
        _base, quote = _split((s.get("pairs") or ["BTC/USDT"])[0])
        equity = _dec(s.get("equity"))
        initial = self._b.initial_cash
        since = (
            ""
            if initial <= ZERO
            else f" (empezaste con {money(initial)}: {pct((equity - initial) / initial)})"
        )
        tf_ms = int(s.get("timeframe_ms") or 0)
        last = s.get("last_bar_open_time")
        next_close = "-" if last is None or not tf_ms else self._when(int(last) + 2 * tf_ms)
        mode = mode_label(s.get("mode", "-"))
        lines = [
            f"{mode[:1].upper()}{mode[1:]} - {phase_label(s.get('phase', '-'))}",
            f"Tenés en total {money(equity)} {quote}{since}",
            f"Efectivo disponible: {money(_dec(s.get('cash')))} {quote}",
        ]
        positions = self._position_lines(s)
        lines.extend(positions or ["No tiene nada comprado: todo está en efectivo."])
        pending = s.get("pending_orders") or []
        if pending:
            lines.append(f"Órdenes esperando ejecutarse: {len(pending)}")
        lines.append(
            f"Última revisión de precios: {self._when(last)} - próxima: {next_close} "
            f"({self._tz_label})"
        )
        active = active_protections(s.get("protections") or {})
        lines.append(f"Protecciones: {', '.join(active) if active else 'ninguna activa'}")
        return "\n".join(lines)

    def balance(self) -> str:
        s = self._b.status_payload()
        _base, quote = _split((s.get("pairs") or ["BTC/USDT"])[0])
        cash = _dec(s.get("cash"))
        equity = _dec(s.get("equity"))
        invested = ZERO
        unrealized = ZERO
        for p in s.get("positions") or []:
            if p.get("mark") is not None:
                invested += _dec(p.get("qty")) * _dec(p.get("mark"))
            unrealized += _dec(p.get("unrealized_pnl"))
        lines = [
            f"Efectivo disponible: {money(cash)} {quote}",
            f"Invertido (a precio de hoy): {money(invested)} {quote}, "
            f"vas {signed_money(unrealized)}",
            f"Total: {money(equity)} {quote}",
        ]
        dust = s.get("dust") or {}
        if dust:
            lines.append(
                "Restos que no se pueden vender (muy chicos): "
                + ", ".join(f"{qty_text(v)} {k}" for k, v in dust.items())
            )
        return "\n".join(lines)

    def positions(self) -> str:
        lines = self._position_lines(self._b.status_payload())
        return "\n".join(lines) if lines else "No tiene nada comprado: todo está en efectivo."

    def trades(self, last: int = DEFAULT_TRADES) -> str:
        rows = list(self._b.trades())[-last:]
        if not rows:
            return "Todavía no cerró ninguna operación (compra y venta completas)."
        lines: list[str] = []
        for t in rows:
            verb = "ganó" if t.pnl >= ZERO else "perdió"
            lines.append(
                f"{self._when(t.entry_time)} -> {self._when(t.exit_time)} {t.pair.base}: {verb} "
                f"{money(abs(t.pnl))} {t.pair.quote} ({pct(t.pnl_pct)}) "
                f"{exit_reason_short(t.exit_reason)}"
            )
        total = sum((t.pnl for t in rows), ZERO)
        quote = rows[0].pair.quote
        lines.append(f"{len(rows)} operaciones cerradas: {signed_money(total)} {quote} en total")
        return "\n".join(lines)

    def profit(self) -> str:
        s = self._b.status_payload()
        _base, quote = _split((s.get("pairs") or ["BTC/USDT"])[0])
        trades = list(self._b.trades())
        realized = sum((t.pnl for t in trades), ZERO)
        unrealized = sum((_dec(p.get("unrealized_pnl")) for p in s.get("positions") or []), ZERO)
        fees = sum((f.fee_in_quote() for f in self._b.fills()), ZERO)
        equity = _dec(s.get("equity"))
        initial = self._b.initial_cash
        lines = [
            f"Tenés {money(equity)} {quote}; empezaste con {money(initial)}: "
            f"{signed_money(equity - initial)}"
            + ("" if initial <= ZERO else f" ({pct((equity - initial) / initial)})"),
            f"Operaciones ya cerradas: {signed_money(realized)} {quote} "
            f"en {len(trades)} operaciones",
            f"Lo que va lo comprado hoy (sin vender): {signed_money(unrealized)} {quote}",
            f"Comisiones pagadas: {money(fees)} {quote}",
        ]
        if trades:
            wins = [t for t in trades if t.is_winner]
            gross_win = sum((t.pnl for t in wins), ZERO)
            gross_loss = -sum((t.pnl for t in trades if not t.is_winner), ZERO)
            ratio = (
                "sin pérdidas"
                if gross_loss == ZERO
                else f"por cada {quote} perdido ganó {gross_win / gross_loss:.2f}".replace(".", ",")
            )
            lines.append(
                f"Ganó {len(wins)} de {len(trades)} operaciones "
                f"({len(wins) / len(trades) * 100:.0f} %); {ratio}"
            )
        return "\n".join(lines)

    def daily(self) -> str:
        """Resumen de las últimas 24 h (lo manda el resumen diario y `/daily`)."""
        s = self._b.status_payload()
        _base, quote = _split((s.get("pairs") or ["BTC/USDT"])[0])
        now = self._b.now_ms()
        since = now - MS_PER_DAY
        equity = _dec(s.get("equity"))
        base, base_label = self._equity_at(since)
        protections = s.get("protections") or {}
        trades = [t for t in self._b.trades() if t.exit_time >= since]
        fills = [f for f in self._b.fills() if f.fill_ts >= since]
        events = [e for e in self._b.events() if e.ts >= since]
        lines = [f"Resumen de las últimas 24 h ({self._when(now)} {self._tz_label})"]
        if base is None:
            lines.append(f"Tenés {money(equity)} {quote}")
        else:
            change = equity - base
            lines.append(
                f"Tenés {money(equity)} {quote}: {signed_money(change)}"
                + ("" if base <= ZERO else f" ({pct(change / base)})")
                + f" {base_label}"
            )
        peak = _dec(protections.get("peak_equity"))
        if peak > ZERO:
            lines.append(
                f"Caída desde el mejor momento ({money(peak)}): "
                f"{plain_pct(_dec(protections.get('drawdown')))}"
            )
        positions = self._position_lines(s)
        lines.extend(positions or ["No tiene nada comprado: todo está en efectivo."])
        if trades:
            total = sum((t.pnl for t in trades), ZERO)
            lines.append(
                f"Operaciones cerradas en el día: {len(trades)}, "
                f"resultado {signed_money(total)} {quote}"
            )
        else:
            lines.append("Operaciones cerradas en el día: ninguna")
        if fills:
            fees = sum((f.fee_in_quote() for f in fills), ZERO)
            avg_bps = sum((f.shortfall_bps for f in fills), ZERO) / len(fills)
            worse = "peor" if avg_bps >= ZERO else "mejor"
            lines.append(
                f"Compras/ventas ejecutadas: {len(fills)}, comisiones {money(fees)} {quote}, "
                f"precio conseguido {plain_pct(abs(avg_bps) / 10_000)} {worse} que el de "
                "referencia"
            )
        kinds = Counter(e.kind for e in events)
        if kinds:
            lines.append(
                "Avisos técnicos: " + ", ".join(f"{k} x{n}" for k, n in sorted(kinds.items()))
            )
        active = active_protections(protections)
        if active:
            lines.append("Protecciones activas: " + ", ".join(active))
        errors = _dec((s.get("stats") or {}).get("price_errors", 0))
        if errors > ZERO:
            lines.append(f"Errores leyendo precios (acumulados): {errors}")
        return "\n".join(lines)

    def _equity_at(self, ts: int) -> tuple[Decimal | None, str]:
        """Total base del resumen y su etiqueta.

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
        return first.equity, f"desde la primera revisión ({self._when(first.ts)})"

    def health(self) -> str:
        s = self._b.status_payload()
        stats = s.get("stats") or {}
        notify = s.get("notify") or {}
        age_s = self._b.stale_for_ms() // 1000
        tf_ms = int(s.get("timeframe_ms") or 0)
        lines = [
            f"Estado: {phase_label(s.get('phase', '-'))} - versión {s.get('bot_version', '-')}"
            f"{' - retomó lo guardado al arrancar' if s.get('restored_from_db') else ''}",
            f"Última revisión de precios hace {age_s // 60} min "
            f"(revisa cada {tf_ms // 60_000} min)",
            f"Revisiones: {stats.get('bars', 0)}; compras/ventas: {stats.get('fills', 0)}; "
            f"controles del límite de pérdida: {stats.get('watcher_ticks', 0)}; errores leyendo "
            f"precios: {stats.get('price_errors', 0)}",
        ]
        stuck = stats.get("stuck_pairs") or []
        if stuck:
            lines.append(
                f"ATENCION: no puede vender {', '.join(stuck)} (Binance no acepta la orden)"
            )
        pending = s.get("pending_orders") or []
        if pending:
            lines.append(f"Órdenes esperando ejecutarse: {len(pending)}")
        if notify:
            lines.append(
                f"Avisos por {notify.get('backend', '-')}: enviados {notify.get('sent', 0)}, con "
                f"error {notify.get('errors', 0)}, descartados {notify.get('dropped', 0)}"
            )
        counts = (s.get("db") or {}).get("counts") or {}
        if counts:
            lines.append(
                "Base de datos: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
            )
        return "\n".join(lines)

    # ------------------------------------------------------------- control

    def pause(self) -> str:
        self._b.kill_switch.activate(flatten=False)
        return (
            "Pausa activada: desde la próxima revisión no compra más. Lo que ya tiene comprado "
            "sigue con su límite de pérdida. /resume la levanta."
        )

    def stop(self, *, flatten: bool = False) -> str:
        if not flatten:
            return self.pause()
        self._flatten_until = self._b.now_ms() + self._window_ms
        return (
            "ATENCION: vas a vender TODO lo comprado al precio de mercado en la próxima revisión. "
            f"Respondé `si` en {self._window_ms // 1000} s para confirmar."
        )

    def confirm(self) -> str:
        if self._flatten_until is None:
            return "No hay nada que confirmar."
        if self._b.now_ms() > self._flatten_until:
            self._flatten_until = None
            return "Se venció el tiempo para confirmar; repetí /stop flatten si querés cerrar todo."
        self._flatten_until = None
        self._b.kill_switch.activate(flatten=True)
        return (
            "Confirmado: en la próxima revisión vende todo al precio de mercado y no compra más. "
            "/resume cancela el pedido si todavía no vendió."
        )

    def resume(self, *, breaker: bool = False) -> str:
        switch = self._b.kill_switch
        lines: list[str] = []
        if breaker:
            switch.request_resume()
            lines.append(
                "Pedido levantar la pausa por caída fuerte (se aplica en la próxima revisión)."
            )
        if switch.path.exists():
            switch.clear()
            lines.append("Pausa levantada: el bot vuelve a poder comprar.")
        else:
            lines.append("No había ninguna pausa manual activa.")
        return "\n".join(lines)
