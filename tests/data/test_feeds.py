"""HistoricalFeed: orden, warmup, pares faltantes y límites del rango."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.factories import BTC, ETH, H4_MS, T0, make_series
from tradingbot.data import HistoricalFeed, MarketFeed, ParquetStore
from tradingbot.domain import Bar, DataError, InsufficientWarmup, Timeframe


@pytest.fixture
def store(tmp_path: Path) -> ParquetStore:
    store = ParquetStore(tmp_path / "data")
    store.write_candles(BTC, Timeframe.H4, make_series(n=20))
    # ETH: falta la vela 12 y arranca 5 velas después que BTC.
    store.write_candles(
        ETH, Timeframe.H4, make_series(pair=ETH, start=T0 + 5 * H4_MS, n=15, skip=frozenset({7}))
    )
    return store


async def collect(feed: HistoricalFeed) -> list[Bar]:
    return [bar async for bar in feed]


async def test_emits_bars_in_order_with_missing_pairs(store: ParquetStore) -> None:
    feed = HistoricalFeed(store, [ETH, BTC], Timeframe.H4, T0 + 10 * H4_MS, T0 + 15 * H4_MS)
    assert feed.pairs == (BTC, ETH)
    bars = await collect(feed)
    assert [b.open_time for b in bars] == [T0 + i * H4_MS for i in range(10, 15)]
    assert all(b.timeframe is Timeframe.H4 for b in bars)
    assert bars[0].pairs == (BTC, ETH)
    # ETH salteó el índice 7 de su serie → open_time T0 + 12·4h.
    missing = next(b for b in bars if b.open_time == T0 + 12 * H4_MS)
    assert missing.pairs == (BTC,)
    assert missing.get(ETH) is None
    assert len(feed) == 5
    assert list(feed.iter_bars()) == bars


def test_warmup_is_preloaded_before_start(store: ParquetStore) -> None:
    start = T0 + 10 * H4_MS
    feed = HistoricalFeed(store, [BTC, ETH], Timeframe.H4, start, T0 + 12 * H4_MS, warmup=3)
    assert [c.open_time for c in feed.warmup_candles(BTC)] == [T0 + i * H4_MS for i in (7, 8, 9)]
    warm = feed.warmup_bars()
    assert [b.open_time for b in warm] == [T0 + i * H4_MS for i in (7, 8, 9)]
    assert all(b.pairs == (BTC, ETH) for b in warm)
    assert all(b.open_time < start for b in warm)


def test_insufficient_warmup_fails_fast(store: ParquetStore) -> None:
    # ETH arranca en T0 + 5·4h: para start = T0 + 7·4h solo tiene 2 velas previas.
    with pytest.raises(InsufficientWarmup, match=r"ETH/USDT.*disponibles 2"):
        HistoricalFeed(store, [BTC, ETH], Timeframe.H4, T0 + 7 * H4_MS, T0 + 9 * H4_MS, warmup=3)
    # Sin ETH alcanza.
    HistoricalFeed(store, [BTC], Timeframe.H4, T0 + 7 * H4_MS, T0 + 9 * H4_MS, warmup=3)


def test_no_data_in_range_raises(store: ParquetStore) -> None:
    with pytest.raises(DataError, match="sin velas"):
        HistoricalFeed(store, [BTC], Timeframe.H4, T0 + 100 * H4_MS, T0 + 110 * H4_MS)


def test_start_is_floored_and_end_exclusive(store: ParquetStore) -> None:
    feed = HistoricalFeed(store, [BTC], Timeframe.H4, T0 + H4_MS + 1, T0 + 4 * H4_MS)
    assert feed.start_ms == T0 + H4_MS
    assert feed.open_times == (T0 + H4_MS, T0 + 2 * H4_MS, T0 + 3 * H4_MS)


def test_argument_validation(store: ParquetStore) -> None:
    with pytest.raises(ValueError, match="al menos un par"):
        HistoricalFeed(store, [], Timeframe.H4, T0, T0 + H4_MS)
    with pytest.raises(ValueError, match="posterior"):
        HistoricalFeed(store, [BTC], Timeframe.H4, T0 + H4_MS, T0)
    with pytest.raises(ValueError, match="warmup"):
        HistoricalFeed(store, [BTC], Timeframe.H4, T0, T0 + H4_MS, warmup=-1)


def test_historical_feed_satisfies_the_port(store: ParquetStore) -> None:
    feed: MarketFeed = HistoricalFeed(store, [BTC], Timeframe.H4, T0, T0 + 2 * H4_MS)
    assert feed.timeframe is Timeframe.H4


def test_warmup_survives_gaps_inside_the_window(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path / "data")
    # Hueco de 3 velas (7, 8, 9) justo antes del inicio: el warmup se toma más atrás.
    store.write_candles(BTC, Timeframe.H4, make_series(n=20, skip=frozenset({7, 8, 9})))
    start = T0 + 12 * H4_MS
    feed = HistoricalFeed(store, [BTC], Timeframe.H4, start, T0 + 15 * H4_MS, warmup=5)
    assert [c.open_time for c in feed.warmup_candles(BTC)] == [
        T0 + i * H4_MS for i in (4, 5, 6, 10, 11)
    ]
    assert len(feed.warmup_bars()) == 5
    with pytest.raises(InsufficientWarmup):
        HistoricalFeed(store, [BTC], Timeframe.H4, start, T0 + 15 * H4_MS, warmup=10)
