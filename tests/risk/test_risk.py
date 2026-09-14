from __future__ import annotations

from decimal import Decimal
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.fakes import MARKETS, market
from tests.factories import BTC, ETH, T0, d, make_position
from tradingbot.config.models import ExecutionConfig, RiskConfig
from tradingbot.domain import ExitReason, Pair, Position, Signal, SignalAction
from tradingbot.risk import (
    PortfolioView,
    ReasonCode,
    RiskManager,
    sellable_qty,
    size_by_fraction,
    size_by_risk,
)


def enter(pair: Pair = BTC, stop: str = "90", strength: float | None = 25.0) -> Signal:
    return Signal(
        action=SignalAction.ENTER_LONG,
        pair=pair,
        open_time=T0,
        stop_price=d(stop),
        strength=strength,
    )


def view(
    cash: str = "10000",
    positions: dict[Pair, Position] | None = None,
    marks: dict[Pair, Decimal] | None = None,
    pending: frozenset[Pair] = frozenset(),
    pending_notional: str = "0",
) -> PortfolioView:
    positions = positions or {}
    marks = marks or {BTC: d("100"), ETH: d("10")}
    value = sum((p.qty * marks[p.pair] for p in positions.values()), Decimal(0))
    return PortfolioView(
        equity=d(cash) + value,
        cash_available=d(cash),
        positions=positions,
        marks=marks,
        pending_pairs=frozenset(pending),
        pending_notional=d(pending_notional),
    )


def manager(
    risk: RiskConfig | None = None, execution: ExecutionConfig | None = None
) -> RiskManager:
    return RiskManager(risk or RiskConfig(), execution or ExecutionConfig(), MARKETS, "ema_trend")


def test_size_by_risk_formula() -> None:
    result = size_by_risk(
        equity=d("10000"),
        cash_available=d("10000"),
        price=d("100"),
        stop=d("90"),
        risk_per_trade=d("0.01"),
        max_position_pct=d("0.25"),
        cost_factor=d("1.0005"),
        market=MARKETS[BTC],
    )
    assert result.ok
    assert result.qty == Decimal("10")  # 100 USDT de riesgo / 10 de distancia
    assert result.notional == Decimal("1000")
    # con stop muy cercano manda el tope de cash: 2500 / (100 × 1.0005) = 24.98750...
    tight = size_by_risk(
        equity=d("10000"),
        cash_available=d("10000"),
        price=d("100"),
        stop=d("99.9"),
        risk_per_trade=d("0.01"),
        max_position_pct=d("0.25"),
        cost_factor=d("1.0005"),
        market=MARKETS[BTC],
    )
    assert tight.qty == Decimal("24.98750")
    assert tight.notional * d("1.0005") <= d("2500")


def test_size_by_risk_rejections() -> None:
    common: dict[str, Any] = {
        "equity": d("10000"),
        "cash_available": d("10000"),
        "price": d("100"),
        "risk_per_trade": d("0.01"),
        "max_position_pct": d("0.25"),
        "cost_factor": d("1.0005"),
        "market": MARKETS[BTC],
    }
    assert size_by_risk(stop=d("100"), **common).reason is ReasonCode.INVALID_STOP
    assert (
        size_by_risk(**{**common, "cash_available": d("0")}, stop=d("90")).reason
        is ReasonCode.NO_CASH
    )
    tiny = size_by_risk(**{**common, "equity": d("1"), "cash_available": d("1")}, stop=d("90"))
    assert tiny.reason is ReasonCode.MIN_NOTIONAL
    coarse = size_by_risk(
        **{**common, "market": market(BTC).model_copy(update={"step_size": d("100")})}, stop=d("90")
    )
    assert coarse.reason is ReasonCode.MIN_QTY


def test_sellable_qty_and_dust() -> None:
    qty, dust = sellable_qty(d("9.990004"), MARKETS[BTC])
    assert qty == Decimal("9.99000")
    assert dust == Decimal("0.000004")


def test_evaluate_entries_ranks_and_applies_slots() -> None:
    m = manager(RiskConfig(max_positions=1))
    decision = m.evaluate_entries(
        [enter(BTC, strength=10.0), enter(ETH, stop="9", strength=30.0)], view(), T0
    )
    assert [i.pair for i in decision.intents] == [ETH]
    assert decision.intents[0].client_order_id.endswith("-B")
    assert decision.intents[0].decision_price == Decimal("10")
    assert [r.reason for r in decision.rejections] == [ReasonCode.MAX_POSITIONS]
    # sin strength va último
    both = manager(RiskConfig(max_positions=2)).evaluate_entries(
        [enter(BTC, strength=None), enter(ETH, stop="9", strength=1.0)], view(), T0
    )
    assert [i.pair for i in both.intents] == [ETH, BTC]


def test_evaluate_entries_blocks_existing_and_pending_pairs() -> None:
    m = manager()
    position = make_position(pair=BTC)
    decision = m.evaluate_entries(
        [enter(BTC), enter(ETH, stop="9")],
        view(positions={BTC: position}, pending=frozenset({ETH})),
        T0,
    )
    assert decision.intents == ()
    reasons = {r.signal.pair: r.reason for r in decision.rejections}
    assert reasons == {BTC: ReasonCode.ALREADY_IN_POSITION, ETH: ReasonCode.PENDING_ORDER}


