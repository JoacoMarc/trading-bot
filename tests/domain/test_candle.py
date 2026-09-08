import pytest
from pydantic import ValidationError

from tests.factories import BTC, ETH, H4_MS, T0, d, make_candle
from tradingbot.domain import Bar, Timeframe


def test_candle_properties() -> None:
    candle = make_candle(open="100", high="110", low="90", close="105")
    assert candle.close_time == T0 + H4_MS - 1
    assert candle.is_bullish
    assert candle.price_range == d("20")
    assert not make_candle(open="105", close="100").is_bullish


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"low": "120"}, "low"),
        ({"open": "200"}, "open"),
        ({"close": "50"}, "close"),
        ({"open_time": T0 + 1}, "alineado"),
        ({"volume": "-1"}, "greater than or equal"),
        ({"close": "0"}, "greater than"),
    ],
)
def test_candle_invariants(kwargs: dict[str, object], match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        make_candle(**kwargs)  # type: ignore[arg-type]


def test_candle_is_frozen() -> None:
    candle = make_candle()
    with pytest.raises(ValidationError):
        candle.close = d("1")  # type: ignore[misc]


def test_bar_from_candles_sorted_and_lookup() -> None:
    eth, btc = make_candle(pair=ETH, close="95"), make_candle(pair=BTC)
    bar = Bar.from_candles([eth, btc])
    assert bar.pairs == (BTC, ETH)
    assert [c.pair for c in bar.iter_candles()] == [BTC, ETH]
    assert bar.get(BTC) is btc
    assert bar.get(ETH) is eth
    assert len(bar) == 2
    assert bar.close_time == T0 + H4_MS - 1
    assert bar.timeframe is Timeframe.H4


def test_bar_tolerates_missing_pairs() -> None:
    bar = Bar.from_candles([make_candle(pair=BTC)])
    assert bar.get(ETH) is None


def test_bar_rejects_duplicated_pair() -> None:
    with pytest.raises(ValueError, match=r"duplicadas.*BTC/USDT"):
        Bar.from_candles([make_candle(pair=BTC), make_candle(pair=BTC, close="100")])


def test_bar_rejects_inconsistent_candles() -> None:
    with pytest.raises(ValueError, match="al menos una vela"):
        Bar.from_candles([])
    with pytest.raises(ValidationError, match="abre en"):
        Bar.from_candles([make_candle(pair=BTC), make_candle(pair=ETH, open_time=T0 + H4_MS)])
    with pytest.raises(ValidationError, match="Bar en"):
        Bar(
            timeframe=Timeframe.H4,
            open_time=T0,
            candles={BTC: make_candle(timeframe=Timeframe.H1, open_time=T0)},
        )
    with pytest.raises(ValidationError, match="no coincide"):
        Bar(timeframe=Timeframe.H4, open_time=T0, candles={ETH: make_candle(pair=BTC)})
    with pytest.raises(ValidationError, match="al menos una vela"):
        Bar(timeframe=Timeframe.H4, open_time=T0, candles={})
