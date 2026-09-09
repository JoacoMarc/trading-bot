"""Optimización de parámetros con optuna, solo sobre in-sample (ADR-0008).

`optimize` es agnóstico del runner: recibe `run_fn(params) -> Metrics`. `run_optimization` lo
conecta con `run_backtest` sobre el rango de la config (que debe ser el IS: el holdout queda
excluido por defecto y el OOS lo evalúa el walk-forward).
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

import optuna
from pydantic import ValidationError

from tradingbot.backtest.metrics import Metrics
from tradingbot.backtest.runner import (
    BacktestRun,
    derive_config,
    load_candles,
    load_markets_for,
    run_backtest,
)
from tradingbot.config.settings import BotConfig
from tradingbot.domain.candle import Candle
from tradingbot.domain.errors import ConfigError, TradingBotError
from tradingbot.domain.pair import Pair
from tradingbot.exchange.binance import MarketInfo
from tradingbot.strategy.base import Choice, FloatRange, IntRange, ParamRange
from tradingbot.strategy.registry import build_strategy

Objective = Literal["sharpe", "calmar", "profit_factor"]
OBJECTIVES: tuple[Objective, ...] = ("sharpe", "calmar", "profit_factor")
FAILED_SCORE = -100.0
CAP_SCORE = 10.0  # objetivo sin pérdidas (PF) o sin DD (Calmar): tope finito, no fallo

optuna.logging.set_verbosity(logging.WARNING)


@dataclass(frozen=True, slots=True)
class OptimizeSettings:
    trials: int = 50
    seed: int = 42
    objective: Objective = "sharpe"
    min_trades: int = 40

    def to_dict(self) -> dict[str, Any]:
        return {
            "trials": self.trials,
            "seed": self.seed,
            "objective": self.objective,
            "min_trades": self.min_trades,
        }


@dataclass(frozen=True, slots=True)
class TrialRow:
    number: int
    params: dict[str, Any]
    score: float
    total_return: Decimal | None
    sharpe: float | None
    max_drawdown: float | None
    profit_factor: float | None
    trades: int | None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "params": self.params,
            "score": self.score,
            "total_return": None if self.total_return is None else str(self.total_return),
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "profit_factor": self.profit_factor,
            "trades": self.trades,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    settings: OptimizeSettings
    space: dict[str, str]
    best_params: dict[str, Any]
    best_score: float
    best_metrics: Metrics | None
    trials: list[TrialRow] = field(default_factory=list)
    duration_s: float = 0.0

    @property
    def completed(self) -> int:
        return sum(1 for t in self.trials if not t.error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": self.settings.to_dict(),
            "space": self.space,
            "best_params": self.best_params,
            "best_score": self.best_score,
            "completed_trials": self.completed,
            "duration_s": round(self.duration_s, 1),
        }


def score_metrics(metrics: Metrics, objective: Objective, min_trades: int) -> float:
    """Valor del objetivo penalizado por pocos trades (ADR-0008).

    Sin trades no hay evidencia: `FAILED_SCORE`. Un objetivo indefinido por falta de pérdidas
    (PF) o de drawdown (Calmar) vale `CAP_SCORE` y sigue penalizado por pocos trades.
    """
    if metrics.trades == 0:
        return FAILED_SCORE
    raw = getattr(metrics, objective)
    if raw is None:
        value = CAP_SCORE
    elif not math.isfinite(float(raw)):
        value = CAP_SCORE if float(raw) > 0 else FAILED_SCORE
    else:
        value = float(raw)
    if min_trades <= 0 or metrics.trades >= min_trades:
        return value
    share = metrics.trades / min_trades
    return value * share if value > 0 else value - (1.0 - share)


def describe_space(space: Mapping[str, ParamRange]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, rng in space.items():
        if isinstance(rng, IntRange):
            out[name] = f"int {rng.low}..{rng.high} paso {rng.step}"
        elif isinstance(rng, FloatRange):
            out[name] = f"float {rng.low}..{rng.high} paso {rng.step}"
        else:
            out[name] = "uno de " + ", ".join(str(o) for o in rng.options)
    return out


def suggest_params(
    trial: optuna.trial.BaseTrial, space: Mapping[str, ParamRange]
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, rng in space.items():
        if isinstance(rng, IntRange):
            params[name] = trial.suggest_int(name, rng.low, rng.high, step=rng.step)
        elif isinstance(rng, FloatRange):
            params[name] = round(trial.suggest_float(name, rng.low, rng.high, step=rng.step), 3)
        elif isinstance(rng, Choice):
            params[name] = trial.suggest_categorical(name, list(rng.options))
    return params


def optimize(
    run_fn: Callable[[Mapping[str, Any]], Metrics],
    space: Mapping[str, ParamRange],
    settings: OptimizeSettings,
    *,
    progress: Callable[[str], None] | None = None,
) -> OptimizationResult:
    """TPE con semilla, secuencial. Una corrida inválida puntúa `FAILED_SCORE` y se registra."""
    if not space:
        msg = "la estrategia no declara search_space(); nada que optimizar"
        raise ConfigError(msg)
    if settings.objective not in OBJECTIVES:
        msg = f"objetivo desconocido {settings.objective!r}; válidos: {', '.join(OBJECTIVES)}"
        raise ConfigError(msg)
    started = time.perf_counter()
    study = optuna.create_study(
        direction="maximize", sampler=optuna.samplers.TPESampler(seed=settings.seed)
    )
    rows: list[TrialRow] = []
    best: tuple[float, dict[str, Any], Metrics] | None = None

    def objective(trial: optuna.Trial) -> float:
        nonlocal best
        params = suggest_params(trial, space)
        try:
            metrics = run_fn(params)
        except (ValidationError, TradingBotError) as exc:
            rows.append(
                TrialRow(
                    trial.number, params, FAILED_SCORE, None, None, None, None, None, str(exc)[:120]
                )
            )
            return FAILED_SCORE
        score = score_metrics(metrics, settings.objective, settings.min_trades)
        rows.append(
            TrialRow(
                trial.number,
                params,
                score,
                metrics.total_return,
                metrics.sharpe,
                metrics.max_drawdown,
                metrics.profit_factor,
                metrics.trades,
            )
        )
        if best is None or score > best[0]:
            best = (score, params, metrics)
        if progress:
            progress(
                f"trial {trial.number + 1}/{settings.trials}: score {score:.3f} "
                f"(mejor {max(score, best[0]):.3f}) {params}"
            )
        return score

    study.optimize(objective, n_trials=settings.trials)
    if best is None:
        return OptimizationResult(
            settings,
            describe_space(space),
            {},
            FAILED_SCORE,
            None,
            rows,
            time.perf_counter() - started,
        )
    return OptimizationResult(
        settings=settings,
        space=describe_space(space),
        best_params=dict(best[1]),
        best_score=best[0],
        best_metrics=best[2],
        trials=rows,
        duration_s=time.perf_counter() - started,
    )


@dataclass(frozen=True, slots=True)
class OptimizationRun:
    config: BotConfig
    result: OptimizationResult
    best_run: BacktestRun


def run_optimization(
    config: BotConfig,
    settings: OptimizeSettings,
    *,
    markets: Mapping[Pair, MarketInfo] | None = None,
    candles: Mapping[Pair, Sequence[Candle]] | None = None,
    progress: Callable[[str], None] | None = None,
) -> OptimizationRun:
    """Optimiza sobre el rango de `config` (IS) y vuelve a correr los mejores parámetros."""
    if config.backtest.include_holdout:
        msg = "la optimización nunca incluye el holdout (docs/GATES.md)"
        raise ConfigError(msg)
    strategy = build_strategy(config.strategy)
    space = strategy.search_space()
    cached = candles if candles is not None else load_candles(config)
    market_infos = load_markets_for(list(config.strategy.pairs), markets)

    def run_fn(params: Mapping[str, Any]) -> Metrics:
        return run_backtest(
            derive_config(config, params=params),
            markets=market_infos,
            with_benchmarks=False,
            candles=cached,
        ).metrics

    result = optimize(run_fn, space, settings, progress=progress)
    best_config = derive_config(config, params=result.best_params) if result.best_params else config
    best_run = run_backtest(best_config, markets=market_infos, candles=cached)
    return OptimizationRun(config=best_config, result=result, best_run=best_run)
