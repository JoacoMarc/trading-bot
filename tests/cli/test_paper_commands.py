"""`tradingbot paper | status | trades` con exchange falso y archivos temporales."""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.factories import BTC
from tests.paper.test_runner import FakePaperExchange, rising_days
from tradingbot.backtest.runner import run_backtest
from tradingbot.cli import paper_commands
from tradingbot.cli.app import app
from tradingbot.config.settings import BotConfig
from tradingbot.observability import StatusWriter
from tradingbot.paper.runner import PaperExchange, PaperSession, build_paper_session
from tradingbot.persistence import SqliteStore
from tradingbot.validation.parity import backtest_config_for

runner = CliRunner()

PAPER_YAML = """
mode: paper
strategy:
  name: regime_bh
  timeframe: 4h
  pairs: [BTC/USDT]
  params:
    sma_days: 3
    momentum_days: 2
risk:
  sizing_mode: fraction
  position_fraction: 0.5
  max_positions: 1
  daily_loss_limit_pct: null
  max_drawdown_pct: null
  kill_switch_file: {root}/logs/STOP
execution:
  slippage_bps: 0
persistence:
  db_dir: {root}/db
  logs_dir: {root}/logs
data:
  data_dir: {root}/data
"""


def test_paper_runs_max_bars_then_status_and_trades(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candles = rising_days(8)
    exchange = FakePaperExchange({BTC: candles}, now_ms=candles[30].open_time + 300_000)
    exchange.last[BTC] = "105"
    monkeypatch.setattr(paper_commands, "exchange_factory", lambda _cfg: exchange)
    # El feed y el watcher duermen con el reloj falso: sin esto la CLI esperaría 4 h reales.
    monkeypatch.setattr(
        paper_commands,
        "build_paper_session",
        lambda cfg, ex, **kw: _real_build(cfg, ex, sleep=exchange.sleep, **kw),
    )
    config = tmp_path / "paper.yaml"
    config.write_text(PAPER_YAML.format(root=tmp_path.as_posix()), encoding="utf-8")

    result = runner.invoke(app, ["paper", "--config", str(config), "--max-bars", "2"])
    assert result.exit_code == 0, result.output
    assert "arranque limpio" in result.output
    assert "paper detenido tras 2 velas" in result.output

    status_file = tmp_path / "logs" / "status.json"
    data = json.loads(status_file.read_text(encoding="utf-8"))
    assert data["phase"] == "detenido"
    # `status` lee el archivo; el heartbeat es del reloj falso (2023): está vencido.
    result = runner.invoke(app, ["status", "--file", str(status_file)])
    assert result.exit_code == 1
    assert "VENCIDO" in result.output
    assert "BTC/USDT" in result.output
    result = runner.invoke(app, ["status", "--file", str(status_file), "--check"])
    assert result.exit_code == 1
    # Un heartbeat fresco pasa el check.
    StatusWriter(status_file).write(
        {**data, "timeframe_ms": 4 * 3_600_000}, heartbeat_ts=int(time.time() * 1000)
    )
    result = runner.invoke(app, ["status", "--file", str(status_file), "--check"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("OK")

    result = runner.invoke(app, ["trades", "--db", str(tmp_path / "db" / "paper.db")])
    assert result.exit_code == 0, result.output
    assert "sin trades cerrados" in result.output
    assert "abiertas: BTC/USDT" in result.output


def _real_build(cfg: BotConfig, ex: PaperExchange, **kw: Any) -> PaperSession:
    return build_paper_session(cfg, ex, **kw)


def test_telegram_test_requires_the_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)  # sin archivo de entorno del repo
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    config = tmp_path / "paper.yaml"
    config.write_text(PAPER_YAML.format(root=tmp_path.as_posix()), encoding="utf-8")
    result = runner.invoke(app, ["telegram-test", "--config", str(config), "--seconds", "1"])
    assert result.exit_code == 1
    assert "TELEGRAM_BOT_TOKEN" in result.output


def test_status_without_file_and_wrong_mode(tmp_path: Path) -> None:
    result = runner.invoke(app, ["status", "--file", str(tmp_path / "nada.json")])
    assert result.exit_code == 1
    assert "sin status" in result.output
    config = tmp_path / "bt.yaml"
    config.write_text(
        PAPER_YAML.format(root=tmp_path.as_posix()).replace("mode: paper", "mode: backtest"),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["paper", "--config", str(config), "--max-bars", "1"])
    assert result.exit_code == 1
    assert "mode: paper" in result.output
    result = runner.invoke(app, ["trades", "--db", str(tmp_path / "db" / "nada.db")])
    assert result.exit_code == 1


def test_parity_of_a_paper_db_seeded_from_the_same_backtest(
    workspace: dict[str, Path], tmp_path: Path
) -> None:
    # "Paper" = las órdenes y fills del backtest de referencia: la paridad tiene que dar 100 %.
    config = BotConfig.load(workspace["config"])
    start, end = date(2023, 4, 1), date(2023, 7, 1)
    reference = run_backtest(backtest_config_for(config, start, end), with_benchmarks=False)
    db = tmp_path / "paper.db"
    with SqliteStore(db) as store:
        for order in reference.engine_result.store.orders():
            store.save_order(order)
        for fill in reference.engine_result.store.fills():
            store.save_fill(fill)
        for trade in reference.engine_result.store.trades():
            store.save_trade(trade)
    assert reference.metrics.trades > 0
    experiments = tmp_path / "experiments"
    result = runner.invoke(
        app,
        [
            "parity",
            "--config",
            str(workspace["config"]),
            "--db",
            str(db),
            "--from",
            start.isoformat(),
            "--to",
            end.isoformat(),
            "--experiments-dir",
            str(experiments),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "paridad 100.0 % de senales coincidentes" in result.output
    assert "desvio medio del fill 0.00 bps" in result.output
    assert "gate 2 (paridad): aprobado" in result.output
    assert "registrado: PAR-0001" in result.output
    run_dir = next(experiments.joinpath("runs").glob("PAR-0001-*"))
    payload = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert payload["kind"] == "PAR"
    assert payload["metrics"]["signal_match_rate"] == 1.0
    assert payload["metrics"]["gate2_parity"] is True
    report = (run_dir / "REPORT.md").read_text(encoding="utf-8")
    assert "Gate 2 (paridad): **aprobado**" in report
    assert "- **Veredicto**: pendiente" in report
    assert "| PAR-0001" in (experiments / "REGISTRY.md").read_text(encoding="utf-8")

    # Sin rango o sin DB: error claro.
    result = runner.invoke(app, ["parity", "--config", str(workspace["config"]), "--db", str(db)])
    assert result.exit_code == 1
    assert "--from y --to" in result.output


def test_telegram_send_only_never_receives_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tradingbot.notify import telegram

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:dummy")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    config = tmp_path / "paper.yaml"
    config.write_text(PAPER_YAML.format(root=tmp_path.as_posix()), encoding="utf-8")
    received: list[bool] = []

    async def fake_smoke(
        _token: str, _chat: str, **kwargs: Any
    ) -> tuple[dict[str, Any], list[str]]:
        received.append(kwargs["receive_commands"])
        assert kwargs["prefix"] == "[PAPER | regime_bh] "
        return {"sent": 1, "errors": 0, "commands": 0}, []

    monkeypatch.setattr(telegram, "run_smoke_test", fake_smoke)
    result = runner.invoke(app, ["telegram-test", "--config", str(config), "--send-only"])
    assert result.exit_code == 0, result.output
    assert received == [False]
    assert "no llego" not in result.output
