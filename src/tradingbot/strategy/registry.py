"""Registro de estrategias por nombre y construcción desde `StrategyConfig`."""

from __future__ import annotations

from tradingbot.config.models import STRATEGY_NAME_RE, StrategyConfig
from tradingbot.domain.errors import ConfigError
from tradingbot.strategy.base import Strategy

_REGISTRY: dict[str, type[Strategy]] = {}


def register[S: type[Strategy]](cls: S) -> S:
    """Decorador: registra la clase bajo `cls.name`. Nombres duplicados son un error."""
    name = getattr(cls, "name", None)
    if not isinstance(name, str) or not STRATEGY_NAME_RE.match(name):
        msg = f"{cls.__name__}.name debe ser snake_case de hasta 12 caracteres, recibido {name!r}"
        raise ValueError(msg)
    existing = _REGISTRY.get(name)
    if existing is not None and existing is not cls:
        msg = f"estrategia {name!r} ya registrada por {existing.__name__}"
        raise ValueError(msg)
    _REGISTRY[name] = cls
    return cls


def available_strategies() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def get_strategy_class(name: str) -> type[Strategy]:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        msg = f"estrategia desconocida {name!r}; disponibles: {', '.join(available_strategies())}"
        raise ConfigError(msg) from exc


def build_strategy(config: StrategyConfig) -> Strategy:
    """Instancia la estrategia de la config validando `params` con su modelo.

    `StrategyConfig.warmup_candles` solo puede **ampliar** el warmup que la estrategia exige;
    uno menor rompería la equivalencia backtest/live y se rechaza.
    """
    cls = get_strategy_class(config.name)
    try:
        params = cls.Params.model_validate(config.params)
    except ValueError as exc:
        msg = f"parámetros inválidos para {config.name!r}: {exc}"
        raise ConfigError(msg) from exc
    strategy = cls(params)
    if config.warmup_candles is not None and config.warmup_candles < strategy.warmup_candles:
        msg = (
            f"strategy.warmup_candles={config.warmup_candles} es menor que el mínimo de "
            f"{config.name!r} ({strategy.warmup_candles}); quitarlo o subirlo"
        )
        raise ConfigError(msg)
    return strategy


def effective_warmup(config: StrategyConfig, strategy: Strategy) -> int:
    """Warmup a usar por el feed: el mayor entre la config y el mínimo de la estrategia."""
    return max(config.warmup_candles or 0, strategy.warmup_candles)
