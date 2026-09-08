"""Validación de estrategias.

Fase 3: equivalencia (lookahead y paridad de ventana). Fase 6: walk-forward, optimizer, plateau,
montecarlo y regímenes.
"""

from tradingbot.validation.equivalence import (
    EquivalenceReport,
    assert_equivalent,
    check_no_lookahead,
    check_window_equivalence,
    signal_at,
)

__all__ = [
    "EquivalenceReport",
    "assert_equivalent",
    "check_no_lookahead",
    "check_window_equivalence",
    "signal_at",
]
