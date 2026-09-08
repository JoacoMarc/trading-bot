from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from tests.factories import BTC, ETH, T0, d, make_fill, make_intent
from tradingbot.domain import (
    ExitReason,
    Order,
    OrderStatus,
    OrderType,
    Pair,
    Side,
    Signal,
    SignalAction,
    make_client_order_id,
)
from tradingbot.domain.orders import CLIENT_ORDER_ID_MAX_LEN, CLIENT_ORDER_ID_RE, order_purpose_tag


def test_client_order_id_is_deterministic_and_binance_compatible() -> None:
    cid = make_client_order_id("ema_trend", BTC, T0, Side.BUY)
    assert cid == f"tb-ema_trend-BTCUSDT-{T0 // 1000}-B"
    assert cid == make_client_order_id("ema_trend", BTC, T0, Side.BUY)
    assert CLIENT_ORDER_ID_RE.match(cid)


def test_client_order_id_distinguishes_exit_purpose() -> None:
    ids = {
        reason: make_client_order_id("ema_trend", BTC, T0, Side.SELL, reason)
        for reason in ExitReason
    }
    assert len(set(ids.values())) == len(ExitReason)
    assert ids[ExitReason.SIGNAL].endswith("-S")
    assert ids[ExitReason.STOP].endswith("-X")
    assert ids[ExitReason.TRAILING].endswith("-T")
    assert ids[ExitReason.FLATTEN].endswith("-F")
    assert ids[ExitReason.RISK].endswith("-R")


def test_purpose_tag_rules() -> None:
    assert order_purpose_tag(Side.BUY, None) == "B"
    with pytest.raises(ValueError, match="no lleva exit_reason"):
        order_purpose_tag(Side.BUY, ExitReason.STOP)
    with pytest.raises(ValueError, match="requiere exit_reason"):
        order_purpose_tag(Side.SELL, None)
    with pytest.raises(ValueError, match="requiere exit_reason"):
        make_client_order_id("s", BTC, T0, Side.SELL)


def test_client_order_id_truncates_long_strategy_and_sanitizes() -> None:
    long_name = "una estrategia con espacios y acentos áé!!" * 3
    cid = make_client_order_id(long_name, Pair(base="ABCDEFGHIJKL", quote="USDT"), T0, Side.BUY)
    assert len(cid) <= CLIENT_ORDER_ID_MAX_LEN
    assert CLIENT_ORDER_ID_RE.match(cid)
    assert make_client_order_id("!!!", BTC, T0, Side.BUY).startswith("tb-s-")


def test_client_order_id_rejects_negative_time() -> None:
    with pytest.raises(ValueError, match="negativo"):
        make_client_order_id("x", BTC, -1, Side.BUY)


@given(
    strategy=st.text(min_size=0, max_size=40),
    base=st.from_regex(r"\A[A-Z0-9]{1,12}\Z"),
    open_time=st.integers(min_value=0, max_value=4_102_444_800_000),
    side=st.sampled_from(list(Side)),
    reason=st.sampled_from(list(ExitReason)),
)
def test_client_order_id_always_valid(
    strategy: str, base: str, open_time: int, side: Side, reason: ExitReason
) -> None:
    if base == "USDT":
        return
    pair = Pair(base=base, quote="USDT")
    cid = make_client_order_id(
        strategy, pair, open_time, side, reason if side is Side.SELL else None
    )
    assert len(cid) <= CLIENT_ORDER_ID_MAX_LEN
    assert CLIENT_ORDER_ID_RE.match(cid)


