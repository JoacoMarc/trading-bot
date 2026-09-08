from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbot.domain import DataError
from tradingbot.persistence.experiments import (
    ExperimentMeta,
    RunArtifacts,
    build_meta,
    data_hash,
    load_runs,
    next_run_id,
    params_hash,
    parse_run_id,
    read_verdict,
    render_registry,
    slugify,
    sync_registry,
    write_run,
)


def _meta(strategy: str = "ema_trend") -> ExperimentMeta:
    return ExperimentMeta(
        created_at="2026-09-08T12:00:00+00:00",
        git_sha="abc1234",
        git_dirty=False,
        data_hash="deadbeef0000",
        host="test",
        python="3.12",
        tradingbot_version="0.1.0",
        duration_s=1.5,
        strategy=strategy,
        timeframe="4h",
        pairs=["BTC/USDT", "ETH/USDT"],
        start="2019-08-01",
        end="2025-09-01",
        include_holdout=False,
        params_hash="0123456789",
    )


def _artifacts(
    run_id: str, label: str = "ema_trend-4h", verdict: str = "pendiente"
) -> RunArtifacts:
    report = f"# {run_id}\n\n## Notas y veredicto\n\n- **Veredicto**: {verdict}\n- **Por qué**: x\n"
    return RunArtifacts(
        run_id=run_id,
        kind=run_id.split("-")[0],
        label=label,
        config={"mode": "backtest", "strategy": {"name": "ema_trend"}},
        metrics={"total_return": "0.25", "sharpe": 1.2, "max_drawdown": 0.1, "trades": 42},
        benchmarks={"B&H BTC": {"total_return": "2.0"}},
        meta=_meta(),
        report_md=report,
        trades_csv="pair\n",
        equity_csv="ts,equity\n",
        equity_png=b"\x89PNG",
    )


def test_ids_and_slugs(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    assert next_run_id(runs, "EXP") == "EXP-0001"
    (runs / "EXP-0007-algo").mkdir(parents=True)
    (runs / "WF-0002-otro").mkdir()
    (runs / "basura").mkdir()
    assert next_run_id(runs, "EXP") == "EXP-0008"
    assert next_run_id(runs, "WF") == "WF-0003"
    assert next_run_id(runs, "OPT") == "OPT-0001"
    with pytest.raises(ValueError, match="desconocido"):
        next_run_id(runs, "XYZ")
    assert parse_run_id("EXP-0007-algo") == ("EXP", 7, "algo")
    assert parse_run_id("EXP-0007") == ("EXP", 7, None)
    assert parse_run_id("basura") is None
    assert slugify("Ema Trend v1 / 4h") == "ema-trend-v1-4h"
    assert slugify("!!!") == "run"


def test_hashes(tmp_path: Path) -> None:
    a = tmp_path / "a.parquet"
    b = tmp_path / "b.parquet"
    a.write_bytes(b"123")
    b.write_bytes(b"456")
    first = data_hash([a, b])
    assert first == data_hash([b, a])  # orden estable
    assert len(first) == 12
    b.write_bytes(b"457")
    assert data_hash([a, b]) != first
    assert params_hash({"a": 1, "b": 2}) == params_hash({"b": 2, "a": 1})
    assert params_hash({"a": 1}) != params_hash({"a": 2})


def test_write_run_and_registry(tmp_path: Path) -> None:
    experiments = tmp_path / "experiments"
    run_dir = write_run(experiments, _artifacts("EXP-0001"))
    assert run_dir.name == "EXP-0001-ema_trend-4h"
    for name in (
        "config.yaml",
        "metrics.json",
        "trades.csv",
        "equity.csv",
        "REPORT.md",
        "equity.png",
    ):
        assert (run_dir / name).exists(), name
    payload = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert payload["id"] == "EXP-0001"
    assert payload["metrics"]["trades"] == 42
    assert payload["meta"]["git_sha"] == "abc1234"

    registry = (experiments / "REGISTRY.md").read_text(encoding="utf-8")
    assert "| EXP-0001 | 2026-09-08 | ema_trend | 0123456789 |" in registry
    assert "+25.0 %" in registry
    assert "pendiente" in registry

    with pytest.raises(DataError, match="ya existe"):
        write_run(experiments, _artifacts("EXP-0001"))

    write_run(experiments, _artifacts("EXP-0002", label="ema_trend-1h", verdict="iterar"))
    summaries = load_runs(experiments)
    assert [s.run_id for s in summaries] == ["EXP-0001", "EXP-0002"]
    assert summaries[1].verdict == "iterar"
    assert summaries[1].number == 2
    text = render_registry(summaries)
    assert text.count("| EXP-") == 2
    assert sync_registry(experiments).exists()


def test_read_verdict(tmp_path: Path) -> None:
    report = tmp_path / "REPORT.md"
    assert read_verdict(report) == "pendiente"
    report.write_text("- **Veredicto**: go | no-go | iterar\n", encoding="utf-8")
    assert read_verdict(report) == "pendiente"
    report.write_text("otras cosas\n- **Veredicto**: no-go\n", encoding="utf-8")
    assert read_verdict(report) == "no-go"


def test_build_meta_reads_git_and_data(tmp_path: Path) -> None:
    data = tmp_path / "x.parquet"
    data.write_bytes(b"abc")
    meta = build_meta(
        strategy="ema_trend",
        timeframe="4h",
        pairs=["ETH/USDT", "BTC/USDT"],
        start="2019-08-01",
        end=None,
        include_holdout=False,
        params={"ema_fast": 20},
        data_files=[data],
        duration_s=0.123456,
        root=Path.cwd(),
        extra={"warmup": 1200},
    )
    assert meta.pairs == ["BTC/USDT", "ETH/USDT"]
    assert meta.duration_s == 0.123
    assert meta.data_hash == data_hash([data])
    assert meta.extra == {"warmup": 1200}
    assert meta.git_sha  # 'unknown' o un sha corto
    assert isinstance(meta.git_dirty, bool)
    assert meta.created_at.endswith("+00:00")
