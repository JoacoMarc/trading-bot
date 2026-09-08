from __future__ import annotations

from decimal import Decimal

import pytest

from tests.engine.fakes import H4, MARKETS, candles_from_prices
from tests.factories import BTC, ETH, T0, d, make_intent
from tradingbot.config.models import ExecutionConfig
from tradingbot.domain import Bar, DomainError, ExitReason, OrderStatus, Side
from tradingbot.execution import SimulatedBroker, StopOrder


def broker(**execution: object) -> SimulatedBroker:
    return SimulatedBroker(ExecutionConfig(**execution), MARKETS)


def test_buy_fill_at_next_open_with_slippage_rounded_up() -> None:
    b = broker()
    order = b.submit(make_intent(qty="2"), ts=T0)
    assert order.status is OrderStatus.PENDING
    assert b.pending_orders() == (order,)
    bar = Bar.from_candles(candles_from_prices([("102", "104", "101", "103")], start=T0 + H4))
    events = b.on_bar_open(bar)
    assert len(events) == 1
    fill = events[0].fill
    assert fill is not None
    assert fill.price == Decimal("102.06")
    assert fill.ref_price == Decimal("102")
    assert fill.fee_asset == "BTC"
    assert fill.fee_amount == Decimal("0.002")
    assert fill.fill_ts == T0 + H4
    assert events[0].order.status is OrderStatus.FILLED
    assert b.pending_orders() == ()


def test_sell_fill_rounded_down_and_fee_in_quote() -> None:
    b = broker()
    b.submit(make_intent(side=Side.SELL, qty="2"), ts=T0)
    bar = Bar.from_candles(candles_from_prices([("110", "111", "109", "110")], start=T0 + H4))
    fill = b.on_bar_open(bar)[0].fill
    assert fill is not None
    assert fill.price == Decimal("109.94")
    assert fill.fee_asset == "USDT"
    assert fill.fee_amount == Decimal("109.94") * 2 * Decimal("0.001")


def test_pay_with_bnb_charges_quote_on_both_sides() -> None:
    b = broker(pay_with_bnb=True, slippage_bps=Decimal("0"))
    b.submit(make_intent(qty="1"), ts=T0)
    bar = Bar.from_candles(candles_from_prices([("100", "101", "99", "100")], start=T0 + H4))
    fill = b.on_bar_open(bar)[0].fill
    assert fill is not None
    assert fill.price == Decimal("100")
    assert fill.fee_asset == "USDT"
    assert fill.fee_amount == Decimal("0.075")


def test_pending_order_waits_for_missing_pair() -> None:
    b = broker()
    b.submit(make_intent(qty="1"), ts=T0)
    eth_only = Bar.from_candles(
        candles_from_prices([("10", "11", "9", "10")], pair=ETH, start=T0 + H4)
    )
    assert b.on_bar_open(eth_only) == []
    assert len(b.pending_orders()) == 1


def test_duplicate_or_unknown_market_rejected() -> None:
    b = broker()
    intent = make_intent()
    b.submit(intent, ts=T0)
    with pytest.raises(DomainError, match="ya pendiente"):
        b.submit(intent, ts=T0)
    only_btc = SimulatedBroker(ExecutionConfig(), {BTC: MARKETS[BTC]})
    with pytest.raises(DomainError, match="sin MarketInfo"):
        only_btc.submit(make_intent(pair=ETH), ts=T0)


def _stop(price: str, reason: ExitReason = ExitReason.STOP) -> StopOrder:
    return StopOrder(
        pair=BTC, stop_price=d(price), qty=d("1"), exit_reason=reason, strategy="s", signal_ts=T0
    )


@pytest.mark.parametrize(
    ("candle", "ref", "price"),
    [
        (("90", "93", "88", "91"), "90", "89.95"),
        (("95", "96", "91", "94"), "92.06", "92.01"),
        (("92.06", "93", "92", "92.5"), "92.06", "92.01"),  # open == stop cuenta como gap
    ],
)
def test_stop_execution_paths(candle: tuple[str, str, str, str], ref: str, price: str) -> None:
    b = broker()
    b.set_stop(_stop("92.06", ExitReason.TRAILING))
    bar = Bar.from_candles(candles_from_prices([candle], start=T0 + H4))
    events = b.on_bar(bar)
    assert len(events) == 1
    fill = events[0].fill
    assert fill is not None
    assert fill.side is Side.SELL
    assert fill.ref_price == Decimal(ref)
    assert fill.price == Decimal(price)
    assert events[0].order.intent.exit_reason is ExitReason.TRAILING
    assert events[0].order.intent.client_order_id.endswith("-T")
    assert b.get_stop(BTC) is None


def test_stop_not_touched_or_missing_pair() -> None:
    b = broker()
    b.set_stop(_stop("92.06"))
    assert (
        b.on_bar(Bar.from_candles(candles_from_prices([("95", "96", "93", "94")], start=T0 + H4)))
        == []
    )
    assert (
        b.on_bar(
            Bar.from_candles(
                candles_from_prices([("10", "11", "9", "10")], pair=ETH, start=T0 + H4)
            )
        )
        == []
    )
    assert b.get_stop(BTC) is not None
    assert b.cancel_stop(BTC) is not None
    assert b.cancel_stop(BTC) is None


def test_set_stop_replaces() -> None:
    b = broker()
    b.set_stop(_stop("92"))
    b.set_stop(_stop("95", ExitReason.TRAILING))
    stop = b.get_stop(BTC)
    assert stop is not None
    assert stop.stop_price == Decimal("95")
    assert stop.exit_reason is ExitReason.TRAILING


def test_buy_rejected_without_cash_and_stop_touch_fill_ts() -> None:
    cash = {"free": Decimal("150")}
    b = SimulatedBroker(ExecutionConfig(), MARKETS, free_cash=lambda: cash["free"])
    b.submit(make_intent(qty="1"), ts=T0)  # 1 BTC a ~100.05 -> entra
    b.submit(make_intent(qty="1", open_time=T0 + H4), ts=T0)  # segunda compra: no alcanza
    bar = Bar.from_candles(candles_from_prices([("100", "101", "99", "100")], start=T0 + H4))
    events = b.on_bar_open(bar)
    assert [e.fill is not None for e in events] == [True, False]
    rejected = events[1].order
    assert rejected.status is OrderStatus.REJECTED
    assert rejected.reject_reason is not None
    assert rejected.reject_reason.startswith("insufficient_funds")
    assert b.pending_orders() == ()
    # el stop tocado dentro de la vela se fecha al close; el gap, al open
    b.set_stop(_stop("92.06"))
    touched = b.on_bar(
        Bar.from_candles(candles_from_prices([("95", "96", "91", "94")], start=T0 + 2 * H4))
    )
    assert touched[0].fill is not None
    assert touched[0].fill.fill_ts == T0 + 3 * H4 - 1
    b.set_stop(_stop("92.06"))
    gapped = b.on_bar(
        Bar.from_candles(candles_from_prices([("90", "93", "88", "91")], start=T0 + 3 * H4))
    )
    assert gapped[0].fill is not None
    assert gapped[0].fill.fill_ts == T0 + 3 * H4
