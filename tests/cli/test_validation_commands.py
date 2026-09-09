"""CLI `walkforward` y `optimize` sobre el store temporal con los fixtures sintéticos de 2023."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.cli.test_backtest_commands import _invoke
from tradingbot.backtest.runner import date_to_ms, derive_config, load_candles, run_backtest
from tradingbot.config.settings import BotConfig
from tradingbot.validation.walkforward import WalkForwardSettings, run_walkforward


def test_walkforward_fixed_mode_registers_wf_run(workspace: dict[str, Path]) -> None:
    config, experiments = workspace["config"], workspace["experiments"] / "wf"
    code, out = _invoke(
        "walkforward",
        "--config",
        str(config),
        "--is-months",
        "4",
        "--oos-months",
        "2",
        "--montecarlo-runs",
        "200",
        "--plateau",
        "--experiments-dir",
        str(experiments),
    )
    assert code == 0, out
    assert "ventana 1/3" in out
    assert "OOS concatenado" in out
    assert "muestra completa" in out
    assert "monte carlo (200 corridas" in out
    assert "meseta:" in out
    assert "gate 1:" in out
    assert "registrado: WF-0001" in out
    run_dir = next(experiments.joinpath("runs").glob("WF-0001-*"))
    for name in (
        "config.yaml",
        "metrics.json",
        "trades.csv",
        "equity.csv",
        "equity.png",
        "REPORT.md",
    ):
        assert (run_dir / name).exists(), name
    report = (run_dir / "REPORT.md").read_text(encoding="utf-8")
    assert "## Ventanas" in report
    assert "## Gate 1" in report
    assert "## Meseta" in report
    assert "- **Veredicto**: pendiente" in report
    registry = (experiments / "REGISTRY.md").read_text(encoding="utf-8")
    assert "| WF-0001" in registry  # con `*` si el árbol está sucio al correr los tests


def test_walkforward_optimized_mode_without_register(workspace: dict[str, Path]) -> None:
    code, out = _invoke(
        "walkforward",
        "--config",
        str(workspace["config"]),
        "--is-months",
        "4",
        "--oos-months",
        "2",
        "--optimize",
        "--trials",
        "2",
        "--seed",
        "1",
        "--montecarlo-runs",
        "100",
        "--no-register",
    )
    assert code == 0, out
    assert "optimizando IS" in out
    assert "n/a   Régimen" in out  # en modo optimizado los regímenes solo se informan
    assert "n/a   Trades muestra completa" in out
    assert "sin registrar" in out


def test_walkforward_rejects_impossible_windows(workspace: dict[str, Path]) -> None:
    code, out = _invoke(
        "walkforward", "--config", str(workspace["config"]), "--is-months", "24", "--no-register"
    )
    assert code == 1
    assert "no alcanza" in out


def test_optimize_registers_opt_run(workspace: dict[str, Path]) -> None:
    experiments = workspace["experiments"] / "opt"
    code, out = _invoke(
        "optimize",
        "--config",
        str(workspace["config"]),
        "--to",
        "2023-09-01",
        "--trials",
        "3",
        "--seed",
        "1",
        "--experiments-dir",
        str(experiments),
    )
    assert code == 0, out
    assert "mejor score" in out
    assert "in-sample" in out
    assert "registrado: OPT-0001" in out
    report = (
        next(experiments.joinpath("runs").glob("OPT-0001-*"))
        .joinpath("REPORT.md")
        .read_text(encoding="utf-8")
    )
    assert "## Mejores 10 trials" in report
    assert "2023-09-01" in report
    code, out = _invoke(
        "optimize", "--config", str(workspace["config"]), "--objective", "sortino", "--no-register"
    )
    assert code == 1
    assert "objective" in out  # ValidationConfig rechaza el objetivo


def test_derive_config_revalidates_and_keeps_the_original(workspace: dict[str, Path]) -> None:
    cfg = BotConfig.load(workspace["config"])
    with pytest.raises(ValidationError):
        derive_config(cfg, start=date(2023, 9, 1), end=date(2023, 8, 1))
    with pytest.raises(ValidationError):
        derive_config(cfg, start=date(2025, 10, 1))  # dentro del holdout
    derived = derive_config(cfg, params={"ema_fast": 7}, start=date(2023, 3, 1))
    assert derived.strategy.params["ema_fast"] == 7
    assert derived.backtest.start == date(2023, 3, 1)
    assert cfg.strategy.params["ema_fast"] == 5
    assert cfg.backtest.start is None


def test_oos_window_does_not_depend_on_data_after_its_end(workspace: dict[str, Path]) -> None:
    cfg = BotConfig.load(workspace["config"])
    result = run_walkforward(
        cfg, WalkForwardSettings(is_months=4, oos_months=2, montecarlo_runs=100)
    )
    first = result.windows[0].window
    full = load_candles(cfg)
    cutoff = date_to_ms(first.oos_end)
    truncated = {p: [c for c in cs if c.open_time < cutoff] for p, cs in full.items()}
    cfg_oos = derive_config(cfg, start=first.oos_start, end=first.oos_end)
    with_future = run_backtest(cfg_oos, candles=full, with_benchmarks=False)
    without_future = run_backtest(cfg_oos, candles=truncated, with_benchmarks=False)
    assert with_future.metrics == without_future.metrics
    assert [t.pnl for t in with_future.trades] == [t.pnl for t in without_future.trades]
    assert with_future.equity == without_future.equity
    assert result.windows[0].oos_metrics == with_future.metrics
    assert (result.oos_equity[0][0], result.oos_equity[0][1]) == with_future.equity[0]


def test_walkforward_frozen_config_reproduces_the_run(workspace: dict[str, Path]) -> None:
    experiments = workspace["experiments"] / "wf-repro"
    code, out = _invoke(
        "walkforward",
        "--config",
        str(workspace["config"]),
        "--is-months",
        "4",
        "--oos-months",
        "2",
        "--montecarlo-runs",
        "100",
        "--experiments-dir",
        str(experiments),
    )
    assert code == 0, out
    frozen = next(experiments.joinpath("runs").glob("WF-0001-*")) / "config.yaml"
    assert "validation:" in frozen.read_text(encoding="utf-8")
    again = experiments / "again"
    code, out = _invoke("walkforward", "--config", str(frozen), "--experiments-dir", str(again))
    assert code == 0, out
    first = (next(experiments.joinpath("runs").glob("WF-0001-*")) / "metrics.json").read_text(
        encoding="utf-8"
    )
    second = (next(again.joinpath("runs").glob("WF-0001-*")) / "metrics.json").read_text(
        encoding="utf-8"
    )
    import json

    assert json.loads(first)["metrics"] == json.loads(second)["metrics"]
    assert (
        json.loads(first)["meta"]["extra"]["walkforward"]
        == json.loads(second)["meta"]["extra"]["walkforward"]
    )


def test_walkforward_and_optimize_refuse_the_holdout(workspace: dict[str, Path]) -> None:
    code, out = _invoke(
        "walkforward",
        "--config",
        str(workspace["config"]),
        "--is-months",
        "4",
        "--oos-months",
        "2",
        "--set",
        "backtest.include_holdout=true",
        "--no-register",
    )
    assert code == 1
    assert "holdout" in out
    code, out = _invoke(
        "optimize",
        "--config",
        str(workspace["config"]),
        "--trials",
        "1",
        "--set",
        "backtest.include_holdout=true",
        "--no-register",
    )
    assert code == 1
    assert "holdout" in out
