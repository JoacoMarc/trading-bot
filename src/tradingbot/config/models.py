"""Sub-configuraciones tipadas. Ningún secreto vive acá: van por variables de entorno."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe

HOLDOUT_START = date(2025, 9, 1)
# Máximo 12 caracteres: el client_order_id recorta el nombre y dos estrategias con el mismo
# prefijo largo colisionarían en la DB y en el test de paridad.
STRATEGY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,11}$")


class Mode(StrEnum):
    BACKTEST = "backtest"
    PAPER = "paper"
    TESTNET = "testnet"
    LIVE = "live"

    @property
    def requires_keys(self) -> bool:
        return self in {Mode.TESTNET, Mode.LIVE}

    @property
    def is_simulated(self) -> bool:
        """True si las órdenes no llegan a ningún exchange (ni siquiera testnet)."""
        return self in {Mode.BACKTEST, Mode.PAPER}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ExchangeConfig(_Strict):
    name: Literal["binance"] = "binance"
    recv_window_ms: int = Field(default=10_000, ge=1_000, le=60_000)
    request_timeout_ms: int = Field(default=10_000, ge=1_000, le=120_000)


def _parse_pairs(value: Any) -> Any:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list | tuple):
        return value
    pairs: list[Pair] = []
    for item in value:
        if isinstance(item, str):
            pair = Pair.parse(item)
        elif isinstance(item, Pair):
            pair = item
        else:
            pair = Pair.model_validate(item)  # dict serializado por `public_dump`
        if pair in pairs:
            msg = f"par repetido: {pair}"
            raise ValueError(msg)
        pairs.append(pair)
    return tuple(sorted(pairs, key=lambda p: p.symbol))


PairList = Annotated[tuple[Pair, ...], BeforeValidator(_parse_pairs)]


def _parse_timeframes(value: Any) -> Any:
    if isinstance(value, str):
        value = value.split()
    if not isinstance(value, list | tuple):
        return value
    seen: list[Timeframe] = []
    for item in value:
        tf = Timeframe.parse(item) if isinstance(item, str) else item
        if tf in seen:
            msg = f"timeframe repetido: {tf}"
            raise ValueError(msg)
        seen.append(tf)
    return tuple(sorted(seen, key=lambda tf: tf.ms))


TimeframeList = Annotated[tuple[Timeframe, ...], BeforeValidator(_parse_timeframes)]

# Universo v1 (PLAN §2.2): 8 pares USDT líquidos con historia desde 2019–2020.
DEFAULT_UNIVERSE: tuple[Pair, ...] = _parse_pairs(
    [
        "BTC/USDT",
        "ETH/USDT",
        "BNB/USDT",
        "XRP/USDT",
        "ADA/USDT",
        "LTC/USDT",
        "LINK/USDT",
        "SOL/USDT",
    ]
)
DEFAULT_DATA_SINCE = date(2019, 1, 1)


class DataConfig(_Strict):
    """Dónde viven las velas y qué se descarga por defecto con `download-data`."""

    data_dir: Path = Path("data")
    universe: PairList = Field(default=DEFAULT_UNIVERSE, min_length=1)
    timeframes: TimeframeList = Field(default=(Timeframe.H1, Timeframe.H4), min_length=1)
    since: date = DEFAULT_DATA_SINCE
    gaps_file: Path = Path("configs") / "binance_gaps.json"


class StrategyConfig(_Strict):
    name: str
    timeframe: Timeframe = Timeframe.H4
    pairs: PairList = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    warmup_candles: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def _slug(cls, value: str) -> str:
        if not STRATEGY_NAME_RE.match(value):
            msg = f"nombre de estrategia inválido {value!r} (minúsculas, dígitos y _, máx. 12)"
            raise ValueError(msg)
        return value

    @field_validator("timeframe", mode="before")
    @classmethod
    def _parse_timeframe(cls, value: Any) -> Any:
        return Timeframe.parse(value) if isinstance(value, str) else value


class MarketFilterConfig(_Strict):
    """Filtro de mercado a nivel cartera (ADR-0009).

    Habilita entradas solo si el cierre diario del par de referencia supera su EMA diaria y su
    retorno a N días es positivo. Apagado por defecto. Los mínimos bajos existen para tests.
    """

    enabled: bool = False
    benchmark_only: bool = False  # no bloquea entradas; solo habilita el benchmark B&H filtrado
    pair: str = "BTC/USDT"
    average: Literal["ema", "sma"] = "ema"  # media de los cierres diarios
    ema_days: int = Field(default=200, ge=2, le=400)
    momentum_days: int = Field(default=30, ge=1, le=200)

    @field_validator("pair")
    @classmethod
    def _pair_format(cls, value: str) -> str:
        if value.count("/") != 1:
            msg = f"par de referencia inválido {value!r}; usar BASE/QUOTE"
            raise ValueError(msg)
        return value.upper()

    @property
    def reference_pair(self) -> Pair:
        base, quote = self.pair.split("/")
        return Pair(base=base, quote=quote)


class RiskConfig(_Strict):
    risk_per_trade: Decimal = Field(default=Decimal("0.01"), gt=0, le=Decimal("0.05"))
    sizing_mode: Literal["risk", "fraction"] = "risk"  # ADR-0010: fracción fija de la equity
    position_fraction: Decimal = Field(default=Decimal("0.6"), gt=0, le=1)
    max_position_pct: Decimal = Field(default=Decimal("0.25"), gt=0, le=1)
    max_positions: int = Field(default=3, ge=1, le=20)
    max_exposure_pct: Decimal = Field(default=Decimal("1.0"), gt=0, le=1)
    daily_loss_limit_pct: Decimal | None = Field(default=Decimal("0.03"), gt=0, le=1)
    max_drawdown_pct: Decimal | None = Field(default=Decimal("0.20"), gt=0, le=1)
    drawdown_resume_pct: Decimal | None = Field(default=None, gt=0, le=1)  # default: mitad del DD
    drawdown_pause_days: int | None = Field(default=30, ge=1)  # respaldo: reanuda y re-basa
    cooldown_candles_after_stop: int = Field(default=0, ge=0)
    pause_after_consecutive_losses: int | None = Field(default=None, ge=1)
    pause_candles_after_losses: int = Field(default=12, ge=1)  # velas del timeframe
    # `logs/` es bind mount en compose: el host escribe el STOP y el contenedor lo ve.
    kill_switch_file: Path = Path("logs") / "STOP"
    market_filter: MarketFilterConfig = MarketFilterConfig()

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.sizing_mode == "fraction":
            if self.position_fraction > self.max_exposure_pct:
                msg = "position_fraction no puede superar max_exposure_pct (modo fraction)"
                raise ValueError(msg)
        elif self.max_position_pct > self.max_exposure_pct:
            msg = "max_position_pct no puede superar max_exposure_pct"
            raise ValueError(msg)
        if self.drawdown_resume_pct is not None:
            if self.max_drawdown_pct is None:
                msg = "drawdown_resume_pct requiere max_drawdown_pct"
                raise ValueError(msg)
            if self.drawdown_resume_pct >= self.max_drawdown_pct:
                msg = "drawdown_resume_pct debe ser menor que max_drawdown_pct"
                raise ValueError(msg)
        return self

    @property
    def effective_drawdown_resume_pct(self) -> Decimal | None:
        """DD bajo el cual el circuit breaker vuelve a permitir entradas (ADR-0007)."""
        if self.max_drawdown_pct is None:
            return None
        if self.drawdown_resume_pct is not None:
            return self.drawdown_resume_pct
        return self.max_drawdown_pct / 2


class ExecutionConfig(_Strict):
    fee_rate: Decimal = Field(default=Decimal("0.001"), ge=0, le=Decimal("0.01"))
    pay_with_bnb: bool = False
    bnb_fee_rate: Decimal = Field(default=Decimal("0.00075"), ge=0, le=Decimal("0.01"))
    slippage_bps: Decimal = Field(default=Decimal("5"), ge=0, le=500)
    stop_limit_offset_pct: Decimal = Field(default=Decimal("0.005"), ge=0, le=Decimal("0.05"))
    stop_watch_interval_s: int = Field(default=60, ge=5, le=3_600)

    @property
    def effective_fee_rate(self) -> Decimal:
        return self.bnb_fee_rate if self.pay_with_bnb else self.fee_rate


class BacktestConfig(_Strict):
    """Rango del backtest. `start` inclusive, `end` **exclusivo** (primer día que no entra)."""

    start: date | None = None
    end: date | None = None
    include_holdout: bool = False
    holdout_start: date = HOLDOUT_START
    initial_cash: Decimal = Field(default=Decimal("10000"), gt=0)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.start and self.end and self.start >= self.end:
            msg = f"start {self.start} debe ser anterior a end {self.end}"
            raise ValueError(msg)
        effective = self.effective_end
        if self.start and effective and self.start >= effective:
            msg = (
                f"start {self.start} cae dentro del holdout (desde {self.holdout_start}); "
                "usar include_holdout solo en la corrida final"
            )
            raise ValueError(msg)
        return self

    @property
    def effective_end(self) -> date | None:
        """Fin real del backtest: nunca entra en el holdout salvo `include_holdout`."""
        if self.include_holdout:
            return self.end
        if self.end is None or self.end > self.holdout_start:
            return self.holdout_start
        return self.end


class ValidationConfig(_Strict):
    """Defaults de `tradingbot walkforward` / `optimize` (ADR-0008); los flags de la CLI los pisan.

    Va al `config.yaml` congelado de cada `WF-` para que recargarlo reproduzca la corrida.
    """

    is_months: int = Field(default=24, ge=1)
    oos_months: int = Field(default=6, ge=1)
    anchored: bool = False
    optimize: bool = False
    trials: int = Field(default=50, ge=1)
    seed: int = 42
    objective: Literal["sharpe", "calmar", "profit_factor"] = "sharpe"
    min_trades: int = Field(default=40, ge=0)
    plateau: bool = False
    montecarlo_runs: int = Field(default=5_000, ge=100)
    trades_full_min: int = Field(default=100, ge=1)  # ADR-0010: por spec
    trades_oos_min: int = Field(default=40, ge=1)


class NotifyConfig(_Strict):
    timezone: str = "America/Argentina/Buenos_Aires"
    telegram_enabled: bool = False
    daily_summary_hour: int = Field(default=9, ge=0, le=23)

    @field_validator("timezone")
    @classmethod
    def _valid_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            msg = f"zona horaria inválida {value!r}"
            raise ValueError(msg) from exc
        return value


class PersistenceConfig(_Strict):
    db_dir: Path = Path("db")
    logs_dir: Path = Path("logs")
    experiments_dir: Path = Path("experiments")
