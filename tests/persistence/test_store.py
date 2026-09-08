from __future__ import annotations

from tests.factories import BTC, ETH, T0, d, make_fill, make_intent, make_position
from tradingbot.domain import Order, OrderStatus, PortfolioSnapshot
from tradingbot.persistence import EventRecord, InMemoryStore


def test_in_memory_store_round_trip() -> None:
    store = InMemoryStore()
    intent = make_intent()
    order = Order(intent=intent, created_ts=T0, updated_ts=T0)
    store.save_order(order)
    filled = order.with_fill(make_fill(intent), ts=T0 + 1)
    store.save_order(filled)  # la última versión gana
    assert store.orders() == (filled,)
    assert store.orders()[0].status is OrderStatus.FILLED

    store.save_fill(make_fill(intent))
    assert len(store.fills()) == 1

    btc, eth = make_position(pair=BTC), make_position(pair=ETH, entry_price="10", stop_price="9")
    store.save_position(eth)
    store.save_position(btc)
    assert store.load_open_positions() == (btc, eth)  # ordenadas por par
    store.save_position(btc.raise_stop(d("95")))
    assert store.load_open_positions()[0].stop_price == d("95")
    store.remove_position(BTC)
    store.remove_position(BTC)  # idempotente
    assert store.load_open_positions() == (eth,)

    store.snapshot_equity(PortfolioSnapshot(ts=T0, cash=d("1")))
    store.record_event(EventRecord(ts=T0, kind="entry_rejected", pair=BTC, reason="max_positions"))
    assert len(store.snapshots()) == 1
    assert store.events()[0].kind == "entry_rejected"
    assert store.trades() == ()
