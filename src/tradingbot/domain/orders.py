"""Señales, intenciones de orden, órdenes y fills."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbot.domain.enums import ExitReason, OrderStatus, OrderType, Side, SignalAction
from tradingbot.domain.money import BPS_DENOMINATOR, ZERO, notional
from tradingbot.domain.pair import Pair

CLIENT_ORDER_ID_MAX_LEN = 36
CLIENT_ORDER_ID_RE = re.compile(r"^[\.A-Z\:/a-z0-9_-]{1,36}$")  # regla de Binance
_CID_PREFIX = "tb"
_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]")

# Letra final del client_order_id. Distingue la venta por señal del stop repuesto en la misma
# vela, que de otro modo colisionarían en la DB y en el test de paridad.
_PURPOSE_BY_EXIT: dict[ExitReason, str] = {
    ExitReason.SIGNAL: "S",
    ExitReason.STOP: "X",
    ExitReason.TRAILING: "T",
    ExitReason.FLATTEN: "F",
    ExitReason.RISK: "R",
}


def order_purpose_tag(side: Side, exit_reason: ExitReason | None) -> str:
    """`B` para compras; `S`/`X`/`T`/`F`/`R` para ventas según el motivo."""
    if side is Side.BUY:
        if exit_reason is not None:
            msg = "una compra no lleva exit_reason"
            raise ValueError(msg)
        return "B"
    if exit_reason is None:
        msg = "una venta requiere exit_reason"
        raise ValueError(msg)
    return _PURPOSE_BY_EXIT[exit_reason]


def make_client_order_id(
    strategy: str,
    pair: Pair,
    open_time_ms: int,
    side: Side,
    exit_reason: ExitReason | None = None,
) -> str:
    """Id determinístico `tb-{estrategia}-{BASEQUOTE}-{open_time_s}-{propósito}`.

    Misma decisión → mismo id: sirve para deduplicar reintentos y para cruzar trades de paper
    y backtest en `parity`. Atención: Binance solo exige unicidad entre órdenes **abiertas**;
    una market order ya llenada no bloquea un reenvío con el mismo id. Antes de reintentar, el
    broker debe consultar la orden por `origClientOrderId` (Fase 10).

    El slug de la estrategia se recorta para respetar los 36 caracteres de Binance; por eso
    `StrategyConfig.name` está limitado a 12 caracteres.
    """
    if open_time_ms < 0:
        msg = f"open_time negativo: {open_time_ms}"
        raise ValueError(msg)
    tag = order_purpose_tag(side, exit_reason)
    fixed = f"{_CID_PREFIX}--{pair.binance_symbol}-{open_time_ms // 1000}-{tag}"
    room = CLIENT_ORDER_ID_MAX_LEN - len(fixed)
    if room < 1:
        msg = f"símbolo {pair.binance_symbol} demasiado largo para un client_order_id"
        raise ValueError(msg)
    slug = _SLUG_RE.sub("", strategy)[:room] or "s"
    cid = f"{_CID_PREFIX}-{slug}-{pair.binance_symbol}-{open_time_ms // 1000}-{tag}"
    if not CLIENT_ORDER_ID_RE.match(cid):  # pragma: no cover - defensa; el slug ya está saneado
        msg = f"client_order_id inválido: {cid}"
        raise ValueError(msg)
    return cid


class Signal(BaseModel):
    """Salida de `Strategy.on_candle` para un par en un cierre.

    `ENTER_LONG` exige `stop_price` (el sizing por riesgo lo necesita) y admite `strength`
    para el ranking cuando hay más señales que slots. `EXIT_LONG` lleva `exit_reason`.
    """

    model_config = ConfigDict(frozen=True)

    action: SignalAction
    pair: Pair
    open_time: int = Field(ge=0, description="open_time de la vela que generó la señal")
    stop_price: Decimal | None = Field(default=None, gt=0)
    strength: float | None = None
    exit_reason: ExitReason | None = None
    note: str = ""

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.action is SignalAction.ENTER_LONG:
            if self.stop_price is None:
                msg = "ENTER_LONG requiere stop_price"
                raise ValueError(msg)
            if self.exit_reason is not None:
                msg = "ENTER_LONG no lleva exit_reason"
                raise ValueError(msg)
        elif self.action is SignalAction.EXIT_LONG:
            if self.exit_reason is None:
                msg = "EXIT_LONG requiere exit_reason"
                raise ValueError(msg)
            if self.stop_price is not None:
                msg = "EXIT_LONG no lleva stop_price"
                raise ValueError(msg)
        elif self.stop_price is not None or self.exit_reason is not None:
            msg = "HOLD no lleva stop_price ni exit_reason"
            raise ValueError(msg)
        return self

    @classmethod
    def hold(cls, pair: Pair, open_time: int, note: str = "") -> Signal:
        return cls(action=SignalAction.HOLD, pair=pair, open_time=open_time, note=note)


class OrderIntent(BaseModel):
    """Decisión ya aprobada por el `RiskManager`, lista para que el `Broker` la ejecute.

    Compras: llevan `stop_price` (el nivel a fijar tras el fill) bajo `decision_price`.
    Ventas: llevan `exit_reason` y no llevan stop.
    """

    model_config = ConfigDict(frozen=True)

    client_order_id: str = Field(pattern=CLIENT_ORDER_ID_RE.pattern)
    strategy: str = Field(min_length=1)
    pair: Pair
    side: Side
    order_type: OrderType = OrderType.MARKET
    qty: Decimal = Field(gt=0)
    limit_price: Decimal | None = Field(default=None, gt=0)
    decision_price: Decimal = Field(gt=0, description="close(t) con el que se decidió")
    stop_price: Decimal | None = Field(default=None, gt=0, description="stop a fijar tras el fill")
    signal_ts: int = Field(ge=0)
    decision_ts: int = Field(ge=0)
    exit_reason: ExitReason | None = None
    note: str = ""

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.decision_ts < self.signal_ts:
            msg = "decision_ts anterior a signal_ts"
            raise ValueError(msg)
        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            msg = "una orden LIMIT requiere limit_price"
            raise ValueError(msg)
        if self.order_type is OrderType.MARKET and self.limit_price is not None:
            msg = "una orden MARKET no lleva limit_price"
            raise ValueError(msg)
        order_purpose_tag(self.side, self.exit_reason)  # valida la combinación lado/motivo
        if self.side is Side.BUY:
            if self.stop_price is None:
                msg = "una compra requiere stop_price"
                raise ValueError(msg)
            if self.stop_price >= self.decision_price:
                msg = (
                    f"stop {self.stop_price} debe estar bajo el precio de decisión "
                    f"{self.decision_price}"
                )
                raise ValueError(msg)
        elif self.stop_price is not None:
            msg = "una venta no lleva stop_price"
            raise ValueError(msg)
        return self

    @property
    def expected_notional(self) -> Decimal:
        return notional(self.decision_price, self.qty)


class Fill(BaseModel):
    """Ejecución (total o parcial) de una orden.

    `ref_price` es el precio de referencia del modelo (open de `t+1`); la diferencia con
    `price` es el *implementation shortfall*, positivo cuando el fill fue peor que la referencia.
    La fee se descuenta del activo recibido salvo que se pague con BNB; en ese caso el broker
    informa además `fee_quote` (la fee convertida a quote) para que el PnL cierre.
    """

    model_config = ConfigDict(frozen=True)

    client_order_id: str = Field(pattern=CLIENT_ORDER_ID_RE.pattern)
    pair: Pair
    side: Side
    price: Decimal = Field(gt=0)
    qty: Decimal = Field(gt=0)
    fee_amount: Decimal = Field(ge=0)
    fee_asset: str = Field(min_length=1)
    fee_quote: Decimal | None = Field(
        default=None, ge=0, description="fee en quote cuando fee_asset no es base ni quote"
    )
    ref_price: Decimal = Field(gt=0)
    signal_ts: int = Field(ge=0)
    decision_ts: int = Field(ge=0)
    fill_ts: int = Field(ge=0)
    exchange_trade_id: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        third_party = self.fee_asset not in (self.pair.base, self.pair.quote)
        if third_party and self.fee_amount > ZERO and self.fee_quote is None:
            msg = f"fee en {self.fee_asset} requiere fee_quote para contabilizar el PnL"
            raise ValueError(msg)
        if not third_party and self.fee_quote is not None:
            msg = "fee_quote solo aplica a fees en un tercer activo"
            raise ValueError(msg)
        return self

    @property
    def notional(self) -> Decimal:
        return notional(self.price, self.qty)

    @property
    def shortfall_bps(self) -> Decimal:
        """Desvío del fill respecto de la referencia, en bps, positivo = peor para nosotros."""
        raw = (self.price - self.ref_price) / self.ref_price
        signed = raw if self.side is Side.BUY else -raw
        return signed * BPS_DENOMINATOR

    @property
    def net_base_qty(self) -> Decimal:
        """Base que queda en la cuenta tras una compra (qty menos fee si se cobró en base)."""
        if self.side is not Side.BUY:
            return ZERO
        return self.qty - self.fee_amount if self.fee_asset == self.pair.base else self.qty

    @property
    def net_quote_amount(self) -> Decimal:
        """Quote que entra tras una venta (notional menos fee si se cobró en quote)."""
        if self.side is not Side.SELL:
            return ZERO
        if self.fee_asset == self.pair.quote:
            return self.notional - self.fee_amount
        return self.notional

    def fee_in_quote(self, reference_price: Decimal | None = None) -> Decimal:
        """Fee expresada en quote para contabilidad de PnL.

        En quote: tal cual. En base: convertida al precio del fill (o a `reference_price`).
        En un tercer activo (BNB): `fee_quote`, que el broker informa.
        """
        if self.fee_asset == self.pair.quote:
            return self.fee_amount
        if self.fee_asset == self.pair.base:
            price = self.price if reference_price is None else reference_price
            return self.fee_amount * price
        return self.fee_quote if self.fee_quote is not None else ZERO


class Order(BaseModel):
    """Estado de una orden enviada al broker. Inmutable: los cambios producen copias validadas."""

    model_config = ConfigDict(frozen=True)

    intent: OrderIntent
    status: OrderStatus = OrderStatus.PENDING
    exchange_order_id: str | None = None
    created_ts: int = Field(ge=0)
    updated_ts: int = Field(ge=0)
    fills: tuple[Fill, ...] = ()
    reject_reason: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.updated_ts < self.created_ts:
            msg = "updated_ts anterior a created_ts"
            raise ValueError(msg)
        seen_trade_ids: set[str] = set()
        for fill in self.fills:
            if fill.client_order_id != self.intent.client_order_id:
                msg = f"fill de {fill.client_order_id} en orden {self.intent.client_order_id}"
                raise ValueError(msg)
            if fill.pair != self.intent.pair or fill.side is not self.intent.side:
                msg = (
                    f"fill de {fill.pair} {fill.side.value} en orden "
                    f"{self.intent.pair} {self.intent.side.value}"
                )
                raise ValueError(msg)
            if fill.exchange_trade_id is not None:
                if fill.exchange_trade_id in seen_trade_ids:
                    msg = f"exchange_trade_id repetido: {fill.exchange_trade_id}"
                    raise ValueError(msg)
                seen_trade_ids.add(fill.exchange_trade_id)
        if self.filled_qty > self.intent.qty:
            msg = f"llenado {self.filled_qty} > pedido {self.intent.qty}"
            raise ValueError(msg)
        return self

    @property
    def client_order_id(self) -> str:
        return self.intent.client_order_id

    @property
    def filled_qty(self) -> Decimal:
        return sum((f.qty for f in self.fills), ZERO)

    @property
    def remaining_qty(self) -> Decimal:
        return self.intent.qty - self.filled_qty

    @property
    def avg_fill_price(self) -> Decimal | None:
        filled = self.filled_qty
        if filled == ZERO:
            return None
        return sum((f.notional for f in self.fills), ZERO) / filled

    @property
    def is_done(self) -> bool:
        return self.status.is_terminal

    def with_fill(self, fill: Fill, ts: int) -> Order:
        """Copia validada con un fill más; pasa a FILLED si completa la cantidad."""
        if self.is_done:
            msg = f"la orden {self.client_order_id} ya está {self.status.value}; no admite fills"
            raise ValueError(msg)
        fills = (*self.fills, fill)
        total = sum((f.qty for f in fills), ZERO)
        status = OrderStatus.FILLED if total >= self.intent.qty else OrderStatus.PARTIALLY_FILLED
        return self._replace(fills=fills, status=status, updated_ts=ts)

    def with_status(self, status: OrderStatus, ts: int, reason: str | None = None) -> Order:
        update: dict[str, object] = {"status": status, "updated_ts": ts}
        if reason is not None:
            update["reject_reason"] = reason
        return self._replace(**update)

    def _replace(self, **update: object) -> Order:
        # `model_copy` no revalida; reconstruimos para que los invariantes se apliquen siempre.
        data = {**self.__dict__, **update}
        return Order.model_validate(data)
