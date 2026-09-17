"""Textos en llano (ADR-0012): formato rioplatense, motivos traducidos y avisos del motor."""

from __future__ import annotations

from decimal import Decimal
from zoneinfo import ZoneInfo

from tests.factories import BTC, H4_MS, T0, d, make_fill, make_intent, make_position
from tradingbot.data.live_feed import FEED_LATE, FEED_REPLAY, FeedEvent
from tradingbot.domain import ExitReason, Side, Trade
from tradingbot.notify import texts
from tradingbot.persistence.store import EventRecord
from tradingbot.risk.protections import PROTECTION_CLEARED, PROTECTION_TRIGGERED

BA = ZoneInfo("America/Argentina/Buenos_Aires")


def test_number_and_time_formatting() -> None:
    assert texts.money("9817.04") == "9.817,04"
    assert texts.money(Decimal("1000000")) == "1.000.000,00"
    assert texts.signed_money("120.5") == "+120,50"
    assert texts.signed_money("-178.2") == "-178,20"
    assert texts.pct(Decimal("-0.0183")) == "-1,83 %"
    assert texts.plain_pct(Decimal("0.0191")) == "1,91 %"
    assert texts.qty_text("0.06320000") == "0,0632"
    assert texts.qty_text("10") == "10"
    assert texts.when(T0, BA) == "14/11 17:00"  # T0 = 2023-11-14 20:00 UTC
    assert texts.when("x", BA) == "-"
    assert texts.duration_text(30 * 60_000) == "30 min"
    assert texts.duration_text(8 * 3_600_000) == "8 h"
    assert texts.duration_text(2 * 86_400_000 + 4 * 3_600_000) == "2 días y 4 h"
    assert texts.duration_text(86_400_000) == "1 día"
    assert texts.tz_label("America/Argentina/Buenos_Aires") == "hora Buenos Aires"
    assert texts.mode_label("paper") == "modo prueba (dinero simulado)"
    assert texts.mode_label("live") == "DINERO REAL"


def test_every_reason_code_and_exit_reason_has_a_translation() -> None:
    from tradingbot.risk.sizing import ReasonCode

    for code in ReasonCode:
        assert texts.reason_text(code.value) != code.value, code
    for reason in ExitReason:
        assert texts.exit_reason_text(reason) != reason.value
        assert texts.exit_reason_short(reason).startswith("por ")
    assert texts.reason_text("insufficient_funds").startswith("no alcanzó el efectivo")
    assert texts.reason_text("algo_nuevo") == "algo_nuevo"  # sin traducción: el código tal cual


def test_entry_and_exit_texts() -> None:
    intent = make_intent(qty="0.0632", decision_price="79000", stop_price="63225.11", open_time=T0)
    fill = make_fill(intent, price="79021.51", ref_price="79000")
    position = make_position(qty="0.0632", entry_price="79021.51", stop_price="63225.11")
    text = texts.entry_text(fill, position, BA)
    assert text == (
        "Compró 0,0632 BTC a 79.021,51 USDT cada uno (gastó 4.994,16 USDT). Si BTC baja a "
        "63.225,11 (-19,99 %), vende solo para no perder más. 14/11 21:00"
    )
    sell_intent = make_intent(side=Side.SELL, qty="0.0632", open_time=T0 + 12 * H4_MS)
    sell = make_fill(sell_intent, price="81000", ref_price="81000")
    trade = Trade(
        pair=BTC,
        strategy="ema_trend",
        qty=d("0.0632"),
        entry_price=d("79021.51"),
        entry_time=T0 + H4_MS,
        exit_price=d("81000"),
        exit_time=T0 + 13 * H4_MS,
        exit_reason=ExitReason.SIGNAL,
        fees_quote=d("10"),
        entry_client_order_id=intent.client_order_id,
        exit_client_order_id=sell_intent.client_order_id,
    )
    text = texts.exit_text(trade, sell, Decimal("9930.25"), BA)
    assert text.startswith(
        "Vendió 0,0632 BTC a 81.000,00 USDT porque la estrategia dio señal de salir. "
        "Resultado: ganó 115,04 USDT (+2,30 %) en 2 días. "
        "Efectivo ahora: 9.930,25 USDT."
    )
    loser = trade.model_copy(update={"exit_price": d("70000"), "exit_reason": ExitReason.STOP})
    text = texts.exit_text(loser, sell, Decimal("9000"), BA)
    assert "porque el precio tocó el límite de pérdida. Resultado: perdió 580,16 USDT" in text


