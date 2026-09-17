"""Textos en lenguaje llano para los avisos y comandos (ADR-0012).

El destinatario no es un trader: nada de "equity", "pnl", "fill" ni "stop" a secas; cada número
lleva su explicación corta. Números en formato rioplatense (`9.817,04`), porcentajes con coma y
horas en la zona del usuario. Todo lo técnico (códigos de motivo, tipos de evento) se traduce acá
y en un solo lugar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from tradingbot.data.live_feed import FEED_LATE, FEED_MISSING_PAIR, FEED_REPLAY, FeedEvent
from tradingbot.domain.enums import ExitReason
from tradingbot.domain.money import ZERO
from tradingbot.domain.orders import Fill
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import Position, Trade
from tradingbot.persistence.store import EventRecord
from tradingbot.risk.protections import PROTECTION_CLEARED

MS_PER_HOUR = 3_600_000
MS_PER_DAY = 24 * MS_PER_HOUR

MODE_LABEL = {
    "paper": "modo prueba (dinero simulado)",
    "testnet": "modo prueba en el exchange (dinero simulado)",
    "live": "DINERO REAL",
    "backtest": "backtest",
}

PHASE_LABEL = {
    "arranque": "arrancando",
    "corriendo": "funcionando",
    "detenido": "detenido",
    "colgado": "sin responder",
}

EXIT_REASON_TEXT = {
    ExitReason.SIGNAL: "la estrategia dio señal de salir",
    ExitReason.STOP: "el precio tocó el límite de pérdida",
    ExitReason.TRAILING: "el precio cayó hasta el límite móvil que protege la ganancia",
    ExitReason.FLATTEN: "vos pediste cerrar todo",
    ExitReason.RISK: "una protección de riesgo pidió cerrar",
}

EXIT_REASON_SHORT = {
    ExitReason.SIGNAL: "por señal de salida",
    ExitReason.STOP: "por límite de pérdida",
    ExitReason.TRAILING: "por límite móvil",
    ExitReason.FLATTEN: "por cierre manual",
    ExitReason.RISK: "por protección de riesgo",
}

# Códigos de `ReasonCode` y del broker, en llano.
REASON_TEXT = {
    "kill_switch": "está en pausa (frenado a mano): no compra hasta que lo reanudes",
    "drawdown_halt": "la caída desde el mejor momento superó el límite: no compra por un tiempo",
    "daily_loss_limit": "hoy ya perdió más de lo permitido: no compra hasta mañana",
    "consecutive_losses": "varias pérdidas seguidas: pausa preventiva",
    "pair_cooldown": "acaba de perder con esta moneda: espera unas revisiones antes de volver",
    "market_filter": "el mercado en general está bajista: no compra",
    "replay": "revisión atrasada tras un reinicio: no compra con datos viejos",
    "max_positions": "ya tiene el máximo de compras abiertas",
    "exposure_limit": "ya tiene invertido el máximo permitido",
    "already_in_position": "ya tiene esta moneda comprada",
    "pending_order": "hay una orden de esta moneda esperando",
    "invalid_stop": "el límite de pérdida calculado no es válido",
    "no_cash": "no hay efectivo suficiente",
    "insufficient_funds": "no alcanzó el efectivo al momento de comprar",
    "min_qty": "la cantidad es menor al mínimo que acepta Binance",
    "min_notional": "el monto es menor al mínimo que acepta Binance",
}

TRIGGERED_TEXT = {
    "kill_switch": "Pausa activada: el bot no compra más hasta que lo reanudes. Lo comprado sigue "
    "protegido por su límite de pérdida.",
    "drawdown_halt": "Protección por caída fuerte: el total cayó demasiado desde su mejor momento "
    "y el bot deja de comprar por un tiempo.",
    "daily_loss_limit": "Protección por pérdida diaria: hoy ya se perdió más de lo permitido; no "
    "compra hasta mañana.",
    "consecutive_losses": "Protección por pérdidas seguidas: pausa preventiva en las compras.",
    "pair_cooldown": "Espera tras una pérdida: no vuelve a comprar esta moneda por unas "
    "revisiones.",
    "market_filter": "Mercado bajista: el bot no compra mientras dure.",
}

CLEARED_TEXT = {
    "kill_switch": "Pausa levantada: el bot vuelve a poder comprar.",
    "drawdown_halt": "Se levantó la protección por caída fuerte: el bot vuelve a poder comprar.",
    "daily_loss_limit": "Nuevo día: se levantó la protección por pérdida diaria.",
    "consecutive_losses": "Terminó la pausa por pérdidas seguidas.",
    "pair_cooldown": "Terminó la espera tras la pérdida: puede volver a comprar esta moneda.",
    "market_filter": "El mercado volvió a alcista: el bot puede comprar de nuevo.",
}

FEED_TEXT = {
    FEED_LATE: "Binance tardó en publicar los precios; el bot siguió con los que había",
    FEED_MISSING_PAIR: "faltaron los precios de una moneda en esta revisión; se saltea esta vez",
    FEED_REPLAY: "el bot estuvo apagado y ahora revisa las velas que se perdió (sin comprar)",
}


# ------------------------------------------------------------------ formato


def money(value: object) -> str:
    """`9817.04` -> `9.817,04` (miles con punto, decimales con coma)."""
    text = f"{Decimal(str(value)):,.2f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def signed_money(value: object) -> str:
    dec = Decimal(str(value))
    return ("+" if dec > ZERO else "") + money(dec)


def pct(fraction: Decimal) -> str:
    return f"{fraction * 100:+.2f} %".replace(".", ",")


def plain_pct(fraction: Decimal) -> str:
    return f"{fraction * 100:.2f} %".replace(".", ",")


def qty_text(qty: object) -> str:
    text = f"{Decimal(str(qty)):f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def when(ts_ms: object, tz: ZoneInfo) -> str:
    try:
        ts = int(str(ts_ms))
    except (TypeError, ValueError):
        return "-"
    return datetime.fromtimestamp(ts / 1000, tz=UTC).astimezone(tz).strftime("%d/%m %H:%M")


def duration_text(ms: int) -> str:
    if ms < MS_PER_HOUR:
        return f"{max(ms // 60_000, 1)} min"
    if ms < MS_PER_DAY:
        return f"{ms // MS_PER_HOUR} h"
    days, rest = divmod(ms, MS_PER_DAY)
    hours = rest // MS_PER_HOUR
    tail = f" y {hours} h" if hours else ""
    return f"{days} día{'s' if days != 1 else ''}{tail}"


def tz_label(tz_name: str) -> str:
    city = tz_name.rsplit("/", 1)[-1].replace("_", " ")
    return f"hora {city}"


def mode_label(mode: object) -> str:
    return MODE_LABEL.get(str(mode), str(mode))


def phase_label(phase: object) -> str:
    return PHASE_LABEL.get(str(phase), str(phase))


def reason_text(code: object) -> str:
    return REASON_TEXT.get(str(code), str(code))


def exit_reason_text(reason: ExitReason) -> str:
    return EXIT_REASON_TEXT.get(reason, reason.value)


def exit_reason_short(reason: ExitReason) -> str:
    return EXIT_REASON_SHORT.get(reason, reason.value)


def _base(pair: Pair | None) -> str:
    return "" if pair is None else pair.base


def _detail(event: EventRecord) -> str:
    return str(event.payload.get("detail", "")) if event.payload else ""


# ------------------------------------------------------------------ avisos del motor


def entry_text(fill: Fill, position: Position, tz: ZoneInfo) -> str:
    stop_frac = (position.stop_price - position.entry_price) / position.entry_price
    return (
        f"Compró {qty_text(fill.qty)} {fill.pair.base} a {money(fill.price)} {fill.pair.quote} "
        f"cada uno (gastó {money(fill.notional)} {fill.pair.quote}). Si {fill.pair.base} baja a "
        f"{money(position.stop_price)} ({pct(stop_frac)}), vende solo para no perder más. "
        f"{when(fill.fill_ts, tz)}"
    )


def exit_text(trade: Trade, fill: Fill, cash: Decimal, tz: ZoneInfo) -> str:
    verb = "ganó" if trade.pnl >= ZERO else "perdió"
    return (
        f"Vendió {qty_text(trade.qty)} {trade.pair.base} a {money(fill.price)} {trade.pair.quote} "
        f"porque {exit_reason_text(trade.exit_reason)}. Resultado: {verb} "
        f"{money(abs(trade.pnl))} {trade.pair.quote} ({pct(trade.pnl_pct)}) en "
        f"{duration_text(trade.duration_ms)}. Efectivo ahora: {money(cash)} {trade.pair.quote}. "
        f"{when(fill.fill_ts, tz)}"
    )


def protection_text(event: EventRecord, tz: ZoneInfo) -> str:
    detail = _detail(event)
    stamp = when(event.ts, tz)
    if event.kind == PROTECTION_CLEARED:
        base = CLEARED_TEXT.get(event.reason, f"Protección levantada ({event.reason}).")
        if event.reason == "kill_switch" and "flatten" in detail:
            base = "Se canceló el pedido de cerrar todo; sigue en pausa (no compra)."
        return f"{base} {stamp}"
    if event.reason == "kill_switch" and "flatten" in detail:
        return (
            "Pediste cerrar todo: en la próxima revisión vende lo comprado y no compra más. "
            f"{stamp}"
        )
    base = TRIGGERED_TEXT.get(event.reason, f"Protección activada ({event.reason}).")
    extra = f" Detalle técnico: {detail}." if detail and event.reason not in TRIGGERED_TEXT else ""
    return f"{base}{extra} {stamp}"


def rejection_text(event: EventRecord, tz: ZoneInfo) -> str:
    return f"No compró {_base(event.pair)}: {reason_text(event.reason)}. {when(event.ts, tz)}"


def exit_rejected_text(event: EventRecord, tz: ZoneInfo) -> str:
    return (
        f"ATENCION: no pudo vender {_base(event.pair)} ({reason_text(event.reason)}). Lo comprado "
        f"sigue abierto; el bot reintenta en la próxima revisión. {when(event.ts, tz)}"
    )


def stuck_text(event: EventRecord, tz: ZoneInfo) -> str:
    detail = _detail(event) or event.reason
    return (
        f"ATENCION: no puede vender {_base(event.pair)}: Binance no acepta la orden ({detail}). "
        f"Queda comprado hasta que se pueda; el bot reintenta en cada revisión. "
        f"{when(event.ts, tz)}"
    )


def generic_event_text(event: EventRecord, tz: ZoneInfo) -> str:
    detail = _detail(event)
    parts = [event.kind, _base(event.pair), event.reason, detail]
    return f"Aviso técnico: {' '.join(p for p in parts if p)}. {when(event.ts, tz)}"


def feed_text(event: FeedEvent) -> str:
    base = FEED_TEXT.get(event.kind, event.detail)
    who = f" ({event.pair.base})" if event.pair is not None else ""
    return f"Aviso técnico: {base}{who}."


# ------------------------------------------------------------------ ciclo de vida


def startup_text(
    mode: object, *, restored: bool, replay: int, positions: int, equity: Decimal, quote: str
) -> str:
    how = "Retomó lo que tenía guardado" if restored else "Empieza de cero"
    tail = (
        f" Antes revisa {replay} velas que quedaron pendientes mientras estuvo apagado."
        if replay
        else ""
    )
    return (
        f"El bot arrancó en {mode_label(mode)}. {how}: {positions} compra(s) abierta(s), total "
        f"{money(equity)} {quote}.{tail}"
    )


def shutdown_text(bars: int, equity: Decimal, positions: int, quote: str) -> str:
    return (
        f"El bot se detuvo después de {bars} revisiones de precio. Total: {money(equity)} "
        f"{quote}, {positions} compra(s) abierta(s). Mientras esté apagado nadie vigila el "
        "límite de pérdida."
    )


def stale_text(minutes: int) -> str:
    return (
        f"PROBLEMA: el bot lleva {minutes} min sin revisar precios. Se reinicia solo; si este "
        "aviso se repite, hay que mirar el servidor."
    )


def task_dead_text(name: str, exc: BaseException, *, critical: bool) -> str:
    if critical:
        return f"PROBLEMA: una parte del bot ({name}) falló: {exc!r}. Se detiene de forma ordenada."
    return f"Aviso técnico: falló {name} ({exc!r}); el bot sigue sin eso."
