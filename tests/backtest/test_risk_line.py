"""Resumen de protecciones que va a la línea de riesgo del REPORT.md."""

from __future__ import annotations

from tests.factories import d
from tradingbot.backtest.runner import _protections_summary
from tradingbot.config.models import RiskConfig


def test_summary_with_defaults() -> None:
    summary = _protections_summary(RiskConfig())
    assert summary == [
        "pérdida diaria 3.0 % (día UTC)",
        "circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d)",
        "pausa por pérdidas off",
        "cooldown tras stop off",
        "filtro de mercado off",
    ]


def test_summary_with_everything_off_or_custom() -> None:
    off = _protections_summary(RiskConfig(daily_loss_limit_pct=None, max_drawdown_pct=None))
    assert off[:2] == ["pérdida diaria off", "circuit breaker off"]
    custom = _protections_summary(
        RiskConfig(
            daily_loss_limit_pct=d("0.01"),
            max_drawdown_pct=d("0.05"),
            drawdown_resume_pct=d("0.025"),
            drawdown_pause_days=None,
            pause_after_consecutive_losses=3,
            pause_candles_after_losses=12,
            cooldown_candles_after_stop=6,
        )
    )
    assert custom == [
        "pérdida diaria 1.0 % (día UTC)",
        "circuit breaker DD 5 % (reanuda bajo 2.5 %)",
        "pausa 12 velas tras 3 pérdidas seguidas",
        "cooldown tras stop 6 velas",
        "filtro de mercado off",
    ]
