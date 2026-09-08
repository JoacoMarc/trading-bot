from __future__ import annotations

from decimal import Decimal

import pytest

from tests.factories import BTC, d, make_fill, make_intent
from tradingbot.backtest import compute_metrics, max_drawdown
from tradingbot.backtest.metrics import DAY_MS, yearly_breakdown
from tradingbot.domain import ExitReason, Side, Trade, make_client_order_id

D0 = 1_704_067_200_000  # 2024-01-01T00:00Z


def _trade(pnl: str, hours: int = 8, reason: ExitReason = ExitReason.TRAILING) -> Trade:
    qty = d("1")
    entry = d("100")
    return Trade(
        pair=BTC,
        strategy="s",
        qty=qty,
        entry_price=entry,
        entry_time=D0,
        exit_price=entry + d(pnl),
        exit_time=D0 + hours * 3_600_000,
        exit_reason=reason,
        fees_quote=d("0"),
        entry_client_order_id=make_client_order_id("s", BTC, D0, Side.BUY),
        exit_client_order_id=make_client_order_id(
            "s", BTC, D0 + hours * 3_600_000, Side.SELL, reason
        ),
    )


def test_hand_computed_metrics() -> None:
    equity = [
        (D0, d("10000")),
        (D0 + DAY_MS, d("11000")),
        (D0 + 2 * DAY_MS, d("9900")),
        (D0 + 3 * DAY_MS, d("12000")),
    ]
    trades = [_trade("100"), _trade("50", hours=4), _trade("-50", reason=ExitReason.STOP)]
    fills = [make_fill(make_intent(), fee_amount="0.001", price="101", ref_price="100")]
    m = compute_metrics(equity, [True, True, False, True], trades, fills)

    assert m.total_return == Decimal("0.2")
    assert m.max_drawdown == pytest.approx(0.1)
    assert m.longest_underwater_days == pytest.approx(2.0)
    assert m.days == pytest.approx(3.0)
    assert m.bars == 4
    assert m.cagr is not None
    assert m.cagr > 0
    assert m.sharpe is not None
    assert m.sharpe > 0
    assert m.sortino is not None
    assert m.calmar is not None
    assert m.calmar == pytest.approx(m.cagr / 0.1)
    assert m.trades == 3
    assert m.win_rate == pytest.approx(2 / 3)
    assert m.profit_factor == pytest.approx(3.0)
    assert m.expectancy == Decimal("100") / 3
    assert m.avg_trade_hours == pytest.approx((8 + 4 + 8) / 3)
    assert m.exposure == pytest.approx(0.75)
    assert m.fees_quote == Decimal("0.101")  # 0.001 BTC × 101
    assert m.avg_shortfall_bps == pytest.approx(100.0)
    assert m.exits == {"stop": 1, "trailing": 2}

    payload = m.to_dict()
    assert payload["total_return"] == "0.2"
    assert payload["expectancy"] == str(Decimal("100") / 3)
    assert payload["exits"] == {"stop": 1, "trailing": 2}


def test_metrics_without_trades_and_flat_equity() -> None:
    equity = [(D0 + i * DAY_MS, d("10000")) for i in range(5)]
    m = compute_metrics(equity, [False] * 5, [], [])
    assert m.total_return == Decimal("0")
    assert m.cagr == pytest.approx(0.0)
    assert m.sharpe is None  # desvío 0
    assert m.max_drawdown == 0.0
    assert m.profit_factor is None
    assert m.win_rate is None
    assert m.expectancy is None
    assert m.exposure == 0.0
    assert m.exits == {}


def test_metrics_validation() -> None:
    with pytest.raises(ValueError, match="al menos un punto"):
        compute_metrics([], [], [], [])
    with pytest.raises(ValueError, match="misma longitud"):
        compute_metrics([(D0, d("1"))], [], [], [])


def test_max_drawdown_paths() -> None:
    assert max_drawdown([(D0, d("1"))]) == (0.0, 0.0)
    rising = [(D0 + i * DAY_MS, d(str(100 + i))) for i in range(5)]
    assert max_drawdown(rising) == (0.0, 0.0)
    never_recovers = [(D0, d("100")), (D0 + DAY_MS, d("80")), (D0 + 2 * DAY_MS, d("90"))]
    depth, days = max_drawdown(never_recovers)
    assert depth == pytest.approx(0.2)
    assert days == pytest.approx(2.0)


def test_yearly_breakdown_uses_previous_close_as_base() -> None:
    dec_30 = 1_703_980_800_000 - DAY_MS  # 2023-12-30T00:00Z
    equity = [
        (dec_30, d("10000")),
        (dec_30 + DAY_MS, d("11000")),  # 2023-12-31
        (dec_30 + 2 * DAY_MS, d("12100")),  # 2024-01-01
        (dec_30 + 3 * DAY_MS, d("11000")),
    ]
    rows = yearly_breakdown(equity, [_trade("10")])
    assert [r["year"] for r in rows] == [2023, 2024]
    assert rows[0]["return"] == pytest.approx(0.1)
    assert rows[1]["return"] == pytest.approx(0.0)  # 11000 / 11000 − 1
    assert rows[1]["max_drawdown"] == pytest.approx(1 - 11000 / 12100)
    assert rows[1]["trades"] == 1
    assert rows[1]["pnl"] == "10"
    assert yearly_breakdown([], []) == []
