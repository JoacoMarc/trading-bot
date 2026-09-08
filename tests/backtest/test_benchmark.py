from __future__ import annotations

from decimal import Decimal

import pytest

from tests.engine.fakes import MARKETS, candles_from_prices
from tests.factories import BTC, ETH, d
from tradingbot.backtest import buy_and_hold, equal_weights
from tradingbot.config.models import ExecutionConfig
from tradingbot.domain import DataError


def test_equal_weights() -> None:
    weights = equal_weights([BTC, ETH])
    assert weights[BTC] == weights[ETH]
    assert sum(weights.values(), Decimal(0)) == Decimal(1)
    with pytest.raises(ValueError, match="al menos un par"):
        equal_weights([])


def test_buy_and_hold_two_pairs_exact_accounting() -> None:
    btc = candles_from_prices([("100", "101", "99", "100")] * 3, BTC)
    eth = candles_from_prices([("10", "11", "9", "10")] * 3, ETH)
    result = buy_and_hold(
        "eq",
        {BTC: btc, ETH: eth},
        equal_weights([BTC, ETH]),
        d("10000"),
        ExecutionConfig(),
        MARKETS,
    )
    assert result.name == "eq"
    assert len(result.fills) == 2
    # BTC: 5000 / 100.05 = 49.975012… -> 49.97501 (step 0.00001), fee 0.1 % en base
    btc_fill = next(f for f in result.fills if f.pair == BTC)
    assert btc_fill.price == Decimal("100.05")
    assert btc_fill.qty == Decimal("49.97501")
    assert btc_fill.fee_asset == "BTC"
    eth_fill = next(f for f in result.fills if f.pair == ETH)
    assert eth_fill.price == Decimal("10.01")  # 10 × 1.0005 = 10.005 -> tick 0.01 hacia arriba
    spent = btc_fill.notional + eth_fill.notional
    assert result.leftover_cash == d("10000") - spent
    holdings_value = (btc_fill.qty - btc_fill.fee_amount) * 100 + (
        eth_fill.qty - eth_fill.fee_amount
    ) * 10
    assert len(result.equity) == 4  # punto inicial (antes de comprar) + 3 velas
    assert result.equity[0] == (btc[0].open_time, d("10000"))
    for _, value in result.equity[1:]:
        assert value == result.leftover_cash + holdings_value
    assert result.metrics.trades == 0
    assert result.metrics.exposure == pytest.approx(0.75)
    assert result.metrics.initial_equity == d("10000")
    assert result.metrics.total_return < 0  # slippage + fee con precios planos
    assert result.metrics.total_return > d("-0.003")


def test_buy_and_hold_marks_with_last_close_on_gaps() -> None:
    btc = candles_from_prices(
        [("100", "101", "99", "100"), ("100", "121", "99", "120"), ("100", "121", "99", "120")], BTC
    )
    eth = candles_from_prices([("10", "11", "9", "10")] * 3, ETH)
    del btc[1]  # hueco de BTC
    result = buy_and_hold(
        "eq",
        {BTC: btc, ETH: eth},
        equal_weights([BTC, ETH]),
        d("10000"),
        ExecutionConfig(),
        MARKETS,
    )
    assert len(result.equity) == 4
    assert result.equity[2][1] == result.equity[1][1]  # BTC marcado al último close conocido
    assert result.equity[3][1] > result.equity[2][1]


def test_buy_and_hold_with_bnb_fee_in_quote() -> None:
    btc = candles_from_prices([("100", "101", "99", "100")] * 2, BTC)
    execution = ExecutionConfig(pay_with_bnb=True, slippage_bps=Decimal("0"))
    result = buy_and_hold("bh", {BTC: btc}, {BTC: Decimal(1)}, d("1000"), execution, MARKETS)
    fill = result.fills[0]
    assert fill.fee_asset == "USDT"
    assert fill.price == Decimal("100")
    assert result.leftover_cash >= 0
    assert fill.notional + fill.fee_amount <= d("1000")


def test_buy_and_hold_validation() -> None:
    btc = candles_from_prices([("100", "101", "99", "100")], BTC)
    with pytest.raises(ValueError, match="suman más de 1"):
        buy_and_hold("x", {BTC: btc}, {BTC: Decimal("1.5")}, d("1000"), ExecutionConfig(), MARKETS)
    with pytest.raises(DataError, match="sin velas"):
        buy_and_hold("x", {BTC: []}, {BTC: Decimal(1)}, d("1000"), ExecutionConfig(), MARKETS)
