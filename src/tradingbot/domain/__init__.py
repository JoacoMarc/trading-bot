"""Tipos del dominio: inmutables, validados, en `Decimal` y ms UTC."""

from tradingbot.domain.candle import Bar, Candle
from tradingbot.domain.enums import ExitReason, OrderStatus, OrderType, Side, SignalAction
from tradingbot.domain.errors import (
    AuthError,
    ConfigError,
    DataError,
    DomainError,
    ExchangeError,
    ExchangeUnavailable,
    InsufficientFunds,
    InsufficientWarmup,
    InvalidOrder,
    RateLimited,
    TradingBotError,
)
from tradingbot.domain.money import (
    ZERO,
    apply_bps,
    fmt,
    notional,
    quantize_price,
    quantize_qty,
    to_decimal,
)
from tradingbot.domain.orders import Fill, Order, OrderIntent, Signal, make_client_order_id
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import PortfolioSnapshot, Position, Trade
from tradingbot.domain.timeframe import Timeframe

__all__ = [
    "ZERO",
    "AuthError",
    "Bar",
    "Candle",
    "ConfigError",
    "DataError",
    "DomainError",
    "ExchangeError",
    "ExchangeUnavailable",
    "ExitReason",
    "Fill",
    "InsufficientFunds",
    "InsufficientWarmup",
    "InvalidOrder",
    "Order",
    "OrderIntent",
    "OrderStatus",
    "OrderType",
    "Pair",
    "PortfolioSnapshot",
    "Position",
    "RateLimited",
    "Side",
    "Signal",
    "SignalAction",
    "Timeframe",
    "Trade",
    "TradingBotError",
    "apply_bps",
    "fmt",
    "make_client_order_id",
    "notional",
    "quantize_price",
    "quantize_qty",
    "to_decimal",
]
