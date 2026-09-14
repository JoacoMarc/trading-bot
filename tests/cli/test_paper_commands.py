"""`tradingbot paper | status | trades` con exchange falso y archivos temporales."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.factories import BTC
from tests.paper.test_runner import FakePaperExchange, rising_days
from tradingbot.cli import paper_commands
from tradingbot.cli.app import app
from tradingbot.config.settings import BotConfig
from tradingbot.observability import StatusWriter
from tradingbot.paper.runner import PaperExchange, PaperSession, build_paper_session

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