def test_protection_rejection_and_stuck_texts() -> None:
    kill = EventRecord(ts=T0, kind=PROTECTION_TRIGGERED, reason="kill_switch")
    assert texts.protection_text(kill, BA).startswith("Pausa activada: el bot no compra más")
    flatten = EventRecord(
        ts=T0, kind=PROTECTION_TRIGGERED, reason="kill_switch", payload={"detail": "flatten: todo"}
    )
    assert texts.protection_text(flatten, BA).startswith("Pediste cerrar todo")
    cleared = EventRecord(ts=T0, kind=PROTECTION_CLEARED, reason="market_filter")
    assert texts.protection_text(cleared, BA).startswith("El mercado volvió a alcista")
    unknown = EventRecord(
        ts=T0, kind=PROTECTION_TRIGGERED, reason="otra_cosa", payload={"detail": "x > y"}
    )
    assert "Protección activada (otra_cosa). Detalle técnico: x > y." in texts.protection_text(
        unknown, BA
    )
    rejected = EventRecord(ts=T0, kind="entry_rejected", pair=BTC, reason="market_filter")
    assert texts.rejection_text(rejected, BA) == (
        "No compró BTC: el mercado en general está bajista: no compra. 14/11 17:00"
    )
    stuck = EventRecord(
        ts=T0, kind="exit_stuck", pair=BTC, reason="min_notional", payload={"detail": "5 USDT"}
    )
    assert texts.stuck_text(stuck, BA).startswith(
        "ATENCION: no puede vender BTC: Binance no acepta la orden (5 USDT)."
    )
    exit_rejected = EventRecord(ts=T0, kind="exit_rejected", pair=BTC, reason="insufficient_funds")
    assert "no pudo vender BTC (no alcanzó el efectivo" in texts.exit_rejected_text(
        exit_rejected, BA
    )
    other = EventRecord(ts=T0, kind="orphan_sell_fill", pair=BTC, reason="tb-x")
    assert (
        texts.generic_event_text(other, BA)
        == "Aviso técnico: orphan_sell_fill BTC tb-x. 14/11 17:00"
    )


def test_feed_and_lifecycle_texts() -> None:
    late = FeedEvent(ts=T0, kind=FEED_LATE, pair=BTC, detail="vela aceptada por reloj")
    assert texts.feed_text(late) == (
        "Aviso técnico: Binance tardó en publicar los precios; el bot siguió con los que había "
        "(BTC)."
    )
    replay = FeedEvent(ts=T0, kind=FEED_REPLAY, detail="3 velas")
    assert "estuvo apagado" in texts.feed_text(replay)
    unknown = FeedEvent(ts=T0, kind="feed_raro", detail="algo pasó")
    assert texts.feed_text(unknown) == "Aviso técnico: algo pasó."
    start = texts.startup_text(
        "paper", restored=True, replay=3, positions=1, equity=Decimal("9817.04"), quote="USDT"
    )
    assert start == (
        "El bot arrancó en modo prueba (dinero simulado). Retomó lo que tenía guardado: "
        "1 compra(s) abierta(s), total 9.817,04 USDT. Antes revisa 3 velas que quedaron "
        "pendientes mientras estuvo apagado."
    )
    fresh = texts.startup_text(
        "paper", restored=False, replay=0, positions=0, equity=Decimal("10000"), quote="USDT"
    )
    assert "Empieza de cero: 0 compra(s) abierta(s), total 10.000,00 USDT." in fresh
    assert fresh.endswith("USDT.")
    stop = texts.shutdown_text(13, Decimal("9817.04"), 1, "USDT")
    assert stop.startswith(
        "El bot se detuvo después de 13 revisiones de precio. Total: 9.817,04 USDT"
    )
    assert "nadie vigila el límite de pérdida" in stop
    assert texts.stale_text(485).startswith("PROBLEMA: el bot lleva 485 min sin revisar precios.")
    assert texts.task_dead_text("watcher", RuntimeError("x"), critical=True).startswith("PROBLEMA")
    assert texts.task_dead_text("daily", RuntimeError("x"), critical=False).startswith(
        "Aviso técnico"
    )
