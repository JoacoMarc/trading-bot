"""Estrategias concretas. Importarlas acá las registra en `strategy.registry`."""

from tradingbot.strategy.strategies.ema_trend import EmaTrend, EmaTrendParams
from tradingbot.strategy.strategies.regime_bh import RegimeBh, RegimeBhParams

__all__ = ["EmaTrend", "EmaTrendParams", "RegimeBh", "RegimeBhParams"]
