"""Paridad paper ↔ backtest: cruce por `client_order_id` y desvío de fills en bps."""

from __future__ import annotations

from tests.factories import BTC, ETH, H4_MS, T0, make_fill, make_intent
from tradingbot.domain import Order, OrderIntent, Pair, Side
from tradingbot.validation.parity import (
    FILL_DEVIATION_MAX_BPS,
    SIGNAL_MATCH_MIN,
    compare,
)


def order(open_time: int, pair: Pair = BTC, side: Side = Side.BUY) -> Order:
    intent: OrderIntent = make_intent(pair=pair, side=side, open_time=open_time)
    ts = open_time + H4_MS - 1  # decidida al cierre de la vela
    return Order(intent=intent, created_ts=ts, updated_ts=ts)


def test_identical_runs_match_perfectly() -> None:
    orders = [order(T0), order(T0 + H4_MS, side=Side.SELL)]
    fills = [make_fill(o.intent) for o in orders]
    result = compare(orders, fills, orders, fills, start_ms=T0, end_ms=T0 + 10 * H4_MS)
    assert result.signal_match_rate == 1.0
    assert result.common_ids == 2
    assert len(result.matched) == 2
    assert result.mean_abs_deviation_bps == 0.0
    assert result.passes_gate2
    assert result.to_metrics()["gate2_parity"] is True


def test_missing_orders_and_price_deviation_with_sign() -> None:
    buy, sell = order(T0), order(T0 + H4_MS, side=Side.SELL)
    paper_orders = [
        buy,
        sell,
        order(T0 + 2 * H4_MS, pair=ETH),  # solo en paper
        order(T0 + 50 * H4_MS),  # fuera del rango: se ignora
    ]
    backtest_orders = [buy, sell, order(T0 + 3 * H4_MS, pair=ETH)]  # la de ETH solo en backtest
    paper_fills = [
        make_fill(buy.intent, price="100.10", ref_price="100"),  # compra 10 bps más caro: peor
        make_fill(sell.intent, price="99.80", ref_price="100"),  # venta 20 bps más barato: peor
    ]
    backtest_fills = [
        make_fill(buy.intent, price="100", ref_price="100"),
        make_fill(sell.intent, price="100", ref_price="100"),
    ]
    result = compare(
        paper_orders,
        paper_fills,
        backtest_orders,
        backtest_fills,
        start_ms=T0,
        end_ms=T0 + 10 * H4_MS,
        paper_trades=1,
        backtest_trades=1,
    )
    assert len(result.paper_ids) == 3  # la cuarta cae fuera del rango
    assert result.only_paper == (paper_orders[2].client_order_id,)
    assert result.only_backtest == (backtest_orders[2].client_order_id,)
    assert result.signal_match_rate == 2 / 4
    assert [round(m.deviation_bps, 2) for m in result.matched] == [10.0, 20.0]
    assert result.mean_abs_deviation_bps == 15.0
    assert result.max_abs_deviation_bps == 20.0
    assert result.mean_ref_deviation_bps == 0.0
    assert not result.passes_gate2  # 50 % < 95 %
    metrics = result.to_metrics()
    assert metrics["orders_only_paper"] == 1
    assert metrics["trades_paper"] == 1
    assert SIGNAL_MATCH_MIN == 0.95
    assert FILL_DEVIATION_MAX_BPS == 15.0
