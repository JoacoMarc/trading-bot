"""Contrato de estrategia, registro y estrategias concretas."""

from tradingbot.strategy import strategies as _strategies  # registra las estrategias concretas
from tradingbot.strategy.base import OhlcvArrays, Strategy, StrategyContext, StrategyParams
from tradingbot.strategy.registry import (
    available_strategies,
    build_strategy,
    effective_warmup,
    get_strategy_class,
    register,
)

__all__ = [
    "OhlcvArrays",
    "Strategy",
    "StrategyContext",
    "StrategyParams",
    "available_strategies",
    "build_strategy",
    "effective_warmup",
    "get_strategy_class",
    "register",
]

del _strategies
