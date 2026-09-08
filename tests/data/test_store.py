"""ParquetStore: esquema Decimal exacto, upsert idempotente, filtros y validación."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.factories import BTC, ETH, H4_MS, T0, make_candle, make_series
from tradingbot.data import (
    ParquetStore,
    candles_to_frame,
    frame_to_candles,
    read_parquet,
    read_parquet_metadata,
    validate_frame,
)
from tradingbot.domain import Candle, DataError, Timeframe

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ohlcv"


@pytest.fixture
def store(tmp_path: Path) -> ParquetStore:
    return ParquetStore(tmp_path / "data")


def test_paths_follow_exchange_pair_timeframe_layout(store: ParquetStore) -> None:
    path = store.path(BTC, Timeframe.H4)
    assert path == store.root / "binance" / "BTCUSDT" / "4h.parquet"
    assert not store.exists(BTC, Timeframe.H4)
    assert store.read(BTC, Timeframe.H4).empty
    assert store.info(BTC, Timeframe.H4) is None
    assert store.list_datasets() == []


def test_round_trip_preserves_decimals_exactly(store: ParquetStore) -> None:
    candles = [
        make_candle(
            open="27123.45",
            high="27200.1",
            low="27000.00000001",
            close="27150.55",
            volume="12.3456789",
        ),
    ]
    store.write_candles(BTC, Timeframe.H4, candles)
    back = store.read_candles(BTC, Timeframe.H4)
    assert back == candles
    assert back[0].low == Decimal("27000.00000001")
    assert isinstance(store.read(BTC, Timeframe.H4)["close"][0], Decimal)
    meta = read_parquet_metadata(store.path(BTC, Timeframe.H4))
    assert meta == {
        "schema_version": "1",
        "exchange": "binance",
        "pair": "BTC/USDT",
        "timeframe": "4h",
    }


def test_info_and_list_datasets(store: ParquetStore) -> None:
    store.write_candles(BTC, Timeframe.H4, make_series(n=10, skip=frozenset({3, 4})))
    store.write_candles(ETH, Timeframe.H1, make_series(pair=ETH, n=3, timeframe=Timeframe.H1))
    info = store.info(BTC, Timeframe.H4)
    assert info is not None
    assert (info.rows, info.first_open_time, info.last_open_time) == (8, T0, T0 + 9 * H4_MS)
    assert info.expected_rows == 10
    assert info.missing_rows == 2
    assert info.size_bytes > 0
    assert store.list_datasets() == [(BTC, Timeframe.H4), (ETH, Timeframe.H1)]


def test_read_filters_are_inclusive_exclusive(store: ParquetStore) -> None:
    store.write_candles(BTC, Timeframe.H4, make_series(n=10))
    frame = store.read(BTC, Timeframe.H4, start_ms=T0 + 2 * H4_MS, end_ms=T0 + 5 * H4_MS)
    assert frame["open_time"].tolist() == [T0 + i * H4_MS for i in (2, 3, 4)]


def test_upsert_is_idempotent_and_overwrites_changed_rows(store: ParquetStore) -> None:
    first = make_series(n=5)
    result = store.upsert_candles(BTC, Timeframe.H4, first)
    assert (result.added, result.updated, result.unchanged, result.total_rows) == (5, 0, 0, 5)

    again = store.upsert_candles(BTC, Timeframe.H4, first)
    assert (again.added, again.updated, again.unchanged, again.total_rows) == (0, 0, 5, 5)
    assert store.read_candles(BTC, Timeframe.H4) == first

    # Re-pedir la última inclusive con datos corregidos + 2 velas nuevas.
    fixed_last = make_candle(
        open_time=T0 + 4 * H4_MS, open="104", high="130", low="99", close="125", volume="999"
    )
    incoming = [fixed_last, *make_series(start=T0 + 5 * H4_MS, n=2, base_price=105)]
    result = store.upsert_candles(BTC, Timeframe.H4, incoming)
    assert (result.added, result.updated, result.unchanged, result.total_rows) == (2, 1, 0, 7)
    stored = store.read_candles(BTC, Timeframe.H4)
    assert stored[4] == fixed_last
    assert [c.open_time for c in stored] == [T0 + i * H4_MS for i in range(7)]


def test_upsert_backfills_and_dedupes_incoming(store: ParquetStore) -> None:
    store.write_candles(BTC, Timeframe.H4, make_series(start=T0 + 5 * H4_MS, n=3, base_price=105))
    dup = make_series(n=5)
    result = store.upsert_candles(BTC, Timeframe.H4, [*dup, dup[0]])
    assert result.added == 5
    assert result.total_rows == 8
    assert store.upsert_candles(BTC, Timeframe.H4, []).total_rows == 8


def test_write_leaves_no_temp_files(store: ParquetStore) -> None:
    store.write_candles(BTC, Timeframe.H4, make_series(n=3))
    files = list(store.path(BTC, Timeframe.H4).parent.iterdir())
    assert [f.name for f in files] == ["4h.parquet"]


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda f: f.assign(open_time=[T0, T0]), "creciente"),
        (lambda f: f.assign(open_time=[T0 + H4_MS, T0]), "creciente"),
        (lambda f: f.assign(open_time=[T0, T0 + 1]), "alineado"),
        (lambda f: f.assign(low=[Decimal("200"), Decimal("90")]), "OHLC"),
        (lambda f: f.assign(volume=[Decimal("1.123456789"), Decimal("1")]), "decimales"),
        (lambda f: f.assign(close=[1.0, 2.0]), "Decimal"),
        (lambda f: f.drop(columns=["volume"]), "faltan columnas"),
    ],
)
def test_validate_frame_rejects_bad_frames(
    mutation: Callable[[pd.DataFrame], pd.DataFrame], match: str
) -> None:
    frame = candles_to_frame(make_series(n=2))
    with pytest.raises(DataError, match=match):
        validate_frame(mutation(frame), Timeframe.H4)


def test_frame_to_candles_validates_via_domain() -> None:
    frame = candles_to_frame(make_series(n=2))
    bad = frame.copy()
    bad["high"] = pd.Series([Decimal("1"), Decimal("1")], dtype="object")
    with pytest.raises(ValueError, match="high"):
        frame_to_candles(bad, BTC, Timeframe.H4)


def test_synthetic_fixtures_load_and_are_complete() -> None:
    for name in ("synthetic-BTCUSDT-4h-2023.parquet", "synthetic-ETHUSDT-4h-2023.parquet"):
        frame = read_parquet(FIXTURES / name)
        validate_frame(frame, Timeframe.H4)
        assert len(frame) == 2190  # 365 días × 6 velas
        times = frame["open_time"]
        assert times.iloc[0] == 1_672_531_200_000
        assert (times.diff().dropna() == H4_MS).all()


def test_corrupt_parquet_raises_data_error(store: ParquetStore) -> None:
    path = store.path(BTC, Timeframe.H4)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not parquet")
    with pytest.raises(DataError, match="no se pudo leer"):
        store.read(BTC, Timeframe.H4)
    with pytest.raises(DataError):
        store.info(BTC, Timeframe.H4)


decimals = st.decimals(min_value=Decimal("0.00000001"), max_value=Decimal("9" * 12), places=8)


@settings(max_examples=40, deadline=None)
@given(prices=st.lists(decimals, min_size=1, max_size=20), volume=decimals)
def test_any_8_decimal_values_survive_the_round_trip(
    tmp_path_factory: pytest.TempPathFactory, prices: list[Decimal], volume: Decimal
) -> None:
    store = ParquetStore(tmp_path_factory.mktemp("h"))
    candles: list[Candle] = []
    for i, price in enumerate(prices):
        candles.append(
            Candle(
                pair=BTC,
                timeframe=Timeframe.H4,
                open_time=T0 + i * H4_MS,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
            )
        )
    store.write_candles(BTC, Timeframe.H4, candles)
    assert store.read_candles(BTC, Timeframe.H4) == candles


def test_empty_frame_has_schema_columns() -> None:
    frame = pd.DataFrame(candles_to_frame([]))
    assert list(frame.columns) == ["open_time", "open", "high", "low", "close", "volume"]
    assert frame.empty
