"""Comandos de datos de la CLI con exchange falso inyectado."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.exchange.fake_ccxt import FakeCcxt, binance_market, ohlcv_rows
from tests.factories import BTC, ETH, H4_MS, T0
from tradingbot.cli import data_commands
from tradingbot.cli.app import app
from tradingbot.data import ParquetStore
from tradingbot.domain import Timeframe
from tradingbot.exchange import BinanceExchange

runner = CliRunner()
SINCE = "2023-11-14"  # T0 = 2023-11-14 20:00 UTC; el día empieza antes que T0
DAY_MS = 86_400_000


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeCcxt:
    n = 12
    server_now = T0 + n * H4_MS - H4_MS // 2  # la vela 11 está en formación
    client = FakeCcxt(
        markets={
            "BTC/USDT": binance_market("BTC"),
            "ETH/USDT": binance_market("ETH", step="0.00010000"),
        },
        candles={
            ("BTC/USDT", "4h"): ohlcv_rows(T0, H4_MS, n),
            ("BTC/USDT", "1h"): ohlcv_rows(T0, Timeframe.H1.ms, 4 * n),
            ("ETH/USDT", "4h"): ohlcv_rows(T0, H4_MS, n, base_price=50.0),
        },
        server_time_ms=server_now,
    )
    monkeypatch.setattr(
        data_commands,
        "exchange_factory",
        lambda: BinanceExchange(client, local_now_ms=lambda: server_now, sleep=lambda _: None),
    )
    return client


def test_download_data_then_info_and_check(tmp_path: Path, fake: FakeCcxt) -> None:
    data_dir = tmp_path / "data"
    result = runner.invoke(
        app,
        [
            "download-data",
            "--data-dir",
            str(data_dir),
            "-p",
            "BTC/USDT,ETH/USDT",
            "-t",
            "4h",
            "--since",
            SINCE,
            "-q",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "BTC/USDT   4h        11       0      11" in result.output
    assert "ETH/USDT   4h        11" in result.output
    store = ParquetStore(data_dir)
    assert store.info(BTC, Timeframe.H4).rows == 11  # type: ignore[union-attr]
    assert (data_dir / "binance" / "markets.json").is_file()
    snapshot = json.loads((data_dir / "binance" / "markets.json").read_text(encoding="utf-8"))
    assert {m["pair"]["base"] for m in snapshot["markets"]} == {"BTC", "ETH"}

    # Idempotente.
    again = runner.invoke(
        app,
        [
            "download-data",
            "--data-dir",
            str(data_dir),
            "-p",
            "BTC/USDT,ETH/USDT",
            "-t",
            "4h",
            "--since",
            SINCE,
            "-q",
        ],
    )
    assert again.exit_code == 0
    assert "BTC/USDT   4h         0       0      11" in again.output

    info = runner.invoke(app, ["data-info", "--data-dir", str(data_dir)])
    assert info.exit_code == 0
    assert "BTC/USDT   4h        11       0" in info.output
    assert "ETH/USDT" in info.output

    check = runner.invoke(
        app,
        [
            "data-check",
            "--data-dir",
            str(data_dir),
            "-p",
            "BTC/USDT,ETH/USDT",
            "-t",
            "4h",
            "--gaps-file",
            str(tmp_path / "gaps.json"),
        ],
    )
    assert check.exit_code == 0, check.output
    assert "[OK  ] BTC/USDT   4h   11 velas" in check.output


def test_download_data_rejects_unknown_pair(tmp_path: Path, fake: FakeCcxt) -> None:
    result = runner.invoke(
        app, ["download-data", "--data-dir", str(tmp_path), "-p", "SOL/USDT", "--since", SINCE]
    )
    assert result.exit_code == 1
    assert "no listados" in result.output


def test_download_data_rejects_bad_inputs(tmp_path: Path, fake: FakeCcxt) -> None:
    assert runner.invoke(app, ["download-data", "--since", "ayer"]).exit_code != 0
    assert runner.invoke(app, ["download-data", "-t", "7h"]).exit_code != 0
    assert runner.invoke(app, ["download-data", "-p", "BTC/EUR"]).exit_code != 0


def test_data_check_register_fills_or_confirms_gaps(tmp_path: Path, fake: FakeCcxt) -> None:
    from tests.factories import make_series

    data_dir = tmp_path / "data"
    store = ParquetStore(data_dir)
    # Dos huecos: [4, 5] existe en el exchange (se recupera); [8] no (se registra como real).
    store.write_candles(BTC, Timeframe.H4, make_series(n=11, skip=frozenset({4, 5, 8})))
    fake.candles[("BTC/USDT", "4h")] = [
        r for r in fake.candles[("BTC/USDT", "4h")] if r[0] != T0 + 8 * H4_MS
    ]
    gaps_file = tmp_path / "gaps.json"
    args = [
        "data-check",
        "--data-dir",
        str(data_dir),
        "-p",
        "BTC/USDT",
        "-t",
        "4h,1h",
        "--gaps-file",
        str(gaps_file),
    ]

    failing = runner.invoke(app, args)
    assert failing.exit_code == 1
    assert "[FAIL] BTC/USDT   4h" in failing.output
    assert failing.output.count("hueco no registrado") == 2
    assert "[SKIP] BTC/USDT   1h" in failing.output

    registered = runner.invoke(app, [*args, "--register"])
    assert registered.exit_code == 0, registered.output
    assert "1 huecos confirmados" in registered.output
    assert "2 velas recuperadas" in registered.output
    payload = json.loads(gaps_file.read_text(encoding="utf-8"))
    assert len(payload["gaps"]) == 1
    assert payload["gaps"][0]["start_ms"] == T0 + 8 * H4_MS
    assert "confirmado vacío" in payload["gaps"][0]["note"]
    assert store.info(BTC, Timeframe.H4).rows == 10  # type: ignore[union-attr]

    clean = runner.invoke(app, args)
    assert clean.exit_code == 0, clean.output
    assert "1 huecos registrados" in clean.output


def test_data_info_without_data(tmp_path: Path) -> None:
    result = runner.invoke(app, ["data-info", "--data-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "sin datos" in result.output


def test_data_markets_from_snapshot_and_refresh(tmp_path: Path, fake: FakeCcxt) -> None:
    result = runner.invoke(
        app, ["data-markets", "--data-dir", str(tmp_path), "-p", "BTC/USDT,SOL/USDT"]
    )
    assert result.exit_code == 0, result.output
    assert "BTC/USDT           0.01      0.00001" in result.output
    assert "SOL/USDT" in result.output

    refreshed = runner.invoke(
        app, ["data-markets", "--data-dir", str(tmp_path), "-p", "BTC/USDT,ETH/USDT", "--refresh"]
    )
    assert refreshed.exit_code == 0, refreshed.output
    assert "ETH/USDT           0.01       0.0001" in refreshed.output
    assert (tmp_path / "binance" / "markets.json").is_file()
    assert fake.count("load_markets") == 1

    # Sin --refresh, ahora se lee la copia local en vez del snapshot empaquetado.
    local = runner.invoke(app, ["data-markets", "--data-dir", str(tmp_path), "-p", "ETH/USDT"])
    assert "ETH/USDT           0.01       0.0001" in local.output
    assert "SOL/USDT" not in local.output


def test_data_markets_refresh_fails_for_unlisted_pair(tmp_path: Path, fake: FakeCcxt) -> None:
    result = runner.invoke(
        app, ["data-markets", "--data-dir", str(tmp_path), "-p", "SOL/USDT", "--refresh"]
    )
    assert result.exit_code == 1
    assert "no listados" in result.output


def test_split_accepts_repeated_and_comma_separated() -> None:
    assert data_commands._split(["A,B", "C", " D E "]) == ["A", "B", "C", "D", "E"]
    _, pairs, tfs = data_commands._resolve(None, ["ETH/USDT", "BTC/USDT"], ["4h", "1h"])
    assert pairs == (BTC, ETH)
    assert tfs == (Timeframe.H1, Timeframe.H4)