def test_signal_rules() -> None:
    Signal(
        action=SignalAction.ENTER_LONG, pair=BTC, open_time=T0, stop_price=d("90"), strength=25.0
    )
    Signal(action=SignalAction.EXIT_LONG, pair=BTC, open_time=T0, exit_reason=ExitReason.SIGNAL)
    assert Signal.hold(BTC, T0).action is SignalAction.HOLD
    with pytest.raises(ValidationError, match="requiere stop_price"):
        Signal(action=SignalAction.ENTER_LONG, pair=BTC, open_time=T0)
    with pytest.raises(ValidationError, match="ENTER_LONG no lleva exit_reason"):
        Signal(
            action=SignalAction.ENTER_LONG,
            pair=BTC,
            open_time=T0,
            stop_price=d("90"),
            exit_reason=ExitReason.SIGNAL,
        )
    with pytest.raises(ValidationError, match="requiere exit_reason"):
        Signal(action=SignalAction.EXIT_LONG, pair=BTC, open_time=T0)
    with pytest.raises(ValidationError, match="EXIT_LONG no lleva stop_price"):
        Signal(
            action=SignalAction.EXIT_LONG,
            pair=BTC,
            open_time=T0,
            exit_reason=ExitReason.STOP,
            stop_price=d("1"),
        )
    with pytest.raises(ValidationError, match="HOLD no lleva"):
        Signal(action=SignalAction.HOLD, pair=BTC, open_time=T0, stop_price=d("1"))


def _intent_with(**update: object) -> None:
    base = make_intent()
    base.model_validate(base.model_dump() | update)


def test_intent_rules() -> None:
    buy = make_intent()
    assert buy.expected_notional == Decimal("50")
    assert buy.order_type is OrderType.MARKET
    sell = make_intent(side=Side.SELL, exit_reason=ExitReason.STOP)
    assert sell.stop_price is None
    assert sell.client_order_id.endswith("-X")

    with pytest.raises(ValidationError, match="requiere limit_price"):
        _intent_with(order_type=OrderType.LIMIT)
    with pytest.raises(ValidationError, match="MARKET no lleva limit_price"):
        _intent_with(limit_price=d("99"))
    with pytest.raises(ValidationError, match="requiere exit_reason"):
        _intent_with(side=Side.SELL, stop_price=None)
    with pytest.raises(ValidationError, match="una venta no lleva stop_price"):
        _intent_with(side=Side.SELL, exit_reason=ExitReason.SIGNAL)
    with pytest.raises(ValidationError, match="una compra requiere stop_price"):
        _intent_with(stop_price=None)
    with pytest.raises(ValidationError, match="no lleva exit_reason"):
        _intent_with(exit_reason=ExitReason.SIGNAL)
    with pytest.raises(ValidationError, match="bajo el precio de decisión"):
        make_intent(stop_price="100")
    with pytest.raises(ValidationError, match="decision_ts anterior"):
        _intent_with(decision_ts=0)
    with pytest.raises(ValidationError, match="String should match pattern"):
        _intent_with(client_order_id="con espacios")


def test_fill_shortfall_and_net_amounts() -> None:
    buy = make_fill(make_intent(), price="101", ref_price="100", fee_amount="0.0005")
    assert buy.shortfall_bps == Decimal("100")
    assert buy.fee_asset == "BTC"
    assert buy.net_base_qty == Decimal("0.4995")
    assert buy.net_quote_amount == Decimal("0")
    assert buy.fee_in_quote() == Decimal("0.0505")
    assert buy.fee_in_quote(Decimal("200")) == Decimal("0.1")

    sell = make_fill(make_intent(side=Side.SELL), price="99", ref_price="100", fee_amount="0.0495")
    assert sell.shortfall_bps == Decimal("100")
    assert sell.fee_asset == "USDT"
    assert sell.notional == Decimal("49.5")
    assert sell.net_quote_amount == Decimal("49.4505")
    assert sell.net_base_qty == Decimal("0")
    assert sell.fee_in_quote() == Decimal("0.0495")

    better = make_fill(make_intent(), price="99", ref_price="100")
    assert better.shortfall_bps == Decimal("-100")


