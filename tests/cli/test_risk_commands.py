"""`tradingbot stop | resume`: kill switch por archivo (ADR-0007), sin construir `BotConfig`."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from tradingbot.cli.app import app
from tradingbot.cli.risk_commands import ENV_VAR

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(ENV_VAR, raising=False)


def test_stop_and_resume_default_file(tmp_path: Path) -> None:
    default = tmp_path / "logs" / "STOP"
    result = runner.invoke(app, ["stop"])
    assert result.exit_code == 0, result.output
    assert default.read_text(encoding="utf-8").strip() == "stop"
    result = runner.invoke(app, ["stop", "--flatten"])
    assert result.exit_code == 0, result.output
    assert "flatten" in default.read_text(encoding="utf-8")
    result = runner.invoke(app, ["resume"])
    assert result.exit_code == 0, result.output
    assert not default.exists()
    result = runner.invoke(app, ["resume"])
    assert result.exit_code == 0
    assert "no habia" in result.output


def test_stop_reads_only_the_risk_block_even_for_live_yaml(tmp_path: Path) -> None:
    # Un YAML de modo real exige claves para construir BotConfig; el kill switch no las necesita.
    target = tmp_path / "state" / "HALT"
    config = tmp_path / "real.yaml"
    config.write_text(
        "mode: live\n"
        "strategy:\n  name: ema_trend\n  pairs: [BTC/USDT]\n"
        f"risk:\n  kill_switch_file: {target.as_posix()}\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["stop", "--config", str(config), "--flatten"])
    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8").strip() == "flatten"
    result = runner.invoke(app, ["resume", "--config", str(config)])
    assert result.exit_code == 0, result.output
    assert not target.exists()


def test_stop_without_risk_block_uses_default(tmp_path: Path) -> None:
    config = tmp_path / "min.yaml"
    config.write_text(
        "mode: paper\nstrategy:\n  name: ema_trend\n  pairs: [BTC/USDT]\n", encoding="utf-8"
    )
    result = runner.invoke(app, ["stop", "--config", str(config)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "logs" / "STOP").exists()


def test_env_var_wins_over_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from_env = tmp_path / "env" / "STOP"
    config = tmp_path / "cfg.yaml"
    config.write_text(
        f"risk:\n  kill_switch_file: {(tmp_path / 'yaml-STOP').as_posix()}\n", encoding="utf-8"
    )
    monkeypatch.setenv(ENV_VAR, str(from_env))
    result = runner.invoke(app, ["stop", "--config", str(config)])
    assert result.exit_code == 0, result.output
    assert from_env.exists()
    assert not (tmp_path / "yaml-STOP").exists()


def test_errors_are_clean(tmp_path: Path) -> None:
    missing = runner.invoke(app, ["resume", "--config", str(tmp_path / "nope.yaml")])
    assert missing.exit_code == 1
    assert "no existe" in missing.output
    broken = tmp_path / "broken.yaml"
    broken.write_text("risk: [unclosed\n", encoding="utf-8")
    result = runner.invoke(app, ["stop", "--config", str(broken)])
    assert result.exit_code == 1
    assert "no se pudo leer" in result.output
    assert not (tmp_path / "logs" / "STOP").exists()


def test_resume_breaker_writes_the_resume_file(tmp_path: Path) -> None:
    result = runner.invoke(app, ["resume", "--breaker"])
    assert result.exit_code == 0, result.output
    resume_file = tmp_path / "logs" / "RESUME"
    assert resume_file.exists()
    assert "circuit breaker" in result.output
