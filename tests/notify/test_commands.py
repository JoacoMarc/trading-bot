"""`CommandService` (ADR-0012) sobre un backend falso: lectura en llano, control y confirmación."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.factories import BTC, H4_MS, T0, d, make_fill, make_intent
from tradingbot.domain import ExitReason, PortfolioSnapshot, Side, Trade
from tradingbot.domain.orders import Fill
from tradingbot.notify.commands import HELP, CommandService, active_protections
from tradingbot.persistence.store import EventRecord
from tradingbot.risk.protections import FileKillSwitch

NOW = T0 + 30 * H4_MS  # 2023-11-19 20:00 UTC = 17:00 en Buenos Aires


def make_trade(pnl_sign: int, exit_time: int, reason: ExitReason = ExitReason.SIGNAL) -> Trade:
    entry = make_intent(open_time=exit_time - 2 * H4_MS)
    exit_ = make_intent(side=Side.SELL, open_time=exit_time, exit_reason=reason)
    exit_price = "110" if pnl_sign > 0 else "95"
    return Trade(
        pair=BTC,
        strategy="ema_trend",
        qty=d("0.5"),
        entry_price=d("100"),
        entry_time=exit_time - 2 * H4_MS,
        exit_price=d(exit_price),
        exit_time=exit_time,
        exit_reason=reason,
        fees_quote=d("0.1"),
        entry_client_order_id=entry.client_order_id,
        exit_client_order_id=exit_.client_order_id,
    )


class FakeBackend:
    def __init__(self, tmp_path: Path) -> None:
        self.kill_switch = FileKillSwitch(tmp_path / "logs" / "STOP")
        self.initial_cash = d("10000")
        self.now = NOW
        self.stale_ms = 90_000
        self.payload: dict[str, Any] = {
            "mode": "paper",
            "phase": "corriendo",
            "bot_version": "0.1.0",
            "strategy": "regime_bh",
            "timeframe": "4h",
            "timeframe_ms": H4_MS,
            "pairs": ["BTC/USDT"],
            "restored_from_db": True,
            "last_bar_open_time": NOW - H4_MS,
            "cash": "4807.95",
            "equity": "9809.00",
            "dust": {},
            "positions": [
                {
                    "pair": "BTC/USDT",
                    "qty": "0.0632",
                    "entry_price": "79021.51",
                    "stop_price": "63225.11",
                    "mark": "76080",
                    "unrealized_pnl": "-185.90",
                    "stop_published": True,
                }
            ],
            "pending_orders": [],
            "protections": {
                "drawdown_halted": "False",
                "daily_halted": "False",
                "losses_paused": "False",
                "kill_switch": "False",
                "peak_equity": "10000",
                "drawdown": "0.0191",
                "pairs_in_cooldown": "",
                "market_filter": "off",
            },
            "stats": {"bars": 13, "fills": 1, "watcher_ticks": 700, "price_errors": 0},
            "notify": {"backend": "telegram", "sent": 5, "errors": 1, "dropped": 0},
            "db": {"counts": {"orders": 1, "fills": 1}},
        }
        self._trades: list[Trade] = []
        self._fills: list[Fill] = []
        self._events: list[EventRecord] = []
        self._snapshots: list[PortfolioSnapshot] = []

    def status_payload(self, phase: str = "corriendo") -> dict[str, Any]:
        return {**self.payload, "phase": phase}

    def trades(self) -> list[Trade]:
        return self._trades

    def fills(self) -> list[Fill]:
        return self._fills

    def events(self) -> list[EventRecord]:
        return self._events

    def snapshots(self) -> list[PortfolioSnapshot]:
        return self._snapshots

    def now_ms(self) -> int:
        return self.now

    def stale_for_ms(self) -> int:
        return self.stale_ms


@pytest.fixture
def backend(tmp_path: Path) -> FakeBackend:
    return FakeBackend(tmp_path)


@pytest.fixture
def service(backend: FakeBackend) -> CommandService:
    return CommandService(backend, timezone="America/Argentina/Buenos_Aires", confirm_window_s=60)


def test_status_in_plain_language(service: CommandService) -> None:
    text = service.handle("/status")
    lines = text.splitlines()
    assert lines[0] == "Modo prueba (dinero simulado) - funcionando"
    assert lines[1] == "Tenés en total 9.809,00 USDT (empezaste con 10.000,00: -1,91 %)"
    assert lines[2] == "Efectivo disponible: 4.807,95 USDT"
    assert lines[3] == (
        "Comprado: 0,0632 BTC a 79.021,51 USDT; hoy vale 76.080,00: vas -185,90 USDT (-3,72 %). "
        "Si baja a 63.225,11 (-19,99 %) vende solo."
    )
    assert lines[4] == (
        "Última revisión de precios: 19/11 13:00 - próxima: 19/11 21:00 (hora Buenos Aires)"
    )
    assert lines[5] == "Protecciones: ninguna activa"
    for jargon in ("equity", "pnl", "fill", "stop "):
        assert jargon not in text.lower()


def test_status_lists_active_protections_and_missing_stop(
    service: CommandService, backend: FakeBackend
) -> None:
    backend.payload["protections"] |= {"drawdown_halted": "True", "kill_switch": "flatten"}
    backend.payload["pending_orders"] = ["tb-x-BTCUSDT-1-B"]
    backend.payload["positions"][0]["stop_published"] = False
    text = service.status()
    assert "pausa por caída fuerte (cayó 1,91 % desde el mejor momento)" in text
    assert "pedido de cerrar todo (vende en la próxima revisión)" in text
    assert "Órdenes esperando ejecutarse: 1" in text
    assert "ATENCION: el límite de pérdida no está cargado en el exchange." in text


def test_balance_and_positions(service: CommandService, backend: FakeBackend) -> None:
    text = service.handle("/balance")
    assert "Efectivo disponible: 4.807,95 USDT" in text
    assert "Invertido (a precio de hoy): 4.808,26 USDT, vas -185,90" in text  # 0.0632 x 76080
    assert "Total: 9.809,00 USDT" in text
    backend.payload["dust"] = {"BTC": "0.00001"}
    assert "Restos que no se pueden vender (muy chicos): 0,00001 BTC" in service.balance()
    backend.payload["positions"] = []
    assert service.handle("/positions") == "No tiene nada comprado: todo está en efectivo."


def test_trades_profit_and_defaults(service: CommandService, backend: FakeBackend) -> None:
    assert service.handle("/trades").startswith("Todavía no cerró ninguna operación")
    backend._trades = [
        make_trade(+1, NOW - 3 * H4_MS),
        make_trade(-1, NOW - 2 * H4_MS, ExitReason.STOP),
        make_trade(+1, NOW - H4_MS),
    ]
    text = service.handle("/trades 2")
    assert text.count("BTC:") == 2
    assert "BTC: perdió 2,60 USDT (-5,20 %) por límite de pérdida" in text  # (95-100)x0.5-0.1
    assert "BTC: ganó 4,90 USDT (+9,80 %) por señal de salida" in text
    assert text.endswith("2 operaciones cerradas: +2,30 USDT en total")
    assert service.handle("/trades").count("BTC:") == 3
    assert service.handle("/trades abc").count("BTC:") == 3  # argumento inválido -> default

    intent = make_intent(qty="0.5")
    backend._fills = [make_fill(intent, price="100.05", fee_amount="0.0005", ref_price="100")]
    text = service.handle("/profit")
    assert "Tenés 9.809,00 USDT; empezaste con 10.000,00: -191,00 (-1,91 %)" in text
    assert "Operaciones ya cerradas: +7,20 USDT en 3 operaciones" in text
    assert "Lo que va lo comprado hoy (sin vender): -185,90 USDT" in text
    assert "Comisiones pagadas: 0,05 USDT" in text  # 0.0005 BTC x 100.05
    assert "Ganó 2 de 3 operaciones (67 %); por cada USDT perdido ganó 3,77" in text


def test_daily_compares_with_the_snapshot_24h_ago(
    service: CommandService, backend: FakeBackend
) -> None:
    day_ago = NOW - 6 * H4_MS
    backend._snapshots = [
        PortfolioSnapshot(ts=day_ago - H4_MS, cash=d("9900")),
        PortfolioSnapshot(ts=day_ago, cash=d("10000")),  # el último en o antes de now - 24 h
        PortfolioSnapshot(ts=NOW - H4_MS, cash=d("9809")),
    ]
    backend._trades = [make_trade(-1, NOW - H4_MS, ExitReason.STOP), make_trade(+1, day_ago - 1)]
    buy = make_intent(qty="0.5", open_time=NOW - 2 * H4_MS)
    sell = make_intent(side=Side.SELL, qty="0.5", open_time=NOW - H4_MS)
    backend._fills = [
        make_fill(buy, price="100.10", ref_price="100"),  # +10 bps en contra
        make_fill(sell, price="99.90", ref_price="100"),  # +10 bps en contra
        make_fill(make_intent(open_time=day_ago - 5 * H4_MS), price="1", ref_price="1"),
    ]
    backend._events = [
        EventRecord(ts=NOW - 1000, kind="feed_late", pair=BTC),
        EventRecord(ts=NOW - 2000, kind="feed_late", pair=BTC),
        EventRecord(ts=day_ago - 1, kind="pending_dropped"),
    ]
    text = service.handle("/daily")
    assert text.startswith("Resumen de las últimas 24 h (19/11 17:00 hora Buenos Aires)")
    assert "Tenés 9.809,00 USDT: -191,00 (-1,91 %) en 24 h" in text
    assert "Caída desde el mejor momento (10.000,00): 1,91 %" in text
    assert "Operaciones cerradas en el día: 1, resultado -2,60 USDT" in text
    assert (
        "Compras/ventas ejecutadas: 2, comisiones 0,00 USDT, precio conseguido 0,10 % peor que "
        "el de referencia"
    ) in text
    assert "Avisos técnicos: feed_late x2" in text
    assert "pending_dropped" not in text


def test_daily_without_snapshots_or_trades(service: CommandService) -> None:
    text = service.daily()
    assert "Tenés 9.809,00 USDT\n" in text
    assert "Operaciones cerradas en el día: ninguna" in text


def test_daily_right_after_start_does_not_pretend_24h(
    service: CommandService, backend: FakeBackend
) -> None:
    backend._snapshots = [PortfolioSnapshot(ts=NOW - 2 * H4_MS, cash=d("10000"))]  # < 24 h
    text = service.daily()
    total_line = next(line for line in text.splitlines() if line.startswith("Tenés "))
    assert "desde la primera revisión (" in total_line
    assert "en 24 h" not in total_line


def test_health_reports_cycle_age_and_notify_counters(service: CommandService) -> None:
    text = service.handle("/health")
    assert "Estado: funcionando - versión 0.1.0 - retomó lo guardado al arrancar" in text
    assert "Última revisión de precios hace 1 min (revisa cada 240 min)" in text
    assert (
        "Revisiones: 13; compras/ventas: 1; controles del límite de pérdida: 700; errores "
        "leyendo precios: 0"
    ) in text
    assert "Avisos por telegram: enviados 5, con error 1, descartados 0" in text
    assert "Base de datos: fills 1, orders 1" in text


def test_pause_stop_and_resume_use_the_kill_switch_files(
    service: CommandService, backend: FakeBackend
) -> None:
    switch = backend.kill_switch
    assert service.handle("/pause").startswith("Pausa activada: desde la próxima revisión")
    assert switch.path.read_text(encoding="utf-8").strip() == "stop"
    assert switch.poll().active
    assert not switch.poll().flatten
    assert service.handle("/resume") == "Pausa levantada: el bot vuelve a poder comprar."
    assert not switch.path.exists()
    assert service.handle("/resume") == "No había ninguna pausa manual activa."

    assert service.handle("/stop").startswith("Pausa activada")  # sin flatten = pause
    assert switch.poll().active
    assert not switch.poll().flatten
    text = service.handle("/resume breaker")
    assert "Pedido levantar la pausa por caída fuerte" in text
    assert "Pausa levantada" in text
    assert switch.resume_path.exists()
    assert switch.consume_resume()


def test_stop_flatten_requires_confirmation_within_the_window(
    service: CommandService, backend: FakeBackend
) -> None:
    switch = backend.kill_switch
    assert service.handle("si") == "No hay nada que confirmar."
    text = service.handle("/stop flatten")
    assert text.startswith("ATENCION: vas a vender TODO")
    assert "60 s" in text
    assert not switch.path.exists()  # todavía nada
    backend.now += 61_000
    assert service.handle("si").startswith("Se venció el tiempo")
    assert not switch.path.exists()

    service.handle("/stop flatten")
    backend.now += 30_000
    assert service.handle("SI").startswith("Confirmado: en la próxima revisión vende todo")
    assert switch.poll().flatten
    assert service.handle("si") == "No hay nada que confirmar."  # la confirmación se consume
    assert service.handle("s") == "No entendí. Mandá /help para ver los comandos."  # una tecla no


def test_dispatch_edge_cases(service: CommandService) -> None:
    assert service.handle("") == HELP
    assert service.handle("/help") == HELP
    assert service.handle("/start") == HELP
    assert service.handle("hola") == "No entendí. Mandá /help para ver los comandos."
    assert service.handle("/nada").startswith("No conozco el comando /nada.")
    assert service.handle("/status@mi_bot").startswith("Modo prueba")
    assert "Glosario" in HELP


def test_active_protections_in_plain_language() -> None:
    assert active_protections({}) == []
    assert active_protections({"daily_halted": "True", "pairs_in_cooldown": "BTC/USDT"}) == [
        "pausa por pérdida diaria",
        "espera tras una pérdida en BTC/USDT",
    ]
    assert active_protections({"market_filter": "deshabilitado (SMA)"}) == [
        "mercado bajista (deshabilitado (SMA))"
    ]
    assert active_protections({"kill_switch": "True"}) == ["pausa manual (no compra)"]