def test_exposure_limit_and_running_cash() -> None:
    m = manager(RiskConfig(max_positions=5, max_position_pct=d("0.5"), max_exposure_pct=d("0.5")))
    # dos señales con stop lejano: cada una pide ~1 000 USDT; la exposición tope es 5 000
    decision = m.evaluate_entries([enter(BTC, stop="90"), enter(ETH, stop="9")], view(), T0)
    assert len(decision.intents) == 2
    # con tope de exposición del 10 % (1 000) solo entra la primera
    tight = manager(
        RiskConfig(max_positions=5, max_position_pct=d("0.1"), max_exposure_pct=d("0.1"))
    )
    decision = tight.evaluate_entries(
        [enter(BTC, stop="90", strength=30.0), enter(ETH, stop="9", strength=10.0)], view(), T0
    )
    assert [i.pair for i in decision.intents] == [BTC]
    assert decision.rejections[0].reason is ReasonCode.EXPOSURE_LIMIT


def test_evaluate_entries_ignores_non_entry_signals_and_missing_data() -> None:
    m = manager()
    hold = Signal.hold(BTC, T0)
    decision = m.evaluate_entries([hold], view(), T0)
    assert decision.intents == ()
    assert decision.rejections == ()
    no_mark = m.evaluate_entries([enter(BTC)], view(marks={ETH: d("10")}), T0)
    assert no_mark.rejections[0].reason is ReasonCode.INVALID_STOP


def test_exit_intent_never_blocks_unless_exchange_would_reject() -> None:
    m = manager()
    position = make_position(pair=BTC, qty="9.990004", entry_price="100", stop_price="90")
    decision = m.exit_intent(position, ExitReason.SIGNAL, d("105"), T0, T0)
    assert decision.intent is not None
    assert decision.intent.qty == Decimal("9.99000")
    assert decision.dust == Decimal("0.000004")
    assert decision.intent.client_order_id.endswith("-S")
    assert decision.intent.exit_reason is ExitReason.SIGNAL
    small = m.exit_intent(
        make_position(pair=BTC, qty="0.00001", entry_price="100", stop_price="90"),
        ExitReason.STOP,
        d("100"),
        T0,
        T0,
    )
    assert small.intent is None
    assert small.reason is ReasonCode.MIN_NOTIONAL


def test_buy_cost_factor() -> None:
    assert manager().buy_cost_factor == Decimal("1.0005")
    with_bnb = manager(execution=ExecutionConfig(pay_with_bnb=True))
    assert with_bnb.buy_cost_factor == Decimal("1.0005") * (1 + Decimal("0.00075"))


@settings(max_examples=100, deadline=None)
@given(
    equity=st.decimals(
        min_value=Decimal("100"),
        max_value=Decimal("1000000"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ),
    price=st.decimals(
        min_value=Decimal("0.5"),
        max_value=Decimal("100000"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ),
    distance_pct=st.decimals(
        min_value=Decimal("0.001"),
        max_value=Decimal("0.5"),
        places=3,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_sizing_never_exceeds_risk_or_budget(
    equity: Decimal, price: Decimal, distance_pct: Decimal
) -> None:
    stop = price * (1 - distance_pct)
    result = size_by_risk(
        equity=equity,
        cash_available=equity,
        price=price,
        stop=stop,
        risk_per_trade=d("0.01"),
        max_position_pct=d("0.25"),
        cost_factor=d("1.0005"),
        market=MARKETS[BTC],
    )
    if result.qty is None:
        assert result.reason in {ReasonCode.MIN_QTY, ReasonCode.MIN_NOTIONAL}
        return
    assert result.qty * (price - stop) <= equity * d("0.01") + MARKETS[BTC].step_size * (
        price - stop
    )
    assert (
        result.notional * d("1.0005")
        <= equity * d("0.25") + price * d("1.0005") * MARKETS[BTC].step_size
    )
    assert result.notional >= MARKETS[BTC].min_notional


def test_size_by_fraction_ignores_stop_distance() -> None:
    result = size_by_fraction(
        equity=d("10000"),
        cash_available=d("10000"),
        price=d("100"),
        fraction=d("0.6"),
        cost_factor=d("1.0005"),
        market=MARKETS[BTC],
    )
    assert result.ok
    assert result.qty is not None
    assert d("59.9") < result.qty <= d("60")  # 6,000 / (100 x 1.0005)
    capped = size_by_fraction(
        equity=d("10000"),
        cash_available=d("2000"),
        price=d("100"),
        fraction=d("0.6"),
        cost_factor=d("1"),
        market=MARKETS[BTC],
    )
    assert capped.qty == d("20")  # el cash libre acota
    broke = size_by_fraction(
        equity=d("10000"),
        cash_available=d("0"),
        price=d("100"),
        fraction=d("0.6"),
        cost_factor=d("1"),
        market=MARKETS[BTC],
    )
    assert broke.reason is ReasonCode.NO_CASH


def test_manager_in_fraction_mode_sizes_by_equity_share() -> None:
    m = manager(RiskConfig(sizing_mode="fraction", position_fraction=d("0.6"), max_positions=1))
    decision = m.evaluate_entries(
        [enter(BTC, stop="99")], view(), T0
    )  # stop a 1 %: por riesgo daría 100 unidades
    assert len(decision.intents) == 1
    assert d("59.9") < decision.intents[0].qty <= d("60")
    assert decision.intents[0].stop_price == d("99")  # el stop viaja igual: es de seguridad
