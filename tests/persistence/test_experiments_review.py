"""Registro: reintento ante colisión de id y marca de árbol sucio en el REGISTRY."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from tests.persistence.test_experiments import _artifacts, _meta
from tradingbot.backtest.metrics import compute_metrics
from tradingbot.backtest.runner import RunPayload, register_payload
from tradingbot.persistence.experiments import write_run


def test_register_payload_retries_when_id_is_taken(tmp_path: Path) -> None:
    experiments = tmp_path / "experiments"
    (experiments / "runs" / "EXP-0001-ocupado").mkdir(parents=True)  # sin metrics.json
    equity = [(1_704_067_200_000 + i * 3_600_000, Decimal(10_000) + i) for i in range(3)]
    metrics = compute_metrics(equity, [False, True, True], [], [])
    payload = RunPayload(
        label="prueba",
        title="Prueba",
        strategy_name="ema_trend",
        spec_path=None,
        params={"a": 1},
        config_dump={"mode": "backtest"},
        metrics=metrics,
        benchmarks={},
        equity=equity,
        benchmark_equities={},
        trades=(),
        fills=(),
        events=(),
        data_line="datos",
        costs_line="costos",
        risk_line="riesgo",
        meta=_meta(),
    )
    # `next_run_id` ve EXP-0001 ocupado y salta a 0002 sin fallar
    run_dir = register_payload(payload, experiments)
    assert run_dir.name.startswith("EXP-0002-")
    assert (run_dir / "equity.png").exists()


def test_registry_marks_dirty_runs(tmp_path: Path) -> None:
    experiments = tmp_path / "experiments"
    dirty = replace(_artifacts("EXP-0001"), meta=replace(_meta(), git_dirty=True))
    write_run(experiments, dirty)
    registry = (experiments / "REGISTRY.md").read_text(encoding="utf-8")
    assert "| EXP-0001* |" in registry
