"""`SqliteStore` (ADR-0011): mismo contrato que `InMemoryStore`, durable y reabrible."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.factories import BTC, ETH, T0, d, make_fill, make_intent, make_position
from tradingbot.domain import ExitReason, Order, OrderStatus, PortfolioSnapshot, Trade
from tradingbot.domain.errors import ConfigError
from tradingbot.persistence import SCHEMA_VERSION, EventRecord, SqliteStore, TradeStore


def test_sqlite_store_round_trip_matches_in_memory_contract(tmp_path: Path) -> None:
    store: TradeStore = SqliteStore(tmp_path / "db" / "paper.db")  # crea el directorio
    intent = make_intent()
    order = Order(intent=intent, created_ts=T0, updated_ts=T0)
    store.save_order(order)
    filled = order.with_fill(make_fill(intent), ts=T0 + 1)
    store.save_order(filled)  # la última versión gana
    assert store.orders() == (filled,)
    assert store.orders()[0].status is OrderStatus.FILLED

    store.save_fill(make_fill(intent))
    assert len(store.fills()) == 1
    assert store.fills()[0].price == make_fill(intent).price  # Decimal exacto

    btc, eth = make_position(pair=BTC), make_position(pair=ETH, entry_price="10", stop_price="9")
    store.save_position(eth)
    store.save_position(btc)
    assert store.load_open_positions() == (btc, eth)  # ordenadas por par
    store.save_position(btc.raise_stop(d("95")))
    assert store.load_open_positions()[0].stop_price == d("95")
    store.remove_position(BTC)
    store.remove_position(BTC)  # idempotente
    assert store.load_open_positions() == (eth,)

    snapshot = PortfolioSnapshot(
        ts=T0, cash=d("1"), positions=(eth,), marks={ETH: d("10.5")}, dust={"BTC": d("0.00001")}
    )
    store.snapshot_equity(snapshot)
    store.record_event(
        EventRecord(
            ts=T0, kind="entry_rejected", pair=BTC, reason="max_positions", payload={"n": "3"}
        )
    )
    store.record_event(EventRecord(ts=T0 + 1, kind="protection_triggered", reason="kill_switch"))
    assert store.snapshots() == (snapshot,)  # marks con Pair como clave, dust y equity exactos
    assert store.snapshots()[0].equity == snapshot.equity
    events = store.events()
    assert [e.kind for e in events] == ["entry_rejected", "protection_triggered"]
    assert events[0].pair == BTC
    assert events[0].payload == {"n": "3"}
    assert events[1].pair is None
    assert store.trades() == ()


def test_sqlite_store_persists_across_reopen_and_upserts(tmp_path: Path) -> None:
    path = tmp_path / "paper.db"
    with SqliteStore(path) as store:
        assert store.pragma("journal_mode") == "wal"
        intent = make_intent()
        store.save_order(Order(intent=intent, created_ts=T0, updated_ts=T0))
        trade = Trade(
            pair=BTC,
            strategy="ema_trend",
            qty=d("0.1"),
            entry_price=d("100"),
            entry_time=T0,
            exit_price=d("110"),
            exit_time=T0 + 10,
            exit_reason=ExitReason.SIGNAL,
            fees_quote=d("0.02"),
            entry_client_order_id=intent.client_order_id,
            exit_client_order_id="tb-ema_trend-BTCUSDT-1700000000-S",
        )
        store.save_trade(trade)
        store.save_trade(trade)  # reintento tras reinicio: no duplica
        store.snapshot_equity(PortfolioSnapshot(ts=T0, cash=d("1")))
        store.snapshot_equity(PortfolioSnapshot(ts=T0, cash=d("2")))  # mismo ts: reemplaza
        store.snapshot_equity(PortfolioSnapshot(ts=T0 + 5, cash=d("3")))
        store.save_state("engine", {"cash": "3", "last_bar_open_time": T0 + 5})

    reopened = SqliteStore(path)
    assert len(reopened.orders()) == 1
    assert reopened.trades() == (trade,)
    assert [s.cash for s in reopened.snapshots()] == [d("2"), d("3")]
    last = reopened.last_snapshot()
    assert last is not None
    assert last.ts == T0 + 5
    assert reopened.load_state("engine") == {"cash": "3", "last_bar_open_time": T0 + 5}
    assert reopened.load_state("missing") is None
    assert reopened.load_state("schema_version") == {"version": SCHEMA_VERSION}
    assert reopened.counts() == {
        "orders": 1,
        "fills": 0,
        "positions": 0,
        "trades": 1,
        "equity_snapshots": 2,
        "events": 0,
    }
    reopened.close()


def test_sqlite_store_rejects_unknown_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    store = SqliteStore(path)
    store.save_state("schema_version", {"version": SCHEMA_VERSION + 1})
    store.close()
    with pytest.raises(ConfigError, match="schema_version"):
        SqliteStore(path)


def test_transaction_rolls_back_everything_on_error(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "tx.db")
    intent = make_intent()
    seen_inside: list[dict[str, object] | None] = []

    def cycle_that_dies() -> None:
        with store.transaction():
            store.save_order(Order(intent=intent, created_ts=T0, updated_ts=T0))
            store.save_state("engine", {"cash": "1"})
            seen_inside.append(store.load_state("engine"))  # visible dentro de la transacción
            with store.transaction():  # anidada: reutiliza la externa
                store.save_position(make_position(pair=BTC))
            msg = "corte a mitad de ciclo"
            raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="corte"):
        cycle_that_dies()
    assert seen_inside == [{"cash": "1"}]
    assert store.orders() == ()
    assert store.load_state("engine") is None
    assert store.load_open_positions() == ()
    assert not store.in_transaction
    with store.transaction():
        store.save_state("engine", {"cash": "2"})
    assert store.load_state("engine") == {"cash": "2"}
    store.close()
