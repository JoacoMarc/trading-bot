"""Aritmética de dinero y cantidades con `Decimal`.

Reglas (ADR-0003): la frontera float → Decimal es siempre `to_decimal` (vía `str`), las
cantidades se cuantizan al `stepSize` hacia abajo y los precios al `tickSize`.
"""

from __future__ import annotations

import numbers
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from typing import SupportsFloat

ZERO = Decimal(0)
ONE = Decimal(1)
BPS_DENOMINATOR = Decimal(10_000)


def to_decimal(value: int | float | str | Decimal | SupportsFloat) -> Decimal:
    """Convierte a `Decimal` sin arrastrar el error binario de los floats.

    `Decimal(0.1)` da 0.1000000000000000055511151231257827...; `Decimal(str(0.1))` da 0.1.
    Acepta escalares de numpy (`float64`, `float32`, `int64`): se pasan por `float()`/`int()`
    porque su `repr` no es parseable. Rechaza NaN e infinitos, que nunca son un precio ni una
    cantidad válidos.
    """
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, bool):
        msg = "bool no es un monto válido"
        raise TypeError(msg)
    elif isinstance(value, numbers.Integral):
        result = Decimal(int(value))
    elif isinstance(value, str):
        try:
            result = Decimal(value.strip())
        except InvalidOperation as exc:
            msg = f"no se puede convertir {value!r} a Decimal"
            raise ValueError(msg) from exc
    else:
        try:
            result = Decimal(repr(float(value)))
        except (TypeError, ValueError) as exc:
            msg = f"no se puede convertir {value!r} a Decimal"
            raise ValueError(msg) from exc
    if not result.is_finite():
        msg = f"monto no finito: {value!r}"
        raise ValueError(msg)
    return result


def _quantize(value: Decimal, step: Decimal, rounding: str) -> Decimal:
    if step <= ZERO:
        msg = f"step debe ser positivo, recibido {step}"
        raise ValueError(msg)
    # Precisión suficiente para que la división sea exacta antes de truncar: con la precisión
    # por defecto (28) un cociente como 0.999...9 / 0.5 se redondearía hacia arriba antes del
    # ROUND_DOWN y el resultado superaría al valor original.
    digits = len(value.as_tuple().digits) + len(step.as_tuple().digits) + 4
    with localcontext() as ctx:
        ctx.prec = max(ctx.prec, digits)
        steps = (value / step).to_integral_value(rounding=rounding)
        result = steps * step
    exponent = step.normalize().as_tuple().exponent
    if isinstance(exponent, int) and exponent < 0:
        return result.quantize(ONE.scaleb(exponent))
    return result.quantize(ONE)


def quantize_qty(qty: Decimal, step: Decimal) -> Decimal:
    """Redondea una cantidad hacia abajo al múltiplo de `step` (LOT_SIZE.stepSize).

    Hacia abajo siempre: nunca se intenta vender más de lo que hay ni comprar por encima
    del presupuesto. El resto por debajo del step es dust.
    """
    return _quantize(qty, step, ROUND_DOWN)


def quantize_price(price: Decimal, tick: Decimal, rounding: str = ROUND_HALF_UP) -> Decimal:
    """Redondea un precio al múltiplo de `tick` (PRICE_FILTER.tickSize).

    Por defecto al más cercano; los brokers pueden pedir `ROUND_DOWN`/`ROUND_UP` según el lado.
    """
    return _quantize(price, tick, rounding)


def notional(price: Decimal, qty: Decimal) -> Decimal:
    """Valor en quote de `qty` unidades a `price`."""
    return price * qty


def apply_bps(value: Decimal, bps: Decimal) -> Decimal:
    """`value × bps / 10_000`. 1 bps = 0.01 %."""
    return value * bps / BPS_DENOMINATOR


def fmt(value: Decimal) -> str:
    """Representación sin notación científica, para loguear o enviar al exchange.

    Para el exchange, cuantizar antes con `quantize_qty`/`quantize_price`: Binance rechaza
    más decimales que los del filtro del símbolo.
    """
    return f"{value:f}"
