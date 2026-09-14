"""Motor: loop por `Bar`, gestión de posiciones, series y reloj."""

from tradingbot.engine.clock import Clock, RealClock, SimClock
from tradingbot.engine.engine import Engine, EngineResult, EngineState, EngineStats
from tradingbot.engine.position_manager import PositionManager
from tradingbot.engine.series import PrecomputedSeries, RollingSeries, SeriesAt, SeriesProvider

__all__ = [
    "Clock",
    "Engine",
    "EngineResult",
    "EngineState",
    "EngineStats",
    "PositionManager",
    "PrecomputedSeries",
    "RealClock",
    "RollingSeries",
    "SeriesAt",
    "SeriesProvider",
    "SimClock",
]