def test_fill_fee_in_third_asset_requires_quote_conversion() -> None:
    bnb = make_fill(make_intent(), fee_amount="0.0001", fee_asset="BNB", fee_quote="0.0375")
    assert bnb.net_base_qty == bnb.qty
    assert bnb.fee_in_quote() == Decimal("0.0375")
    with pytest.raises(ValidationError, match="requiere fee_quote"):
        make_fill(make_intent(), fee_amount="0.0001", fee_asset="BNB")
    with pytest.raises(ValidationError, match="solo aplica"):
        make_fill(make_intent(), fee_amount="0.0005", fee_quote="0.05")
    free = make_fill(make_intent(), fee_amount="0", fee_asset="BNB")
    assert free.fee_in_quote() == Decimal("0")


def test_order_lifecycle() -> None:
    intent = make_intent(qty="1")
    order = Order(intent=intent, created_ts=T0, updated_ts=T0)
    assert order.status is OrderStatus.PENDING
    assert order.remaining_qty == Decimal("1")
    assert order.avg_fill_price is None
    assert not order.is_done

    partial = order.with_fill(
        make_fill(intent, price="100", qty="0.4", exchange_trade_id="t1"), ts=T0 + 1
    )
    assert partial.status is OrderStatus.PARTIALLY_FILLED
    assert partial.filled_qty == Decimal("0.4")
    assert partial.remaining_qty == Decimal("0.6")

    done = partial.with_fill(
        make_fill(intent, price="110", qty="0.6", exchange_trade_id="t2"), ts=T0 + 2
    )
    assert done.status is OrderStatus.FILLED
    assert done.is_done
    assert done.avg_fill_price == Decimal("106")
    assert done.client_order_id == intent.client_order_id

    rejected = order.with_status(
        OrderStatus.REJECTED, ts=T0 + 3, reason="-2010 insufficient balance"
    )
    assert rejected.is_done
    assert rejected.reject_reason == "-2010 insufficient balance"


def test_with_fill_enforces_invariants() -> None:
    intent = make_intent(qty="1")
    order = Order(intent=intent, created_ts=T0, updated_ts=T0)
    with pytest.raises(ValidationError, match="llenado"):
        order.with_fill(make_fill(intent, qty="2"), ts=T0 + 1)
    with pytest.raises(ValidationError, match="fill de"):
        order.with_fill(make_fill(make_intent(pair=ETH)), ts=T0 + 1)
    wrong_side = make_fill(make_intent(side=Side.SELL)).model_copy(
        update={"client_order_id": intent.client_order_id}
    )
    with pytest.raises(ValidationError, match="fill de"):
        order.with_fill(wrong_side, ts=T0 + 1)
    first = order.with_fill(make_fill(intent, qty="0.5", exchange_trade_id="t1"), ts=T0 + 1)
    with pytest.raises(ValidationError, match="repetido"):
        first.with_fill(make_fill(intent, qty="0.5", exchange_trade_id="t1"), ts=T0 + 2)
    canceled = order.with_status(OrderStatus.CANCELED, ts=T0 + 1)
    with pytest.raises(ValueError, match="no admite fills"):
        canceled.with_fill(make_fill(intent, qty="0.5"), ts=T0 + 2)
    with pytest.raises(ValidationError, match="anterior"):
        order.with_status(OrderStatus.OPEN, ts=T0 - 1)


def test_order_construction_invariants() -> None:
    intent = make_intent(qty="1")
    with pytest.raises(ValidationError, match="fill de"):
        Order(
            intent=intent, created_ts=T0, updated_ts=T0, fills=(make_fill(make_intent(pair=ETH)),)
        )
    with pytest.raises(ValidationError, match="llenado"):
        Order(intent=intent, created_ts=T0, updated_ts=T0, fills=(make_fill(intent, qty="2"),))
    with pytest.raises(ValidationError, match="anterior"):
        Order(intent=intent, created_ts=T0, updated_ts=T0 - 1)


def test_terminal_statuses() -> None:
    assert OrderStatus.FILLED.is_terminal
    assert OrderStatus.CANCELED.is_terminal
    assert not OrderStatus.OPEN.is_terminal
