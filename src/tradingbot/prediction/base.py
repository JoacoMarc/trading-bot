"""Puerto sin red: filtra compras sin cambiar riesgo, salidas ni prioridad."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from tradingbot.domain import Pair, Signal
from tradingbot.strategy.base import StrategyContext


@dataclass(frozen=True)
class EntryDecision:
    accepted: bool
    reason: str
    prediction_id: str = ""


class EntryFilter(Protocol):
    def observe(self, contexts: Mapping[Pair, StrategyContext], signal_ts: int) -> None: ...
    def evaluate(self, signal: Signal, signal_ts: int) -> EntryDecision: ...
