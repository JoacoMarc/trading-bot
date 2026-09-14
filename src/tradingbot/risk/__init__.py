"""Riesgo: sizing, `RiskManager` y protecciones (ADR-0007). Nunca bloquea salidas (regla 7)."""

from tradingbot.risk.manager import (
    ExitDecision,
    PortfolioView,
    Rejection,
    RiskDecision,
    RiskManager,
)
from tradingbot.risk.market_filter import MarketFilter, MarketState
from tradingbot.risk.protections import (
    Block,
    FileKillSwitch,
    KillSwitch,
    KillSwitchState,
    ProtectionEvent,
    Protections,
)
from tradingbot.risk.sizing import ReasonCode, SizingResult, sellable_qty, size_by_risk

__all__ = [
    "Block",
    "ExitDecision",
    "FileKillSwitch",
    "KillSwitch",
    "KillSwitchState",
    "MarketFilter",
    "MarketState",
    "PortfolioView",
    "ProtectionEvent",
    "Protections",
    "ReasonCode",
    "Rejection",
    "RiskDecision",
    "RiskManager",
    "SizingResult",
    "sellable_qty",
    "size_by_risk",
]
