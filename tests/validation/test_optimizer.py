"""Optimizador optuna (ADR-0008): score penalizado, determinismo y trials fallidos."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import optuna
import pytest

from tests.validation.factories import make_metrics
from tradingbot.backtest.metrics import Metrics
from tradingbot.domain.errors import ConfigError
from tradingbot.strategy.base import Choice, FloatRange, IntRange, ParamRange
from tradingbot.validation.optimizer import (
    FAILED_SCORE,
    OptimizeSettings,
    optimize,
    score_metrics,
    suggest_params,
)


def test_score_penalizes_few_trades_in_both_signs() -> None:
    assert score_metrics(make_metrics(sharpe=1.0, trades=40), "sharpe", 40) == 1.0
    assert score_metrics(make_metrics(sharpe=1.0, trades=20), "sharpe", 40) == pytest.approx(0.5)
    assert score_metrics(make_metrics(sharpe=-1.0, trades=20), "sharpe", 40) == pytest.approx(-1.5)
    assert score_metrics(make_metrics(sharpe=None, trades=80), "sharpe", 40) == 10.0  # tope
    assert score_metrics(make_metrics(profit_factor=2.0, trades=5), "profit_factor", 0) == 2.0
    # Sin pérdidas el PF es None: tope finito penalizado, no un fallo.
    assert score_metrics(make_metrics(profit_factor=None, trades=3), "profit_factor", 40) == (
        pytest.approx(10.0 * 3 / 40)
    )
    assert score_metrics(make_metrics(sharpe=1.0, trades=0), "sharpe", 40) == FAILED_SCORE


SPACE: dict[str, ParamRange] = {"x": IntRange(0, 100, 1), "y": FloatRange(0.0, 1.0, 0.1)}


def _bowl(params: Mapping[str, Any]) -> Metrics:
    x, y = params["x"], params["y"]
    return make_metrics(sharpe=2.0 - (x - 70) ** 2 / 1000 - (y - 0.5) ** 2, trades=100)


def test_optimize_is_deterministic_and_finds_the_bowl() -> None:
    settings = OptimizeSettings(trials=40, seed=7)
    first = optimize(_bowl, SPACE, settings)
    second = optimize(_bowl, SPACE, settings)
    assert first.best_params == second.best_params
    assert [t.params for t in first.trials] == [t.params for t in second.trials]
    assert len(first.trials) == 40
    assert first.completed == 40
    assert 55 <= first.best_params["x"] <= 85
    assert first.best_score == max(t.score for t in first.trials)
    assert first.best_metrics is not None
    assert first.best_metrics.sharpe == pytest.approx(first.best_score)


def test_optimize_records_failed_trials_and_keeps_best_valid() -> None:
    def run_fn(params: Mapping[str, Any]) -> Metrics:
        if params["x"] > 50:
            msg = "fuera de rango"
            raise ConfigError(msg)
        return _bowl(params)

    result = optimize(run_fn, SPACE, OptimizeSettings(trials=30, seed=3))
    failed = [t for t in result.trials if t.error]
    assert failed
    assert all(t.score == FAILED_SCORE for t in failed)
    assert result.best_params["x"] <= 50
    assert result.completed == 30 - len(failed)


def test_optimize_requires_a_space_and_a_known_objective() -> None:
    with pytest.raises(ConfigError, match="search_space"):
        optimize(_bowl, {}, OptimizeSettings(trials=1))
    with pytest.raises(ConfigError, match="objetivo"):
        optimize(_bowl, SPACE, OptimizeSettings(trials=1, objective="sortino"))  # type: ignore[arg-type]


def test_suggest_params_rounds_floats_and_handles_choices() -> None:
    trial = optuna.trial.FixedTrial({"x": 3, "y": 0.3, "mode": "state"})
    params = suggest_params(trial, {**SPACE, "mode": Choice(("cross", "state"))})
    assert params == {"x": 3, "y": 0.3, "mode": "state"}
