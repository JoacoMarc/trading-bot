"""Estrategias concretas. Importarlas acá las registra en `strategy.registry`."""

from tradingbot.strategy.strategies.ema_trend import EmaTrend, EmaTrendParams

__all__ = ["EmaTrend", "EmaTrendParams"]
