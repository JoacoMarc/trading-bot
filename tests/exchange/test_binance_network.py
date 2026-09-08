"""Contra endpoints públicos de Binance (sin claves). Solo con `uv run pytest -m network`."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.factories import BTC
from tradingbot.domain import Timeframe
from tradingbot.exchange import BinanceExchange, load_markets_snapshot

pytestmark = pytest.mark.network


@pytest.fixture(scope="module")
def exchange() -> BinanceExchange:
    return BinanceExchange.create()


def test_real_markets_match_snapshot_universe(exchange: BinanceExchange) -> None:
    markets = exchange.load_markets()
    snapshot = load_markets_snapshot()
    for market in snapshot.markets:
        real = markets[market.pair]
        assert real.tick_size == market.tick_size, market.pair
        assert real.step_size == market.step_size, market.pair
        assert real.min_notional == market.min_notional, market.pair
    assert exchange.rate_limits().request_weight_per_minute >= 1200


def test_real_ohlcv_first_2023_candles(exchange: BinanceExchange) -> None:
    since = 1_672_531_200_000  # 2023-01-01 00:00 UTC
    candles = exchange.fetch_ohlcv(BTC, Timeframe.H4, since, since + 3 * Timeframe.H4.ms)
    assert [c.open_time for c in candles] == [since + i * Timeframe.H4.ms for i in range(3)]
    assert candles[0].open == Decimal("16541.77")


def test_real_clock_offset_is_small(exchange: BinanceExchange) -> None:
    assert abs(exchange.time_offset_ms()) < 5_000
