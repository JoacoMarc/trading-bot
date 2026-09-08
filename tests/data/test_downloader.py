"""Downloader: descarta la vela en formación, incremental inclusive, idempotente, backfill."""

from __future__ import annotations

from pathlib import Path

import ccxt
import pytest

from tests.exchange.fake_ccxt import FakeCcxt, binance_market, ohlcv_rows
from tests.factories import BTC, ETH, H4_MS, T0, make_series
from tradingbot.data import Downloader, Gap, ParquetStore, closed_cutoff_ms, drop_forming
from tradingbot.domain import ExchangeUnavailable, Timeframe
from tradingbot.exchange import BinanceExchange


def build(
    tmp_path: Path, n: int, now_offset_ms: int, start: int = T0
) -> tuple[FakeCcxt, BinanceExchange, ParquetStore, Downloader]:
    """Exchange falso con `n` velas desde `start`; hora del servidor = fin de la última + offset."""
    server_now = start + n * H4_MS + now_offset_ms
    client = FakeCcxt(
        markets={"BTC/USDT": binance_market("BTC"), "ETH/USDT": binance_market("ETH")},
        candles={
            ("BTC/USDT", "4h"): ohlcv_rows(start, H4_MS, n),
            ("ETH/USDT", "4h"): ohlcv_rows(start, H4_MS, n, base_price=50.0),
        },
        server_time_ms=server_now,
    )
    exchange = BinanceExchange(client, local_now_ms=lambda: server_now, sleep=lambda _: None)
    store = ParquetStore(tmp_path / "data")
    return client, exchange, store, Downloader(exchange, store, close_safety_ms=0)


def test_closed_cutoff_and_drop_forming() -> None:
    # now = mitad de la vela 3 → cerradas 0,1,2; la 3 está en formación.
    now = T0 + 3 * H4_MS + H4_MS // 2
    assert closed_cutoff_ms(Timeframe.H4, now) == T0 + 3 * H4_MS
    kept, dropped = drop_forming(make_series(n=5), Timeframe.H4, now)
    assert [c.open_time for c in kept] == [T0, T0 + H4_MS, T0 + 2 * H4_MS]
    assert dropped == 2  # la 3 (en formación) y la 4 (futuro espurio)
    # Exactamente al cierre de la vela 2, la 2 ya cuenta como cerrada.
    kept, _ = drop_forming(make_series(n=5), Timeframe.H4, T0 + 3 * H4_MS)
    assert len(kept) == 3


def test_download_discards_forming_candle(tmp_path: Path) -> None:
    # 10 velas en el exchange; la última (índice 9) está en formación: now = su open + 1 h.
    _, _, store, downloader = build(tmp_path, n=10, now_offset_ms=-3 * 3_600_000)
    result = downloader.download(BTC, Timeframe.H4, T0)
    assert result.fetched == 9
    assert result.added == 9
    assert result.last_open_time == T0 + 8 * H4_MS
    # El corte se pide al exchange (until = primera vela no cerrada); el filtro defensivo no actúa.
    assert result.until_ms == T0 + 9 * H4_MS
    assert result.discarded_forming == 0
    assert store.info(BTC, Timeframe.H4) is not None
    assert store.info(BTC, Timeframe.H4).rows == 9  # type: ignore[union-attr]


def test_download_is_incremental_and_idempotent(tmp_path: Path) -> None:
    client, _, _, downloader = build(tmp_path, n=10, now_offset_ms=0)
    first = downloader.download(BTC, Timeframe.H4, T0)
    assert (first.added, first.updated, first.total_rows) == (10, 0, 10)

    second = downloader.download(BTC, Timeframe.H4, T0)
    assert (second.added, second.updated, second.total_rows) == (0, 0, 10)
    assert not second.changed
    # La segunda corrida re-pide desde la última vela guardada, inclusive.
    last_since = [c[1][2] for c in client.calls if c[0] == "klines"][-1]
    assert last_since == T0 + 9 * H4_MS
    assert second.fetched == 1


def test_download_extends_when_new_candles_close(tmp_path: Path) -> None:
    client, exchange, store, downloader = build(tmp_path, n=10, now_offset_ms=0)
    downloader.download(BTC, Timeframe.H4, T0)
    # Pasan 3 velas más; la última guardada llega "corregida" con otro volumen.
    client.candles[("BTC/USDT", "4h")] = ohlcv_rows(T0, H4_MS, 13)
    client.candles[("BTC/USDT", "4h")][9][5] = 4242.0
    client.server_time_ms = T0 + 13 * H4_MS
    exchange.time_offset_ms(force=True)
    result = downloader.download(BTC, Timeframe.H4, T0)
    assert (result.added, result.updated, result.total_rows) == (3, 1, 13)
    assert str(store.read_candles(BTC, Timeframe.H4)[9].volume) == "4242.00000000"


def test_download_backfills_earlier_history(tmp_path: Path) -> None:
    _, _, store, downloader = build(tmp_path, n=20, now_offset_ms=0)
    downloader.download(BTC, Timeframe.H4, T0 + 10 * H4_MS)
    assert store.info(BTC, Timeframe.H4).rows == 10  # type: ignore[union-attr]
    ranges = downloader.plan_ranges(BTC, Timeframe.H4, T0, T0 + 20 * H4_MS)
    assert ranges == [(T0, T0 + 10 * H4_MS), (T0 + 19 * H4_MS, T0 + 20 * H4_MS)]
    result = downloader.download(BTC, Timeframe.H4, T0)
    assert result.added == 10
    assert result.total_rows == 20
    assert store.info(BTC, Timeframe.H4).first_open_time == T0  # type: ignore[union-attr]


