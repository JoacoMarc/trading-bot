"""Tests de humo de la Fase 0: CLI y chequeos de doctor sin red."""

import pytest
from typer.testing import CliRunner

from tradingbot import __version__
from tradingbot.cli.app import app
from tradingbot.doctor import check_binance, check_env, check_python, run_all

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "doctor" in result.stdout


def test_check_python_minimum() -> None:
    assert check_python((3, 12)).ok
    assert check_python((3, 13)).ok
    assert not check_python((3, 11)).ok


def test_check_env_never_leaks_values() -> None:
    result = check_env({"BINANCE_API_KEY": "super-secret", "ANTHROPIC_API_KEY": ""})
    assert result.ok
    assert "BINANCE_API_KEY" in result.detail
    assert "super-secret" not in result.detail


def test_clock_offset_within_limit() -> None:
    local = iter([1_000, 1_200])
    results = check_binance(fetch_server_time_ms=lambda: 1_100 + 300, now_ms=lambda: next(local))
    connectivity, clock = results
    assert connectivity.ok
    assert clock.ok
    assert "+300 ms" in clock.detail


def test_clock_offset_beyond_limit_fails() -> None:
    local = iter([1_000, 1_000])
    results = check_binance(fetch_server_time_ms=lambda: 1_000 - 5_000, now_ms=lambda: next(local))
    assert results[0].ok
    assert not results[1].ok


def test_connectivity_failure_reports_without_raising() -> None:
    def boom() -> int:
        raise ConnectionError("dns")

    results = check_binance(fetch_server_time_ms=boom)
    assert len(results) == 1
    assert not results[0].ok
    assert "ConnectionError" in results[0].detail


@pytest.mark.network
def test_doctor_against_real_binance() -> None:
    results = run_all()
    by_name = {r.name: r for r in results}
    assert by_name["binance"].ok, by_name["binance"].detail
