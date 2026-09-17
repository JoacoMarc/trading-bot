"""Estrategias concretas. Importarlas acá las registra en `strategy.registry`."""

from tradingbot.strategy.strategies.donchian import Donchian, DonchianParams
from tradingbot.strategy.strategies.ema_trend import EmaTrend, EmaTrendParams
from tradingbot.strategy.strategies.pullback_rsi import PullbackRsi, PullbackRsiParams
from tradingbot.strategy.strategies.regime_bh import RegimeBh, RegimeBhParams

__all__ = [
    "Donchian",
    "DonchianParams",
    "EmaTrend",
    "EmaTrendParams",
    "PullbackRsi",
    "PullbackRsiParams",
    "RegimeBh",
    "RegimeBhParams",
]
