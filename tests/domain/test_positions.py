from decimal import Decimal

import pytest
from pydantic import ValidationError

from tests.factories import BTC, ETH, H4_MS, T0, d, make_position
from tradingbot.domain import (
    ExitReason,
    PortfolioSnapshot,
    Position,
    Side,
    Trade,
    make_client_order_id,
)


def test_position_math() -> None:
    position = make_position(qty="0.5", entry_price="100", stop_price="90")
    assert position.value(d("120")) == Decimal("60")
    assert position.unrealized_pnl(d("120")) == Decimal("10")
    assert position.risk_at_stop() == Decimal("5")


def test_position_highest_close_only_rises() -> None:
    position = make_position(entry_price="100")
    higher = position.with_close(d("120"))
    assert higher.highest_close_since_entry == Decimal("120")
    assert higher.with_close(d("110")) is higher


def test_position_stop_only_rises() -> None:
    position = make_position(stop_price="90")
    raised = position.raise_stop(d("95"))
    assert raised.stop_price == Decimal("95")
    assert raised.raise_stop(d("92")) is raised
    assert raised.raise_stop(d("95")) is raised


def test_position_stop_above_entry_is_valid_and_reloadable() -> None:
    """Trailing con ganancia asegurada o gap bajista en el fill: el stop supera la entrada."""
    locked = make_position(entry_price="100", stop_price="105")
    assert locked.risk_at_stop() == Decimal("-2.5")
    trailed = make_position(entry_price="100", stop_price="90").raise_stop(d("130"))
    reloaded = Position.model_validate(trailed.model_dump())
    assert reloaded == trailed
    assert reloaded.stop_price == Decimal("130")


def test_position_rejects_non_positive_values() -> None:
    with pytest.raises(ValidationError):
        make_position(qty="0")
    with pytest.raises(ValidationError):
        make_position(stop_price="0")


def _trade(
    exit_price: str, fees: str = "0.2", exit_reason: ExitReason = ExitReason.TRAILING
) -> Trade:
    return Trade(
        pair=BTC,
        strategy="ema_trend",
        qty=d("0.5"),
        entry_price=d("100"),
        entry_time=T0,
        exit_price=d(exit_price),
        exit_time=T0 + 3 * H4_MS,
        exit_reason=exit_reason,
        fees_quote=d(fees),
        entry_client_order_id=make_client_order_id("ema_trend", BTC, T0, Side.BUY),
        exit_client_order_id=make_client_order_id(
            "ema_trend", BTC, T0 + 3 * H4_MS, Side.SELL, exit_reason
        ),
    )


def test_trade_pnl() -> None:
    winner = _trade("120")
    assert winner.gross_pnl == Decimal("10")
    assert winner.pnl == Decimal("9.8")
    assert winner.pnl_pct == Decimal("0.196")
    assert winner.duration_ms == 3 * H4_MS
    assert winner.is_winner
    loser = _trade("90", exit_reason=ExitReason.STOP)
    assert loser.pnl == Decimal("-5.2")
    assert not loser.is_winner
    assert loser.exit_client_order_id.endswith("-X")


def test_trade_rejects_exit_before_entry() -> None:
    with pytest.raises(ValidationError, match="anterior"):
        _trade("120").model_validate(_trade("120").model_dump() | {"exit_time": T0 - 1})


def test_snapshot_equity_and_exposure() -> None:
    btc = make_position(pair=BTC, qty="0.5", entry_price="100", stop_price="90")
    eth = make_position(pair=ETH, qty="10", entry_price="10", stop_price="9")
    snapshot = PortfolioSnapshot(
        ts=T0,
        cash=d("100"),
        positions=(btc, eth),
        marks={BTC: d("120"), ETH: d("8")},
        dust={"BTC": d("0.000004")},
    )
    assert snapshot.positions_value == Decimal("140")
    assert snapshot.equity == Decimal("240")
    assert snapshot.exposure_pct == Decimal("140") / Decimal("240")
    assert snapshot.position_for(BTC) is btc
    assert snapshot.position_for(ETH) is eth
    assert snapshot.dust["BTC"] == Decimal("0.000004")


def test_empty_snapshot() -> None:
    snapshot = PortfolioSnapshot(ts=T0, cash=d("0"))
    assert snapshot.equity == Decimal("0")
    assert snapshot.exposure_pct == Decimal("0")
    assert snapshot.position_for(BTC) is None


def test_snapshot_invariants() -> None:
    position = make_position()
    with pytest.raises(ValidationError, match="dos posiciones"):
        PortfolioSnapshot(ts=T0, cash=d("1"), positions=(position, position), marks={BTC: d("1")})
    with pytest.raises(ValidationError, match="falta el precio"):
        PortfolioSnapshot(ts=T0, cash=d("1"), positions=(position,))
    with pytest.raises(ValidationError):
        PortfolioSnapshot(ts=T0, cash=d("-1"))
