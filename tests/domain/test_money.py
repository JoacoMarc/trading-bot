from decimal import ROUND_DOWN, ROUND_UP, Decimal, localcontext

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from tradingbot.domain import apply_bps, fmt, notional, quantize_price, quantize_qty, to_decimal


def test_to_decimal_avoids_float_artifacts() -> None:
    assert to_decimal(0.1) == Decimal("0.1")
    assert to_decimal(43521.12) == Decimal("43521.12")
    assert to_decimal(3) == Decimal(3)
    assert to_decimal(" 1.50 ") == Decimal("1.50")
    assert to_decimal(Decimal("2.5")) == Decimal("2.5")


def test_to_decimal_accepts_numpy_floats() -> None:
    assert to_decimal(np.float64(0.1)) == Decimal("0.1")
    assert to_decimal(np.float64(43521.12)) == Decimal("43521.12")
    assert to_decimal(np.float32(1.5)) == Decimal("1.5")


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), "nan", "abc", "Infinity", np.float64("nan")]
)
def test_to_decimal_rejects_non_finite_and_garbage(value: float | str) -> None:
    with pytest.raises(ValueError, match=r"no finito|no se puede convertir"):
        to_decimal(value)


def test_to_decimal_rejects_bool() -> None:
    with pytest.raises(TypeError):
        to_decimal(True)


def test_quantize_qty_rounds_down_to_step() -> None:
    assert quantize_qty(Decimal("0.123456789"), Decimal("0.00001")) == Decimal("0.12345")
    assert quantize_qty(Decimal("1.74"), Decimal("0.5")) == Decimal("1.5")
    assert quantize_qty(Decimal("199"), Decimal("100")) == Decimal("100")
    assert quantize_qty(Decimal("0.000004"), Decimal("0.00001")) == Decimal("0")
    assert str(quantize_qty(Decimal("1"), Decimal("0.00100000"))) == "1.000"


def test_quantize_never_rounds_up_with_long_inputs() -> None:
    almost_one = Decimal("0.9999999999999999999999999999")
    assert quantize_qty(almost_one, Decimal("0.5")) == Decimal("0.5")
    assert quantize_qty(Decimal("0." + "9" * 29), Decimal("1")) == Decimal("0")


def test_quantize_price_rounding_modes() -> None:
    assert quantize_price(Decimal("100.005"), Decimal("0.01")) == Decimal("100.01")
    assert quantize_price(Decimal("100.004"), Decimal("0.01")) == Decimal("100.00")
    assert quantize_price(Decimal("100.009"), Decimal("0.01"), ROUND_DOWN) == Decimal("100.00")
    assert quantize_price(Decimal("100.001"), Decimal("0.01"), ROUND_UP) == Decimal("100.01")


def test_quantize_rejects_bad_step() -> None:
    with pytest.raises(ValueError, match="positivo"):
        quantize_qty(Decimal("1"), Decimal("0"))
    with pytest.raises(ValueError, match="positivo"):
        quantize_price(Decimal("1"), Decimal("-0.01"))


def test_helpers() -> None:
    assert notional(Decimal("100"), Decimal("0.5")) == Decimal("50")
    assert apply_bps(Decimal("10000"), Decimal("5")) == Decimal("5")
    assert fmt(Decimal("1E+2")) == "100"
    assert fmt(Decimal("0.00001000")) == "0.00001000"


STEPS = [
    Decimal(s) for s in ("1", "0.1", "0.01", "0.001", "0.00001", "0.00000001", "0.5", "0.25", "100")
]


@given(
    qty=st.decimals(
        min_value=Decimal("0"),
        max_value=Decimal("1000000"),
        places=30,
        allow_nan=False,
        allow_infinity=False,
    ),
    step=st.sampled_from(STEPS),
)
def test_quantize_qty_properties(qty: Decimal, step: Decimal) -> None:
    result = quantize_qty(qty, step)
    # Las comprobaciones se hacen con precisión alta: con los 28 dígitos por defecto la resta
    # `qty - result` puede redondearse hacia arriba y dar un falso positivo.
    with localcontext() as ctx:
        ctx.prec = 80
        assert result <= qty
        assert qty - result < step
        assert (result / step) == (result / step).to_integral_value()
    assert quantize_qty(result, step) == result