def test_download_respects_until_and_alignment(tmp_path: Path) -> None:
    _, _, _, downloader = build(tmp_path, n=10, now_offset_ms=0)
    result = downloader.download(BTC, Timeframe.H4, T0, until_ms=T0 + 4 * H4_MS)
    assert result.total_rows == 4
    assert result.until_ms == T0 + 4 * H4_MS
    with pytest.raises(ValueError, match="alineado"):
        downloader.download(BTC, Timeframe.H4, T0 + 1)


def test_download_many_is_deterministic(tmp_path: Path) -> None:
    _, _, store, downloader = build(tmp_path, n=6, now_offset_ms=0)
    results = downloader.download_many([ETH, BTC], [Timeframe.H4], T0)
    assert [r.pair for r in results] == [BTC, ETH]
    assert store.list_datasets() == [(BTC, Timeframe.H4), (ETH, Timeframe.H4)]


def test_download_nothing_new_when_store_is_ahead(tmp_path: Path) -> None:
    _, _, _, downloader = build(tmp_path, n=10, now_offset_ms=0)
    downloader.download(BTC, Timeframe.H4, T0)
    # since posterior a lo guardado: se continúa desde la última vela (re-pedida inclusive).
    result = downloader.download(BTC, Timeframe.H4, T0 + 20 * H4_MS)
    assert result.fetched == 1
    assert not result.changed
    assert result.total_rows == 10


# --------------------------------------------------------------------------- revisión Fase 2


def test_safety_margin_keeps_just_closed_candle_out(tmp_path: Path) -> None:
    # now = cierre de la vela 9 + 100 ms. Sin margen se guardaría; con 2 s de margen, no.
    client, exchange, store, _ = build(tmp_path, n=10, now_offset_ms=100)
    strict = Downloader(exchange, store, close_safety_ms=2_000)
    result = strict.download(BTC, Timeframe.H4, T0)
    assert result.total_rows == 9
    assert result.until_ms == T0 + 9 * H4_MS
    just_after = T0 + 10 * H4_MS + 100
    assert closed_cutoff_ms(Timeframe.H4, just_after, safety_ms=2_000) == T0 + 9 * H4_MS
    assert (
        closed_cutoff_ms(Timeframe.H4, T0 + 10 * H4_MS + 2_000, safety_ms=2_000) == T0 + 10 * H4_MS
    )
    # Un rato después la vela 9 ya entra.
    client.server_time_ms = T0 + 10 * H4_MS + 5_000
    exchange.time_offset_ms(force=True)
    assert strict.download(BTC, Timeframe.H4, T0).total_rows == 10


def test_later_since_continues_from_last_stored_candle_without_gap(tmp_path: Path) -> None:
    client, exchange, store, downloader = build(tmp_path, n=5, now_offset_ms=0)
    downloader.download(BTC, Timeframe.H4, T0)
    client.candles[("BTC/USDT", "4h")] = ohlcv_rows(T0, H4_MS, 20)
    client.server_time_ms = T0 + 20 * H4_MS
    exchange.time_offset_ms(force=True)
    late_since = T0 + 12 * H4_MS
    assert downloader.plan_ranges(BTC, Timeframe.H4, late_since, T0 + 20 * H4_MS) == [
        (T0 + 4 * H4_MS, T0 + 20 * H4_MS)
    ]
    result = downloader.download(BTC, Timeframe.H4, late_since)
    assert result.total_rows == 20
    info = store.info(BTC, Timeframe.H4)
    assert info is not None
    assert info.missing_rows == 0


def test_progress_is_persisted_when_the_exchange_dies_mid_download(tmp_path: Path) -> None:
    client, exchange, store, _ = build(tmp_path, n=50, now_offset_ms=0)
    downloader = Downloader(exchange, store, page_limit=10, flush_pages=2, close_safety_ms=0)
    client.fail_klines_from = T0 + 30 * H4_MS
    client.klines_failure = ccxt.ExchangeNotAvailable("503")
    with pytest.raises(ExchangeUnavailable):
        downloader.download(BTC, Timeframe.H4, T0)
    info = store.info(BTC, Timeframe.H4)
    assert info is not None
    assert info.rows == 30  # 3 páginas bajadas antes de la caída, todas guardadas
    # Al volver el exchange, la corrida siguiente continúa desde la última guardada.
    client.fail_klines_from = None
    result = downloader.download(BTC, Timeframe.H4, T0)
    assert (result.added, result.total_rows) == (20, 50)
    assert [c[1][2] for c in client.calls if c[0] == "klines"][-1] >= T0 + 29 * H4_MS


def test_fill_gaps_fills_what_the_exchange_has_and_confirms_the_rest(tmp_path: Path) -> None:
    client, _, store, downloader = build(tmp_path, n=20, now_offset_ms=0)
    # Store con dos huecos: [4, 5] y [10, 11]. El exchange tiene el primero pero no el segundo.
    store.write_candles(BTC, Timeframe.H4, make_series(n=20, skip=frozenset({4, 5, 10, 11})))
    client.candles[("BTC/USDT", "4h")] = [
        r for r in ohlcv_rows(T0, H4_MS, 20) if r[0] not in (T0 + 10 * H4_MS, T0 + 11 * H4_MS)
    ]
    gaps = [Gap(T0 + 4 * H4_MS, T0 + 5 * H4_MS), Gap(T0 + 10 * H4_MS, T0 + 11 * H4_MS)]
    results = downloader.fill_gaps(BTC, Timeframe.H4, gaps)
    assert [r.filled for r in results] == [2, 0]
    assert results[1].confirmed_empty
    info = store.info(BTC, Timeframe.H4)
    assert info is not None
    assert (info.rows, info.missing_rows) == (18, 2)
