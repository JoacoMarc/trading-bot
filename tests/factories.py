"""Constructores de objetos de dominio para tests."""

from __future__ import annotations

from decimal import Decimal

from tradingbot.domain import (
    Candle,
    ExitReason,
    Fill,
    OrderIntent,
    Pair,
    Position,
    Side,
    Timeframe,
    make_client_order_id,
)

BTC = Pair(base="BTC", quote="USDT")
ETH = Pair(base="ETH", quote="USDT")
H4_MS = Timeframe.H4.ms
T0 = 1_700_000_000_000 - 1_700_000_000_000 % H4_MS  # open_time alineado a 4h


def d(value: str | int | float) -> Decimal:
    return Decimal(str(value))


def make_candle(
    pair: Pair = BTC,
    open_time: int = T0,
    timeframe: Timeframe = Timeframe.H4,
    open: str | int = "100",
    high: str | int = "110",
    low: str | int = "90",
    close: str | int = "105",
    volume: str | int = "1000",
) -> Candle:
    return Candle(
        pair=pair,
        timeframe=timeframe,
        open_time=open_time,
        open=d(open),
        high=d(high),
        low=d(low),
        close=d(close),
        volume=d(volume),
    )


def make_intent(
    pair: Pair = BTC,
    side: Side = Side.BUY,
    qty: str = "0.5",
    decision_price: str = "100",
    stop_price: str | None = "90",
    open_time: int = T0,
    strategy: str = "ema_trend",
    exit_reason: ExitReason | None = None,
) -> OrderIntent:
    if side is Side.SELL and exit_reason is None:
        exit_reason = ExitReason.SIGNAL
    return OrderIntent(
        client_order_id=make_client_order_id(strategy, pair, open_time, side, exit_reason),
        strategy=strategy,
        pair=pair,
        side=side,
        qty=d(qty),
        decision_price=d(decision_price),
        stop_price=d(stop_price) if (stop_price and side is Side.BUY) else None,
        signal_ts=open_time + H4_MS - 1,
        decision_ts=open_time + H4_MS,
        exit_reason=exit_reason,
    )


def make_fill(
    intent: OrderIntent,
    price: str = "101",
    qty: str | None = None,
    fee_amount: str = "0",
    fee_asset: str | None = None,
    fee_quote: str | None = None,
    ref_price: str = "100",
    exchange_trade_id: str | None = None,
) -> Fill:
    received = intent.pair.base if intent.side is Side.BUY else intent.pair.quote
    return Fill(
        client_order_id=intent.client_order_id,
        pair=intent.pair,
        side=intent.side,
        price=d(price),
        qty=d(qty) if qty is not None else intent.qty,
        fee_amount=d(fee_amount),
        fee_asset=fee_asset or received,
        fee_quote=d(fee_quote) if fee_quote is not None else None,
        ref_price=d(ref_price),
        signal_ts=intent.signal_ts,
        decision_ts=intent.decision_ts,
        fill_ts=intent.decision_ts + 500,
        exchange_trade_id=exchange_trade_id,
    )


def make_position(
    pair: Pair = BTC,
    qty: str = "0.5",
    entry_price: str = "100",
    stop_price: str = "90",
    highest_close: str | None = None,
    entry_time: int = T0,
) -> Position:
    return Position(
        pair=pair,
        strategy="ema_trend",
        qty=d(qty),
        entry_price=d(entry_price),
        entry_time=entry_time,
        stop_price=d(stop_price),
        highest_close_since_entry=d(highest_close or entry_price),
        client_order_id=make_client_order_id("ema_trend", pair, entry_time, Side.BUY),
    )
