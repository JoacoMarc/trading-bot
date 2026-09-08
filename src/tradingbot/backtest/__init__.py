"""Backtesting: runner sobre el `Engine`, métricas, benchmarks y reportes."""

from tradingbot.backtest.benchmark import BenchmarkResult, buy_and_hold, equal_weights
from tradingbot.backtest.metrics import EquityPoint, Metrics, compute_metrics, max_drawdown
from tradingbot.backtest.runner import (
    BacktestRun,
    RunPayload,
    payload_from_backtest,
    payload_from_benchmark,
    register_payload,
    run_backtest,
    run_benchmark,
)

__all__ = [
    "BacktestRun",
    "BenchmarkResult",
    "EquityPoint",
    "Metrics",
    "RunPayload",
    "buy_and_hold",
    "compute_metrics",
    "equal_weights",
    "max_drawdown",
    "payload_from_backtest",
    "payload_from_benchmark",
    "register_payload",
    "run_backtest",
    "run_benchmark",
]
