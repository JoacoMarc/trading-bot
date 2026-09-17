"""`CommandService` (ADR-0012) sobre un backend falso: lectura, control y confirmación."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from tests.factories import BTC, H4_MS, T0, d, make_fill, make_intent, make_position
from tradingbot.domain import ExitReason, PortfolioSnapshot, Side, Trade
from tradingbot.domain.orders import Fill
from tradingbot.notify.commands import HELP, CommandService, active_protections
from tradingbot.persistence.store import EventRecord
from tradingbot.risk.protections import FileKillSwitch

NOW = T0 + 30 * H4_MS  # 5 días después de T0


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


def test_status_summarizes_equity_positions_and_next_close(service: CommandService) -> None:
    text = service.handle("/status")
    assert text.startswith("paper regime_bh 4h BTC/USDT - corriendo")
    assert "equity 9,809.00 (-1.91 % desde 10,000.00) - cash 4,807.95" in text
    assert (
        "BTC/USDT: 0.0632 @ 79,021.51, mark 76,080.00, pnl -185.90 (-3.72 %), "
        "stop 63,225.11 (-19.99 %)"
    ) in text
    assert "proximo cierre" in text
    assert "America/Argentina/Buenos_Aires" in text
    assert "protecciones: ninguna activa" in text


def test_status_lists_active_protections_and_pending_orders(
    service: CommandService, backend: FakeBackend
) -> None:
    backend.payload["protections"] |= {"drawdown_halted": "True", "kill_switch": "flatten"}
    backend.payload["pending_orders"] = ["tb-x-BTCUSDT-1-B"]
    backend.payload["positions"][0]["stop_published"] = False
    text = service.status()
    assert "circuit breaker (DD 1.91 %)" in text
    assert "kill switch (flatten)" in text
    assert "ordenes pendientes: tb-x-BTCUSDT-1-B" in text
    assert "SIN STOP PUBLICADO" in text


def test_balance_and_positions(service: CommandService, backend: FakeBackend) -> None:
    text = service.handle("/balance")
    assert "cash 4,807.95" in text
    assert "invertido 4,808.26 (pnl no realizado -185.90)" in text  # 0.0632 x 76080
    assert "equity 9,809.00" in text
    backend.payload["dust"] = {"BTC": "0.00001"}
    assert "dust: BTC 0.00001" in service.balance()
    backend.payload["positions"] = []
    assert service.handle("/positions") == "sin posiciones abiertas"


def test_trades_profit_and_defaults(service: CommandService, backend: FakeBackend) -> None:
    assert service.handle("/trades") == "sin trades cerrados"
    backend._trades = [
        make_trade(+1, NOW - 3 * H4_MS),
        make_trade(-1, NOW - 2 * H4_MS, ExitReason.STOP),
        make_trade(+1, NOW - H4_MS),
    ]
    text = service.handle("/trades 2")
    assert text.count("BTC/USDT") == 2
    assert "stop pnl -2.60" in text  # (95 - 100) x 0.5 - 0.1
    assert text.endswith("2 trades, pnl 2.30")  # -2.60 + 4.90
    assert service.handle("/trades").count("BTC/USDT") == 3
    assert service.handle("/trades abc").count("BTC/USDT") == 3  # argumento inválido -> default

    intent = make_intent(qty="0.5")
    backend._fills = [make_fill(intent, price="100.05", fee_amount="0.0005", ref_price="100")]
    text = service.handle("/profit")
    assert "equity 9,809.00 vs inicial 10,000.00: -191.00 (-1.91 %)" in text
    assert "realizado 7.20 en 3 trades - no realizado -185.90" in text
    assert "fees pagadas 0.05" in text  # 0.0005 BTC x 100.05
    assert "win rate 67 % - profit factor 3.77" in text  # 9.80 / 2.60


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
    assert text.startswith("resumen 24 h (")
    assert "equity 9,809.00: -191.00 (-1.91 %) en 24 h" in text
    assert "drawdown 1.91 % desde el pico 10,000.00" in text
    assert "1 trades cerrados, pnl -2.60" in text
    assert "2 fills, fees 0.00, shortfall medio +10.0 bps" in text
    assert "eventos: feed_late x2" in text
    assert "pending_dropped" not in text


def test_daily_without_snapshots_or_trades(service: CommandService) -> None:
    text = service.daily()
    assert "equity 9,809.00\n" in text
    assert "sin trades cerrados" in text


def test_daily_right_after_start_does_not_pretend_24h(
    service: CommandService, backend: FakeBackend
) -> None:
    backend._snapshots = [PortfolioSnapshot(ts=NOW - 2 * H4_MS, cash=d("10000"))]  # < 24 h
    text = service.daily()
    equity_line = next(line for line in text.splitlines() if line.startswith("equity "))
    assert "desde el primer cierre (" in equity_line
    assert "en 24 h" not in equity_line


def test_health_reports_cycle_age_and_notify_counters(service: CommandService) -> None:
    text = service.handle("/health")
    assert "fase corriendo - version 0.1.0 - reanudado desde la DB" in text
    assert "ultimo ciclo hace 1 min (timeframe 240 min)" in text
    assert "velas 13, fills 1, ticks del watcher 700, errores de precio 0" in text
    assert "avisos (telegram): enviados 5, errores 1, descartados 0" in text
    assert "db: fills 1, orders 1" in text


def test_pause_stop_and_resume_use_the_kill_switch_files(
    service: CommandService, backend: FakeBackend
) -> None:
    switch = backend.kill_switch
    assert "sin entradas nuevas" in service.handle("/pause")
    assert switch.path.read_text(encoding="utf-8").strip() == "stop"
    assert switch.poll().active
    assert not switch.poll().flatten
    assert "kill switch retirado" in service.handle("/resume")
    assert not switch.path.exists()
    assert service.handle("/resume") == "no habia kill switch activo"

    assert "sin entradas nuevas" in service.handle("/stop")  # sin flatten = pause
    assert switch.poll().active
    assert not switch.poll().flatten
    text = service.handle("/resume breaker")
    assert "circuit breaker pedida" in text
    assert "kill switch retirado" in text
    assert switch.resume_path.exists()
    assert switch.consume_resume()


def test_stop_flatten_requires_confirmation_within_the_window(
    service: CommandService, backend: FakeBackend
) -> None:
    switch = backend.kill_switch
    assert service.handle("si") == "nada que confirmar"
    text = service.handle("/stop flatten")
    assert "ATENCION" in text
    assert "60 s" in text
    assert not switch.path.exists()  # todavía nada
    backend.now += 61_000
    assert "vencio" in service.handle("si")
    assert not switch.path.exists()

    service.handle("/stop flatten")
    backend.now += 30_000
    assert "flatten pedido" in service.handle("SI")
    assert switch.poll().flatten
    assert service.handle("si") == "nada que confirmar"  # la confirmación se consume


def test_dispatch_edge_cases(service: CommandService) -> None:
    assert service.handle("") == HELP
    assert service.handle("/help") == HELP
    assert service.handle("/start") == HELP
    assert service.handle("hola") == "no entendi; /help muestra los comandos"
    assert service.handle("/nada").startswith("comando desconocido: /nada")
    assert service.handle("/status@mi_bot").startswith("paper regime_bh")


def test_helpers() -> None:
    assert active_protections({}) == []
    assert active_protections({"daily_halted": "True", "pairs_in_cooldown": "BTC/USDT"}) == [
        "perdida diaria",
        "cooldown BTC/USDT",
    ]
    assert active_protections({"market_filter": "deshabilitado (SMA)"}) == [
        "filtro de mercado deshabilitado (SMA)"
    ]
    # Fees y shortfall son los del dominio (`Fill.fee_in_quote`, `Fill.shortfall_bps`).
    buy = make_fill(make_intent(), price="100.20", ref_price="100")
    assert buy.shortfall_bps == Decimal("20")
    base_fee = make_fill(make_intent(qty="1"), price="100", fee_amount="0.001")  # fee en BTC
    assert base_fee.fee_in_quote() == Decimal("0.1")
    assert make_position().qty == Decimal("0.5")
