"""Protecciones dinámicas (ADR-0007): pérdida diaria, breaker, pausas, cooldown, kill switch."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from tests.factories import BTC, ETH, H4_MS, T0, d, make_position
from tests.risk.test_risk import enter, manager, view
from tradingbot.config.models import RiskConfig
from tradingbot.domain import Pair, Trade
from tradingbot.domain.enums import ExitReason, Side
from tradingbot.domain.orders import make_client_order_id
from tradingbot.risk import FileKillSwitch, KillSwitchState, Protections, ReasonCode
from tradingbot.risk.protections import MS_PER_DAY, PROTECTION_CLEARED, PROTECTION_TRIGGERED

DAY0 = T0 - T0 % MS_PER_DAY  # medianoche UTC del día de T0
OFF = {"daily_loss_limit_pct": None, "max_drawdown_pct": None}


def trade(pnl: str, reason: ExitReason = ExitReason.TRAILING, pair: Pair = BTC) -> Trade:
    """Round trip de 1 unidad a 100 con fees 0.2: `pnl` es el neto."""
    return Trade(
        pair=pair,
        strategy="ema_trend",
        qty=d("1"),
        entry_price=d("100"),
        entry_time=T0,
        exit_price=d("100") + d(pnl) + d("0.2"),
        exit_time=T0 + H4_MS,
        exit_reason=reason,
        fees_quote=d("0.2"),
        entry_client_order_id=make_client_order_id("ema_trend", pair, T0, Side.BUY),
        exit_client_order_id=make_client_order_id("ema_trend", pair, T0 + H4_MS, Side.SELL, reason),
    )


def kinds(p: Protections) -> list[tuple[str, ReasonCode]]:
    return [(e.kind, e.reason) for e in p.pop_events()]


def reason(p: Protections) -> ReasonCode | None:
    block = p.global_block()
    return None if block is None else block.reason


def halted(p: Protections) -> bool:
    return p.drawdown_halted


def daily(p: Protections) -> bool:
    return p.daily_halted


def paused(p: Protections) -> bool:
    return p.losses_paused


def flatten(p: Protections) -> bool:
    return p.flatten_requested


def test_daily_loss_blocks_until_next_utc_day() -> None:
    p = Protections(RiskConfig(daily_loss_limit_pct=d("0.03"), max_drawdown_pct=None))
    p.on_bar(0, DAY0 + H4_MS - 1)
    p.on_equity(DAY0 + H4_MS - 1, d("10000"))
    p.on_equity(DAY0 + 2 * H4_MS - 1, d("9800"))  # -2 %: nada
    assert reason(p) is None
    p.on_equity(DAY0 + 3 * H4_MS - 1, d("9700"))  # -3 %: bloquea el resto del día
    assert daily(p)
    assert reason(p) is ReasonCode.DAILY_LOSS_LIMIT
    assert kinds(p) == [(PROTECTION_TRIGGERED, ReasonCode.DAILY_LOSS_LIMIT)]
    p.on_equity(DAY0 + 4 * H4_MS - 1, d("9900"))  # recuperar dentro del día no libera
    assert daily(p)
    # Día siguiente: libera; la base pasa a ser la última equity del día anterior (9900).
    p.on_equity(DAY0 + MS_PER_DAY + H4_MS - 1, d("9700"))  # -2.02 %
    assert not daily(p)
    assert reason(p) is None
    assert kinds(p) == [(PROTECTION_CLEARED, ReasonCode.DAILY_LOSS_LIMIT)]
    p.on_equity(DAY0 + MS_PER_DAY + 2 * H4_MS - 1, d("9600"))  # -3.03 %
    assert daily(p)
    assert p.status()["daily_halted"] == "True"


def test_drawdown_breaker_auto_resume() -> None:
    p = Protections(RiskConfig(daily_loss_limit_pct=None, max_drawdown_pct=d("0.10")))
    p.on_equity(T0, d("10000"))
    p.on_equity(T0 + H4_MS, d("8900"))  # DD 11 %
    assert halted(p)
    assert reason(p) is ReasonCode.DRAWDOWN_HALT
    p.on_equity(T0 + 2 * H4_MS, d("9400"))  # DD 6 % > 5 %: sigue frenado
    assert halted(p)
    p.on_equity(T0 + 3 * H4_MS, d("9600"))  # DD 4 % <= 5 %: reanuda solo
    assert not halted(p)
    assert kinds(p) == [
        (PROTECTION_TRIGGERED, ReasonCode.DRAWDOWN_HALT),
        (PROTECTION_CLEARED, ReasonCode.DRAWDOWN_HALT),
    ]
    p.on_equity(T0 + 4 * H4_MS, d("11000"))
    assert p.peak_equity == d("11000")
    assert p.drawdown == d("0")


def test_drawdown_breaker_manual_resume_rebases_peak() -> None:
    cfg = RiskConfig(daily_loss_limit_pct=None, max_drawdown_pct=d("0.10"), drawdown_pause_days=1)
    p = Protections(cfg, auto_resume=False)
    p.on_equity(T0, d("10000"))
    p.on_equity(T0 + H4_MS, d("8900"))
    assert halted(p)
    p.on_equity(T0 + 2 * H4_MS, d("9900"))  # DD 1 %: en paper/live nada reanuda solo
    assert halted(p)
    p.on_equity(T0 + 2 * MS_PER_DAY, d("9900"))  # ni el plazo
    assert halted(p)
    p.resume()  # inmediato; el pico pasa a ser la equity actual (9900)
    assert not halted(p)
    assert p.peak_equity == d("9900")
    p.on_equity(T0 + 3 * MS_PER_DAY, d("9000"))  # DD 9.1 % del nuevo pico: no frena
    assert not halted(p)
    p.on_equity(T0 + 4 * MS_PER_DAY, d("8900"))  # DD 10.1 %: frena
    assert halted(p)
    p.resume()  # aun con DD sobre el umbral: re-basa en 8900
    assert not halted(p)
    assert p.peak_equity == d("8900")
    cleared = [e.detail for e in p.pop_events() if e.kind == PROTECTION_CLEARED]
    assert len(cleared) == 2
    assert all("manual" in detail for detail in cleared)


def test_drawdown_time_fallback_rebases_peak_in_backtest() -> None:
    cfg = RiskConfig(daily_loss_limit_pct=None, max_drawdown_pct=d("0.10"), drawdown_pause_days=2)
    p = Protections(cfg)
    p.on_equity(T0, d("10000"))
    p.on_equity(T0 + H4_MS, d("8900"))  # frena; en cash el DD queda clavado en 11 %
    assert halted(p)
    p.on_equity(T0 + H4_MS + MS_PER_DAY, d("8900"))
    assert halted(p)
    p.on_equity(T0 + H4_MS + 2 * MS_PER_DAY, d("8900"))  # plazo cumplido: reanuda y re-basa
    assert not halted(p)
    assert p.peak_equity == d("8900")
    assert p.status()["halted_since"] == ""
    p.on_equity(T0 + 2 * H4_MS + 2 * MS_PER_DAY, d("8000"))  # DD 10.1 % del nuevo pico
    assert halted(p)
    details = [e.detail for e in p.pop_events() if e.kind == PROTECTION_CLEARED]
    assert details == ["2 días frenado sin recuperar el DD; pico re-basado en 8900"]

    stuck = Protections(
        RiskConfig(daily_loss_limit_pct=None, max_drawdown_pct=d("0.10"), drawdown_pause_days=None)
    )
    stuck.on_equity(T0, d("10000"))
    stuck.on_equity(T0 + H4_MS, d("8900"))
    stuck.on_equity(T0 + 10 * MS_PER_DAY, d("8900"))  # sin plazo: frenado para siempre
    assert halted(stuck)


def test_drawdown_resume_config_validation() -> None:
    with pytest.raises(ValidationError):
        RiskConfig(max_drawdown_pct=d("0.2"), drawdown_resume_pct=d("0.2"))
    with pytest.raises(ValidationError):
        RiskConfig(max_drawdown_pct=None, drawdown_resume_pct=d("0.1"))
    with pytest.raises(ValidationError):
        RiskConfig(drawdown_pause_days=0)
    assert RiskConfig(max_drawdown_pct=d("0.2")).effective_drawdown_resume_pct == d("0.1")
    assert RiskConfig(max_drawdown_pct=None).effective_drawdown_resume_pct is None
    assert RiskConfig(
        max_drawdown_pct=d("0.2"), drawdown_resume_pct=d("0.05")
    ).effective_drawdown_resume_pct == d("0.05")


def test_consecutive_losses_pause_and_reset() -> None:
    cfg = RiskConfig(**OFF, pause_after_consecutive_losses=2, pause_candles_after_losses=3)
    p = Protections(cfg)
    p.on_bar(10, T0)
    p.on_trade_closed(trade("-5"))
    p.on_trade_closed(trade("3"))  # la ganancia reinicia la racha
    p.on_trade_closed(trade("-5"))
    assert not paused(p)
    p.on_trade_closed(trade("-5"))
    assert paused(p)
    assert reason(p) is ReasonCode.CONSECUTIVE_LOSSES
    p.on_bar(12, T0)
    assert paused(p)
    p.on_bar(13, T0)
    assert not paused(p)
    assert reason(p) is None
    p.on_trade_closed(trade("-5"))  # la pausa reinició la racha: una pérdida no re-pausa
    assert not paused(p)
    p.on_trade_closed(trade("-5"))
    assert paused(p)
    assert kinds(p) == [
        (PROTECTION_TRIGGERED, ReasonCode.CONSECUTIVE_LOSSES),
        (PROTECTION_CLEARED, ReasonCode.CONSECUTIVE_LOSSES),
        (PROTECTION_TRIGGERED, ReasonCode.CONSECUTIVE_LOSSES),
    ]


def test_pair_cooldown_after_losing_stop_or_trailing() -> None:
    p = Protections(RiskConfig(**OFF, cooldown_candles_after_stop=2))
    p.on_bar(5, T0)
    p.on_trade_closed(trade("8", ExitReason.TRAILING))  # trailing ganador: no enfría
    assert p.pair_block(BTC) is None
    p.on_trade_closed(trade("-5", ExitReason.SIGNAL))  # salida por señal: no enfría
    assert p.pair_block(BTC) is None
    p.on_trade_closed(trade("-5", ExitReason.TRAILING))  # trailing perdedor: enfría
    block = p.pair_block(BTC)
    assert block is not None
    assert block.reason is ReasonCode.PAIR_COOLDOWN
    assert p.pair_block(ETH) is None
    assert reason(p) is None
    p.on_bar(6, T0)
    assert p.pair_block(BTC) is not None
    p.on_bar(7, T0)
    assert p.pair_block(BTC) is None
    p.on_trade_closed(trade("-5", ExitReason.STOP, ETH))  # stop perdedor: enfría
    assert p.pair_block(ETH) is not None
    events = p.pop_events()
    assert [e.pair for e in events] == [BTC, BTC, ETH]
    assert events[0].ts == T0 + H4_MS  # el evento lleva el ts del fill de salida


def test_kill_switch_transitions_and_priority() -> None:
    p = Protections(RiskConfig(daily_loss_limit_pct=None, max_drawdown_pct=d("0.10")))
    p.on_equity(T0, d("10000"))
    p.on_equity(T0 + H4_MS, d("8000"))  # circuit breaker activo
    p.set_kill_switch(KillSwitchState(active=True))
    p.set_kill_switch(KillSwitchState(active=True))  # idempotente: un solo evento
    assert reason(p) is ReasonCode.KILL_SWITCH
    assert not flatten(p)
    p.set_kill_switch(KillSwitchState(active=True, flatten=True))
    assert flatten(p)
    assert p.status()["kill_switch"] == "flatten"
    p.set_kill_switch(KillSwitchState(active=True))  # downgrade flatten -> stop
    assert not flatten(p)
    assert reason(p) is ReasonCode.KILL_SWITCH
    p.set_kill_switch(KillSwitchState())
    assert reason(p) is ReasonCode.DRAWDOWN_HALT
    events = p.pop_events()
    assert [(e.kind, e.reason) for e in events] == [
        (PROTECTION_TRIGGERED, ReasonCode.DRAWDOWN_HALT),
        (PROTECTION_TRIGGERED, ReasonCode.KILL_SWITCH),
        (PROTECTION_TRIGGERED, ReasonCode.KILL_SWITCH),
        (PROTECTION_CLEARED, ReasonCode.KILL_SWITCH),
        (PROTECTION_CLEARED, ReasonCode.KILL_SWITCH),
    ]
    assert "flatten retirado" in events[3].detail


def test_drawdown_outranks_daily_loss() -> None:
    p = Protections(RiskConfig(daily_loss_limit_pct=d("0.03"), max_drawdown_pct=d("0.10")))
    p.on_equity(T0, d("10000"))
    p.on_equity(T0 + H4_MS, d("8900"))  # dispara ambas
    assert daily(p)
    assert halted(p)
    assert reason(p) is ReasonCode.DRAWDOWN_HALT
    assert [r for _, r in kinds(p)] == [ReasonCode.DAILY_LOSS_LIMIT, ReasonCode.DRAWDOWN_HALT]


def test_risk_manager_rejects_entries_with_protection_reason() -> None:
    m = manager(
        RiskConfig(
            daily_loss_limit_pct=None, max_drawdown_pct=d("0.10"), cooldown_candles_after_stop=2
        )
    )
    p = m.protections
    p.on_bar(0, T0)
    p.on_equity(T0, d("10000"))
    p.on_equity(T0 + H4_MS, d("8500"))
    decision = m.evaluate_entries([enter(BTC), enter(ETH, stop="9")], view(cash="8500"), T0)
    assert decision.intents == ()
    assert {r.reason for r in decision.rejections} == {ReasonCode.DRAWDOWN_HALT}
    # Reanuda; solo el par en cooldown queda afuera.
    p.on_equity(T0 + 2 * H4_MS, d("9800"))
    p.on_trade_closed(trade("-5", ExitReason.STOP, BTC))
    decision = m.evaluate_entries([enter(BTC), enter(ETH, stop="9")], view(cash="9800"), T0)
    assert [i.pair for i in decision.intents] == [ETH]
    assert [(r.signal.pair, r.reason) for r in decision.rejections] == [
        (BTC, ReasonCode.PAIR_COOLDOWN)
    ]


@settings(max_examples=64, deadline=None)
@given(
    kill=st.booleans(),
    flatten=st.booleans(),
    drawdown=st.booleans(),
    daily=st.booleans(),
    losses=st.booleans(),
)
def test_exits_ignore_protections_and_entries_respect_them(
    kill: bool, flatten: bool, drawdown: bool, daily: bool, losses: bool
) -> None:
    m = manager(
        RiskConfig(
            daily_loss_limit_pct=d("0.01"),
            max_drawdown_pct=d("0.05"),
            pause_after_consecutive_losses=1,
            pause_candles_after_losses=5,
            cooldown_candles_after_stop=5,
        )
    )
    p = m.protections
    p.on_bar(0, T0)
    p.on_equity(T0, d("10000"))
    if drawdown:
        p.on_equity(T0 + H4_MS, d("9000"))  # DD 10 % y pérdida diaria 10 %
    elif daily:
        p.on_equity(T0 + H4_MS, d("9850"))  # pérdida diaria 1.5 % con DD 1.5 % < 5 %
    if losses:
        p.on_trade_closed(trade("-5", ExitReason.STOP, BTC))  # pausa + cooldown BTC
    p.set_kill_switch(KillSwitchState(active=kill, flatten=flatten))

    exit_decision = m.exit_intent(
        make_position(pair=BTC, qty="1"), ExitReason.SIGNAL, d("100"), T0, T0
    )
    assert exit_decision.intent is not None
    assert exit_decision.intent.qty == d("1")

    entries = m.evaluate_entries([enter(BTC)], view(), T0)
    blocked = kill or drawdown or daily or losses
    assert (entries.intents == ()) is blocked
    if blocked:
        assert entries.rejections[0].reason in {
            ReasonCode.KILL_SWITCH,
            ReasonCode.DRAWDOWN_HALT,
            ReasonCode.DAILY_LOSS_LIMIT,
            ReasonCode.CONSECUTIVE_LOSSES,
        }


def test_file_kill_switch(tmp_path: Path) -> None:
    switch = FileKillSwitch(tmp_path / "state" / "STOP")
    assert switch.poll() == KillSwitchState()
    switch.activate()
    assert switch.poll() == KillSwitchState(active=True, flatten=False)
    switch.activate(flatten=True)
    assert switch.poll().flatten
    switch.clear()
    switch.clear()  # idempotente
    assert not switch.poll().active


def test_file_kill_switch_fails_safe_when_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    switch = FileKillSwitch(Path("STOP-inaccesible"))

    def boom(_self: Path) -> bool:
        raise PermissionError("denegado")

    monkeypatch.setattr(Path, "exists", boom)
    state = switch.poll()
    assert state == KillSwitchState(active=True, flatten=False)
    assert switch.last_error is not None
    assert "denegado" in switch.last_error
