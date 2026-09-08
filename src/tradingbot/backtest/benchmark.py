"""Benchmarks buy & hold, calculados aparte del `Engine` (no son estrategias).

Compra al open de la primera vela del rango con los mismos costos que el bot (slippage, fee en
el activo recibido, cuantización al `stepSize`), mantiene hasta el final y marca a mercado con
el close de cada vela. La curva arranca en `initial_cash` (antes de pagar los costos de entrada)
para ser comparable con la estrategia, cuyo primer snapshot también vale `initial_cash`.
Sirve de referencia en cada `REPORT.md` y como experimentos propios (EXP-0001 BTC,
EXP-0002 equiponderado).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, ROUND_UP, Decimal

from tradingbot.backtest.metrics import EquityPoint, Metrics, compute_metrics
from tradingbot.config.models import ExecutionConfig
from tradingbot.domain.candle import Candle
from tradingbot.domain.enums import Side
from tradingbot.domain.errors import DataError
from tradingbot.domain.money import BPS_DENOMINATOR, ONE, ZERO, quantize_price, quantize_qty
from tradingbot.domain.orders import Fill, make_client_order_id
from tradingbot.domain.pair import Pair
from tradingbot.exchange.binance import MarketInfo

FEE_QUANTUM = Decimal("1e-8")


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    name: str
    weights: dict[Pair, Decimal]
    equity: list[EquityPoint]
    fills: list[Fill]
    metrics: Metrics
    leftover_cash: Decimal


def equal_weights(pairs: Sequence[Pair]) -> dict[Pair, Decimal]:
    if not pairs:
        msg = "se necesita al menos un par"
        raise ValueError(msg)
    weight = ONE / Decimal(len(pairs))
    return {pair: weight for pair in pairs}


def buy_and_hold(
    name: str,
    candles_by_pair: Mapping[Pair, Sequence[Candle]],
    weights: Mapping[Pair, Decimal],
    initial_cash: Decimal,
    execution: ExecutionConfig,
    markets: Mapping[Pair, MarketInfo],
) -> BenchmarkResult:
    """Equity de comprar y mantener con `weights` (deben sumar ≤ 1)."""
    if sum(weights.values(), ZERO) > ONE + Decimal("1e-9"):
        msg = f"los pesos suman más de 1: {sum(weights.values(), ZERO)}"
        raise ValueError(msg)
    for pair in weights:
        if not candles_by_pair.get(pair):
            msg = f"sin velas de {pair} para el benchmark {name}"
            raise DataError(msg)

    slippage = execution.slippage_bps / BPS_DENOMINATOR
    cash = initial_cash
    holdings: dict[Pair, Decimal] = {}
    fills: list[Fill] = []
    last_close: dict[Pair, Decimal] = {}

    for pair, weight in weights.items():
        candles = candles_by_pair[pair]
        market = markets[pair]
        first = candles[0]
        price = quantize_price(first.open * (ONE + slippage), market.tick_size, ROUND_UP)
        budget = initial_cash * weight
        if execution.pay_with_bnb:
            budget /= ONE + execution.bnb_fee_rate
        qty = quantize_qty(budget / price, market.step_size)
        if qty <= ZERO:
            continue
        notional = price * qty
        if execution.pay_with_bnb:
            fee_asset = pair.quote
            fee_amount = (notional * execution.bnb_fee_rate).quantize(FEE_QUANTUM, ROUND_HALF_UP)
            net_qty = qty
            cash -= notional + fee_amount
        else:
            fee_asset = pair.base
            fee_amount = (qty * execution.fee_rate).quantize(FEE_QUANTUM, ROUND_HALF_UP)
            net_qty = qty - fee_amount
            cash -= notional
        holdings[pair] = net_qty
        fills.append(
            Fill(
                client_order_id=make_client_order_id(name, pair, first.open_time, Side.BUY),
                pair=pair,
                side=Side.BUY,
                price=price,
                qty=qty,
                fee_amount=fee_amount,
                fee_asset=fee_asset,
                ref_price=first.open,
                signal_ts=first.open_time,
                decision_ts=first.open_time,
                fill_ts=first.open_time,
            )
        )

    by_time: dict[Pair, dict[int, Candle]] = {
        pair: {c.open_time: c for c in candles_by_pair[pair]} for pair in weights
    }
    times: set[int] = set()
    for candles_at in by_time.values():
        times.update(candles_at)
    ordered = sorted(times)
    equity: list[EquityPoint] = [(ordered[0], initial_cash)]  # antes de comprar
    for open_time in ordered:
        value = cash
        close_time = open_time
        for pair in weights:
            candle = by_time[pair].get(open_time)
            if candle is not None:
                last_close[pair] = candle.close
                close_time = candle.close_time
            mark = last_close.get(pair)
            if mark is not None and pair in holdings:
                value += holdings[pair] * mark
        equity.append((close_time, value))

    invested = [False, *([True] * len(ordered))]
    metrics = compute_metrics(equity, invested, [], fills)
    return BenchmarkResult(
        name=name,
        weights=dict(weights),
        equity=equity,
        fills=fills,
        metrics=metrics,
        leftover_cash=cash,
    )
