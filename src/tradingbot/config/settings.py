"""`BotConfig`: configuración completa del bot.

Precedencia (de mayor a menor): argumentos de la CLI (`overrides`) > variables de entorno
(`TRADINGBOT_*`, anidadas con `__`) > `.env` > YAML > defaults. Los secretos solo entran por
entorno o `.env`; si aparecen en el YAML o en los overrides la carga falla.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, ClassVar, Self

import yaml
from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from tradingbot.config.models import (
    BacktestConfig,
    DataConfig,
    ExchangeConfig,
    ExecutionConfig,
    Mode,
    NotifyConfig,
    PersistenceConfig,
    RiskConfig,
    StrategyConfig,
    ValidationConfig,
)
from tradingbot.domain.errors import ConfigError

SECRET_FIELDS: frozenset[str] = frozenset(
    {
        "binance_api_key",
        "binance_api_secret",
        "telegram_bot_token",
        "telegram_chat_id",
        "anthropic_api_key",
    }
)

_YAML_LOCK = threading.Lock()


def _secret(env_name: str) -> Any:
    return Field(default=None, validation_alias=AliasChoices(env_name, env_name.lower()))


class _KnownFieldsDotEnv(DotEnvSettingsSource):
    """Lee `.env` pero solo entrega campos conocidos.

    La fuente estándar agrega al payload toda clave del `.env` que no reconoce y, con
    `extra="forbid"`, eso tumba el arranque e imprime el valor en el error de validación
    (un `LOG_LEVEL=debug` ajeno o un typo en el nombre de un secreto). Acá una clave
    desconocida simplemente se ignora.
    """

    def __call__(self) -> dict[str, Any]:
        return EnvSettingsSource.__call__(self)


class BotConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRADINGBOT_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )

    _yaml_file: ClassVar[Path | None] = None

    mode: Mode = Mode.BACKTEST
    exchange: ExchangeConfig = ExchangeConfig()
    data: DataConfig = DataConfig()
    strategy: StrategyConfig
    risk: RiskConfig = RiskConfig()
    execution: ExecutionConfig = ExecutionConfig()
    backtest: BacktestConfig = BacktestConfig()
    validation: ValidationConfig = ValidationConfig()
    notify: NotifyConfig = NotifyConfig()
    persistence: PersistenceConfig = PersistenceConfig()

    # Secretos: sin prefijo TRADINGBOT_, nunca desde YAML ni desde --set.
    binance_api_key: SecretStr | None = _secret("BINANCE_API_KEY")
    binance_api_secret: SecretStr | None = _secret("BINANCE_API_SECRET")
    telegram_bot_token: SecretStr | None = _secret("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: SecretStr | None = _secret("TELEGRAM_CHAT_ID")
    anthropic_api_key: SecretStr | None = _secret("ANTHROPIC_API_KEY")

    @model_validator(mode="after")
    def _cross_checks(self) -> Self:
        if self.mode.requires_keys and not self.has_binance_keys:
            msg = f"el modo {self.mode.value} requiere BINANCE_API_KEY y BINANCE_API_SECRET"
            raise ValueError(msg)
        if self.notify.telegram_enabled and not (self.telegram_bot_token and self.telegram_chat_id):
            msg = "notify.telegram_enabled requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID"
            raise ValueError(msg)
        return self

    @property
    def has_binance_keys(self) -> bool:
        return bool(self.binance_api_key and self.binance_api_secret)

    @property
    def db_path(self) -> Path:
        return self.persistence.db_dir / f"{self.mode.value}.db"

    def public_dump(self) -> dict[str, Any]:
        """Configuración serializable sin secretos (para congelar en `experiments/runs/`).

        Es recargable con `BotConfig.load(overrides=cfg.public_dump())`.
        """
        return self.model_dump(mode="json", exclude=set(SECRET_FIELDS))

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        env_file = getattr(dotenv_settings, "env_file", None)
        sources: list[PydanticBaseSettingsSource] = [
            init_settings,
            env_settings,
            _KnownFieldsDotEnv(settings_cls, env_file=env_file),
        ]
        if cls._yaml_file is not None:
            sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=cls._yaml_file))
        return tuple(sources)

    @classmethod
    def load(
        cls,
        yaml_path: str | Path | None = None,
        overrides: Mapping[str, Any] | None = None,
        env_file: str | Path | None = ".env",
    ) -> BotConfig:
        """Carga la configuración con la precedencia documentada en el módulo.

        `overrides` es un dict anidado (ver `config.overrides.parse_set`). `env_file=None`
        desactiva la lectura de `.env` (útil en tests).
        """
        path = Path(yaml_path) if yaml_path is not None else None
        if path is not None:
            _reject_secrets_in_yaml(path)
        if overrides:
            leaked = _find_secret_keys(overrides)
            if leaked:
                msg = f"los secretos no se pasan por --set ({', '.join(leaked)}); van en .env"
                raise ConfigError(msg)
        with _yaml_source(cls, path):
            return cls(_env_file=env_file, **dict(overrides or {}))


def _find_secret_keys(data: Mapping[str, Any], prefix: str = "") -> list[str]:
    """Rutas (`a.b.c`) de toda clave que coincida con un secreto, a cualquier profundidad."""
    found: list[str] = []
    for key, value in data.items():
        path = f"{prefix}{key}"
        if str(key).lower() in SECRET_FIELDS:
            found.append(path)
        if isinstance(value, Mapping):
            found.extend(_find_secret_keys(value, f"{path}."))
    return found


def _reject_secrets_in_yaml(path: Path) -> None:
    if not path.exists():
        msg = f"no existe el archivo de configuración {path}"
        raise ConfigError(msg)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        msg = f"{path} debe contener un mapa YAML en la raíz"
        raise ConfigError(msg)
    leaked = _find_secret_keys(data)
    if leaked:
        msg = f"{path} contiene secretos ({', '.join(leaked)}); van en .env, nunca en YAML"
        raise ConfigError(msg)


@contextmanager
def _yaml_source(cls: type[BotConfig], path: Path | None) -> Iterator[None]:
    # El lock cubre el caso de cargas concurrentes (optuna con n_jobs > 1).
    with _YAML_LOCK:
        previous = cls._yaml_file
        cls._yaml_file = path
        try:
            yield
        finally:
            cls._yaml_file = previous
