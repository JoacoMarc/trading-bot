import pytest
from hypothesis import given
from hypothesis import strategies as st

from tradingbot.domain import Timeframe

ALL = list(Timeframe)


def test_durations() -> None:
    assert Timeframe.M1.ms == 60_000
    assert Timeframe.H1.ms == 3_600_000
    assert Timeframe.H4.ms == 4 * 3_600_000
    assert Timeframe.D1.ms == 86_400_000
    assert Timeframe.H4.to_ms() == Timeframe.H4.ms


def test_candles_per_day() -> None:
    assert Timeframe.H4.candles_per_day() == 6
    assert Timeframe.M1.candles_per_day() == 1440
    assert Timeframe.D1.candles_per_day() == 1


@pytest.mark.parametrize(
    ("text", "expected"), [("4h", Timeframe.H4), ("H4", Timeframe.H4), (" 1m ", Timeframe.M1)]
)
def test_parse(text: str, expected: Timeframe) -> None:
    assert Timeframe.parse(text) is expected


def test_parse_invalid() -> None:
    with pytest.raises(ValueError, match="timeframe inválido"):
        Timeframe.parse("7h")


def test_floor_and_close_concrete() -> None:
    tf = Timeframe.H4
    open_time = 1_700_006_400_000  # 2023-11-15 00:00 UTC, alineado a 4h
    assert tf.is_aligned(open_time)
    assert tf.floor(open_time + 1) == open_time
    assert tf.floor(open_time + tf.ms - 1) == open_time
    assert tf.close_time(open_time) == open_time + tf.ms - 1
    assert tf.next_close(open_time + 5) == open_time + tf.ms


def test_alignment_matches_binance_epoch_grid() -> None:
    midnight_2024 = 1_704_067_200_000  # 2024-01-01T00:00:00Z
    assert Timeframe.D1.is_aligned(midnight_2024)
    assert Timeframe.H4.is_aligned(midnight_2024)
    assert not Timeframe.H4.is_aligned(midnight_2024 + Timeframe.H1.ms)
    assert not Timeframe.D1.is_aligned(midnight_2024 + Timeframe.H4.ms)


def test_is_closed_uses_exchange_boundary() -> None:
    tf = Timeframe.H1
    assert not tf.is_closed(0, tf.ms - 1)
    assert tf.is_closed(0, tf.ms)


def test_unaligned_and_negative_raise() -> None:
    with pytest.raises(ValueError, match="no está alineado"):
        Timeframe.H4.close_time(1)
    with pytest.raises(ValueError, match="no está alineado"):
        Timeframe.H4.is_closed(1, 10)
    with pytest.raises(ValueError, match="negativo"):
        Timeframe.H4.floor(-1)
    assert not Timeframe.H4.is_aligned(-Timeframe.H4.ms)


@given(ts=st.integers(min_value=0, max_value=4_102_444_800_000), tf=st.sampled_from(ALL))
def test_floor_properties(ts: int, tf: Timeframe) -> None:
    start = tf.floor(ts)
    assert tf.is_aligned(start)
    assert start <= ts < start + tf.ms
    assert tf.next_close(ts) == start + tf.ms
    assert not tf.is_closed(start, ts)
    assert tf.is_closed(start, tf.next_close(ts))
    assert tf.close_time(start) == tf.next_close(ts) - 1
