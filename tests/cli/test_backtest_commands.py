"""CLI de backtesting sobre un store temporal con los fixtures sintéticos de 2023."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from tradingbot.cli.app import app

runner = CliRunner()


def _invoke(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, list(args), env={"PYTHONUTF8": "1"})
    return result.exit_code, result.output


def test_backtest_registers_run_and_is_reproducible(workspace: dict[str, Path]) -> None:
    config, experiments = workspace["config"], workspace["experiments"]
    code, out = _invoke("backtest", "--config", str(config), "--experiments-dir", str(experiments))
    assert code == 0, out
    assert "ema_trend" in out
    assert "B&H BTC" in out
    assert "Equiponderado" in out
    assert "registrado: EXP-0001" in out

    run_dir = next(experiments.joinpath("runs").glob("EXP-0001-*"))
    for name in (
        "config.yaml",
        "metrics.json",
        "trades.csv",
        "equity.csv",
        "equity.png",
        "REPORT.md",
    ):
        assert (run_dir / name).exists(), name
    payload = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert payload["kind"] == "EXP"
    assert payload["metrics"]["bars"] > 1000
    assert "B&H BTC" in payload["benchmarks"]
    assert payload["meta"]["include_holdout"] is False
    report = (run_dir / "REPORT.md").read_text(encoding="utf-8")
    assert "- **Veredicto**: pendiente" in report
    assert "## Métricas" in report
    registry = (experiments / "REGISTRY.md").read_text(encoding="utf-8")
    assert "| EXP-0001" in registry  # con `*` si el árbol de git está sucio durante el test

    # misma config -> mismo bloque metrics (reproducibilidad), nuevo id
    code, out = _invoke("backtest", "--config", str(config), "--experiments-dir", str(experiments))
    assert code == 0, out
    assert "registrado: EXP-0002" in out
    second = json.loads(
        next(experiments.joinpath("runs").glob("EXP-0002-*/metrics.json")).read_text(
            encoding="utf-8"
        )
    )
    assert second["metrics"] == payload["metrics"]
    assert second["meta"]["data_hash"] == payload["meta"]["data_hash"]


def test_backtest_overrides_and_no_register(workspace: dict[str, Path]) -> None:
    config, experiments = workspace["config"], workspace["experiments"]
    code, out = _invoke(
        "backtest",
        "--config",
        str(config),
        "--experiments-dir",
        str(experiments),
        "--pairs",
        "BTC/USDT",
        "--set",
        "risk.max_positions=1",
        "--from",
        "2023-06-01",
        "--to",
        "2023-09-01",
        "--no-register",
    )
    assert code == 0, out
    assert "sin registrar" in out
    assert "Equiponderado" not in out  # un solo par: sin benchmark equiponderado
    assert not list(experiments.joinpath("runs").glob("EXP-0003-*"))


def test_benchmark_commands_register(workspace: dict[str, Path]) -> None:
    config, experiments = workspace["config"], workspace["experiments"]
    code, out = _invoke(
        "benchmark",
        "--config",
        str(config),
        "--experiments-dir",
        str(experiments),
        "--kind",
        "bh_btc",
    )
    assert code == 0, out
    assert "registrado: EXP-0003" in out
    code, out = _invoke(
        "benchmark",
        "--config",
        str(config),
        "--experiments-dir",
        str(experiments),
        "--kind",
        "equal_weight",
    )
    assert code == 0, out
    assert "registrado: EXP-0004" in out
    code, out = _invoke("benchmark", "--config", str(config), "--kind", "nope")
    assert code == 1
    assert "kind desconocido" in out


def test_experiments_commands(workspace: dict[str, Path]) -> None:
    experiments = workspace["experiments"]
    code, out = _invoke("experiments", "list", "--experiments-dir", str(experiments))
    assert code == 0, out
    assert "EXP-0001" in out
    assert "EXP-0004" in out
    code, out = _invoke("experiments", "show", "EXP-0001", "--experiments-dir", str(experiments))
    assert code == 0, out
    assert "veredicto: pendiente" in out
    assert "B&H BTC" in out
    code, out = _invoke(
        "experiments", "compare", "EXP-0001", "EXP-0003", "--experiments-dir", str(experiments)
    )
    assert code == 0, out
    assert "EXP-0003" in out
    code, out = _invoke("experiments", "show", "EXP-9999", "--experiments-dir", str(experiments))
    assert code == 1
    assert "no existe" in out
    code, out = _invoke("experiments", "sync", "--experiments-dir", str(experiments))
    assert code == 0, out
    assert "4 corridas" in out


def test_backtest_missing_config_fails_cleanly(tmp_path: Path) -> None:
    code, out = _invoke("backtest", "--config", str(tmp_path / "nope.yaml"), "--no-register")
    assert code == 1
    assert "no existe" in out
