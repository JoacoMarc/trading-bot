import pytest
from pydantic import ValidationError

from tradingbot.domain import Pair


@pytest.mark.parametrize(
    "text", ["BTC/USDT", "btc/usdt", "BTC-USDT", "BTC_USDT", "BTCUSDT", " btcusdt "]
)
def test_parse_variants(text: str) -> None:
    pair = Pair.parse(text)
    assert pair.base == "BTC"
    assert pair.quote == "USDT"
    assert pair.symbol == "BTC/USDT"
    assert pair.binance_symbol == "BTCUSDT"
    assert str(pair) == "BTC/USDT"


def test_single_letter_assets_exist_on_binance() -> None:
    pair = Pair.parse("T/USDT")
    assert pair.base == "T"
    assert pair.binance_symbol == "TUSDT"
    assert Pair.parse("TUSDT") == pair


def test_parse_unknown_quote_fails() -> None:
    with pytest.raises(ValueError, match="no soportado en v1"):
        Pair.parse("BTC/BUSD")
    with pytest.raises(ValueError, match="no se puede interpretar"):
        Pair.parse("BTCBUSD")


def test_invalid_assets() -> None:
    with pytest.raises(ValidationError):
        Pair(base="", quote="USDT")
    with pytest.raises(ValidationError):
        Pair(base="A" * 13, quote="USDT")
    with pytest.raises(ValidationError):
        Pair(base="BTC$", quote="USDT")
    with pytest.raises(ValidationError, match="iguales"):
        Pair(base="USDT", quote="USDT")


def test_hashable_and_sortable() -> None:
    btc, eth = Pair.parse("BTC/USDT"), Pair.parse("ETH/USDT")
    assert {btc: 1}[Pair.parse("btcusdt")] == 1
    assert btc == Pair(base="BTC", quote="USDT")
    assert sorted([eth, btc]) == [btc, eth]
    assert btc < eth
