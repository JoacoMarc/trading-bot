"""Fábricas para tests de validación: `Metrics` sintéticas sin correr el motor."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from tests.factories import H4_MS, T0, d
from tradingbot.backtest.metrics import Metrics, compute_metrics

_BASE = compute_metrics([(T0, d("100")), (T0 + H4_MS, d("110"))], [False, True], [], [])


def make_metrics(**overrides: Any) -> Metrics:
    """Métricas de referencia con los campos que el test quiera fijar (sharpe, trades, ...)."""
    return replace(_BASE, **overrides)
