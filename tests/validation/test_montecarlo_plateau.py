"""Monte Carlo por bootstrap y meseta de parámetros (ADR-0008)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.factories import H4_MS, T0, d
from tests.validation.factories import make_metrics
from tradingbot.backtest.metrics import Metrics
from tradingbot.domain.errors import ConfigError
from tradingbot.strategy.base import Choice, FloatRange, IntRange, ParamRange
from tradingbot.validation.montecarlo import block_bootstrap_daily, bootstrap_trades
from tradingbot.validation.plateau import _bump, run_plateau, variations


def test_only_winning_trades_have_no_drawdown() -> None:
    result = bootstrap_trades([d("10")] * 20, d("1000"), runs=200, seed=1)
    assert result.trades == 20
    assert result.dd_p95 == 0.0
    assert result.return_p05 == pytest.approx(0.2)  # 20 x 10 sobre 1000, en todos los caminos


def test_bootstrap_is_deterministic_and_percentiles_are_ordered() -> None:
    pnls = [d(x) for x in ("120", "-40", "-35", "300", "-50", "-45", "80", "-30", "-60", "200")]
    first = bootstrap_trades(pnls, d("1000"), runs=500, seed=7)
    second = bootstrap_trades(pnls, d("1000"), runs=500, seed=7)
    assert first == second
    assert 0.0 < first.dd_p50 <= first.dd_p95 <= first.dd_p99
    assert first.return_p05 <= first.return_p50
    assert bootstrap_trades(pnls, d("1000"), runs=500, seed=8) != first


def test_bootstrap_edge_cases() -> None:
    empty = bootstrap_trades([], d("1000"), runs=10, seed=1)
    assert (empty.trades, empty.dd_p95, empty.return_p50) == (0, 0.0, 0.0)
    with pytest.raises(ValueError, match="positivo"):
        bootstrap_trades([d("1")], d("1000"), runs=0)


def test_bootstrap_drawdown_is_capped_at_100_percent() -> None:
    ruin = bootstrap_trades([d("-600")] * 3, d("1000"), runs=50, seed=1)
    assert ruin.dd_p50 == 1.0
    assert ruin.dd_p99 == 1.0
    assert ruin.return_p50 == pytest.approx(-1.8)


SPACE: dict[str, ParamRange] = {
    "ema_fast": IntRange(10, 30, 1),
    "stop_atr_mult": FloatRange(1.5, 4.0, 0.5),
    "entry_mode": Choice(("cross", "state")),
}
BASE: dict[str, Any] = {"ema_fast": 20, "stop_atr_mult": 2.0, "entry_mode": "cross", "other": 5}


def test_variations_one_at_a_time_plus_vertices_quantized() -> None:
    variants = variations(BASE, SPACE, pct=0.2)
    # 2 por parámetro numérico + 2^2 vértices, sin repetir el base; el categórico no se toca.
    assert len(variants) == 8
    assert BASE not in variants
    assert {v["ema_fast"] for v in variants} == {16, 20, 24}
    assert {v["stop_atr_mult"] for v in variants} == {1.5, 2.0, 2.5}  # 1.6 -> 1.5, 2.4 -> 2.5
    assert all(v["entry_mode"] == "cross" and v["other"] == 5 for v in variants)
    vertices = [v for v in variants if v["ema_fast"] != 20 and v["stop_atr_mult"] != 2.0]
    assert len(vertices) == 4


def test_variations_clamp_to_space_bounds() -> None:
    variants = variations({"ema_fast": 28, "stop_atr_mult": 3.8}, SPACE)
    assert max(v["ema_fast"] for v in variants) == 30
    assert max(v["stop_atr_mult"] for v in variants) == 4.0


def test_run_plateau_counts_failed_variants_as_not_passing() -> None:
    def run_fn(params: Mapping[str, Any]) -> Metrics:
        if params["ema_fast"] > 22:
            msg = "parámetros inválidos"
            raise ConfigError(msg)
        good = params["stop_atr_mult"] >= 2.0
        return make_metrics(
            profit_factor=1.5 if good else 0.9, total_return=d("0.1") if good else d("-0.1")
        )

    result = run_plateau(BASE, SPACE, run_fn, only=("ema_fast", "stop_atr_mult"))
    assert len(result.rows) == 8
    failed = [r for r in result.rows if r.error]
    assert len(failed) == 3  # ema_fast 24 solo y en dos vértices
    assert all(not r.passed for r in failed)
    passing = [r for r in result.rows if r.passed]
    assert all(r.params["stop_atr_mult"] >= 2.0 and r.params["ema_fast"] <= 22 for r in passing)
    assert result.pass_rate == pytest.approx(len(passing) / 8)


@given(
    value=st.floats(min_value=1.5, max_value=4.0),
    sign=st.sampled_from([-1, 1]),
    pct=st.floats(min_value=0.05, max_value=0.5),
)
def test_bump_stays_in_range_and_on_the_grid(value: float, sign: int, pct: float) -> None:
    rng = FloatRange(1.5, 4.0, 0.5)
    result = _bump(value, rng, sign, pct)
    assert rng.low <= result <= rng.high
    steps = (result - rng.low) / rng.step
    assert abs(steps - round(steps)) < 1e-9
    int_rng = IntRange(10, 30, 1)
    bumped = _bump(20, int_rng, sign, pct)
    assert isinstance(bumped, int)
    assert int_rng.low <= bumped <= int_rng.high


def test_plateau_warns_when_base_is_outside_the_space() -> None:
    result = run_plateau(
        {"ema_fast": 35}, {"ema_fast": IntRange(10, 30, 1)}, lambda _p: make_metrics()
    )
    assert result.warnings
    assert "ema_fast=35" in result.warnings[0]


def test_relative_pass_rate_uses_half_of_the_base_sharpe() -> None:
    def run_fn(params: Mapping[str, Any]) -> Metrics:
        return make_metrics(sharpe=1.2 if params["ema_fast"] >= 20 else 0.3, profit_factor=1.5)

    result = run_plateau(
        BASE, SPACE, run_fn, only=("ema_fast",), base_metrics=make_metrics(sharpe=1.0)
    )
    assert result.pass_rate == 1.0  # el criterio absoluto no discrimina
    assert result.relative_pass_rate == pytest.approx(0.5)  # ema_fast 24 sí, 16 no
    assert result.to_dict()["base_sharpe"] == 1.0
    assert run_plateau(BASE, SPACE, run_fn, only=("ema_fast",)).relative_pass_rate is None


def test_block_bootstrap_of_daily_returns() -> None:
    day = 6 * H4_MS
    rising = [(T0 + i * day, d(1000 + 10 * i)) for i in range(120)]
    steady = block_bootstrap_daily(rising, runs=100, seed=3)
    assert steady.trades == 119
    assert steady.dd_p95 == 0.0
    assert steady.return_p05 > 0
    zigzag = [(T0 + i * day, d(1000 + (50 if i % 2 else 0))) for i in range(120)]
    noisy = block_bootstrap_daily(zigzag, runs=100, seed=3)
    assert noisy.dd_p50 > 0
    assert noisy == block_bootstrap_daily(zigzag, runs=100, seed=3)
    assert block_bootstrap_daily(rising[:10], runs=10).trades == 9  # muestra corta: ceros
    with pytest.raises(ValueError, match="positivos"):
        block_bootstrap_daily(rising, runs=0)
