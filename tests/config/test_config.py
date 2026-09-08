from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tradingbot.config import (
    HOLDOUT_START,
    BacktestConfig,
    BotConfig,
    Mode,
    NotifyConfig,
    RiskConfig,
    StrategyConfig,
    deep_merge,
    parse_set,
)
from tradingbot.domain import ConfigError, Pair, Timeframe

ROOT = Path(__file__).resolve().parents[2]
MINIMAL: dict[str, Any] = {"strategy": {"name": "ema_trend", "pairs": ["BTC/USDT"]}}


def load(overrides: dict[str, Any] | None = None, yaml_path: Path | None = None) -> BotConfig:
    return BotConfig.load(yaml_path, overrides=overrides, env_file=None)


def write_yaml(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults() -> None:
    cfg = load(MINIMAL)
    assert cfg.mode is Mode.BACKTEST
    assert cfg.strategy.timeframe is Timeframe.H4
    assert cfg.strategy.pairs == (Pair.parse("BTC/USDT"),)
    assert cfg.risk.risk_per_trade == Decimal("0.01")
    assert cfg.execution.effective_fee_rate == Decimal("0.001")
    assert cfg.backtest.effective_end == HOLDOUT_START
    assert cfg.db_path == Path("db") / "backtest.db"
    assert not cfg.has_binance_keys


@pytest.mark.parametrize("name", ["backtest.example.yaml", "paper.example.yaml"])
def test_example_configs_load(name: str) -> None:
    cfg = load(yaml_path=ROOT / "configs" / name)
    assert cfg.strategy.name == "ema_trend"
    assert cfg.strategy.pairs == (Pair.parse("BTC/USDT"), Pair.parse("ETH/USDT"))
    assert cfg.strategy.params["ema_fast"] == 20
    assert cfg.mode is (Mode.PAPER if "paper" in name else Mode.BACKTEST)


def test_precedence_cli_over_env_over_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_yaml(
        tmp_path,
        "strategy: {name: ema_trend, pairs: [BTC/USDT]}\nrisk: {max_positions: 5}\nmode: paper\n",
    )
    assert load(yaml_path=path).risk.max_positions == 5

    monkeypatch.setenv("TRADINGBOT_RISK__MAX_POSITIONS", "4")
    monkeypatch.setenv("TRADINGBOT_MODE", "backtest")
    from_env = load(yaml_path=path)
    assert from_env.risk.max_positions == 4
    assert from_env.mode is Mode.BACKTEST

    from_cli = load({"risk": {"max_positions": 2}}, yaml_path=path)
    assert from_cli.risk.max_positions == 2
    assert from_cli.mode is Mode.BACKTEST


def test_secrets_come_from_env_and_are_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "key-123")
    monkeypatch.setenv("BINANCE_API_SECRET", "secret-456")
    cfg = load(MINIMAL)
    assert cfg.has_binance_keys
    assert cfg.binance_api_key is not None
    assert cfg.binance_api_key.get_secret_value() == "key-123"
    assert "key-123" not in repr(cfg)
    dumped = cfg.public_dump()
    assert "binance_api_key" not in dumped
    assert dumped["strategy"]["pairs"] == [{"base": "BTC", "quote": "USDT"}]


def test_live_and_testnet_require_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for mode in ("live", "testnet"):
        with pytest.raises(ValidationError, match="requiere BINANCE_API_KEY"):
            load(MINIMAL | {"mode": mode})
    monkeypatch.setenv("BINANCE_API_KEY", "k")
    monkeypatch.setenv("BINANCE_API_SECRET", "s")
    assert load(MINIMAL | {"mode": "live"}).mode is Mode.LIVE
    assert Mode.LIVE.requires_keys
    assert not Mode.LIVE.is_simulated
    assert Mode.PAPER.is_simulated
    assert not Mode.PAPER.requires_keys


def test_paper_ignores_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "k")
    monkeypatch.setenv("BINANCE_API_SECRET", "s")
    assert load(MINIMAL | {"mode": "paper"}).mode is Mode.PAPER


def test_telegram_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="TELEGRAM_BOT_TOKEN"):
        load(MINIMAL | {"notify": {"telegram_enabled": True}})
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    assert load(MINIMAL | {"notify": {"telegram_enabled": True}}).notify.telegram_enabled


def test_yaml_with_secrets_is_rejected(tmp_path: Path) -> None:
    path = write_yaml(tmp_path, "strategy: {name: x, pairs: [BTC/USDT]}\nBINANCE_API_KEY: abc\n")
    with pytest.raises(ConfigError, match="contiene secretos"):
        load(yaml_path=path)


def test_yaml_missing_or_malformed(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no existe"):
        load(yaml_path=tmp_path / "nope.yaml")
    with pytest.raises(ConfigError, match="mapa YAML"):
        load(yaml_path=write_yaml(tmp_path, "- 1\n- 2\n"))


def test_unknown_keys_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        load(MINIMAL | {"risk": {"max_positons": 2}})
    with pytest.raises(ValidationError, match="Extra inputs"):
        load(yaml_path=write_yaml(tmp_path, "strategy: {name: x, pairs: [BTC/USDT]}\nfoo: 1\n"))


def test_strategy_config_rules() -> None:
    cfg = StrategyConfig(name="ema_trend", timeframe="1h", pairs="ETH/USDT")
    assert cfg.timeframe is Timeframe.H1
    assert cfg.pairs == (Pair.parse("ETH/USDT"),)
    sorted_pairs = StrategyConfig(name="s", pairs=["ETH/USDT", "BTC/USDT"]).pairs
    assert [p.symbol for p in sorted_pairs] == ["BTC/USDT", "ETH/USDT"]
    with pytest.raises(ValidationError, match="repetido"):
        StrategyConfig(name="s", pairs=["BTC/USDT", "btcusdt"])
    with pytest.raises(ValidationError, match="nombre de estrategia"):
        StrategyConfig(name="Ema-Trend", pairs=["BTC/USDT"])
    with pytest.raises(ValidationError, match="no soportado"):
        StrategyConfig(name="s", pairs=["BTC/BUSD"])
    with pytest.raises(ValidationError):
        StrategyConfig(name="s", pairs=[])


def test_risk_and_backtest_rules() -> None:
    with pytest.raises(ValidationError, match="max_exposure_pct"):
        RiskConfig(max_position_pct=Decimal("0.9"), max_exposure_pct=Decimal("0.5"))
    with pytest.raises(ValidationError):
        RiskConfig(risk_per_trade=Decimal("0.1"))
    with pytest.raises(ValidationError, match="anterior"):
        BacktestConfig(start=date(2024, 1, 1), end=date(2023, 1, 1))
    clamped = BacktestConfig(start=date(2019, 1, 1), end=date(2026, 6, 1))
    assert clamped.effective_end == HOLDOUT_START
    assert BacktestConfig(end=date(2024, 1, 1)).effective_end == date(2024, 1, 1)
    assert BacktestConfig(end=date(2026, 6, 1), include_holdout=True).effective_end == date(
        2026, 6, 1
    )
    assert BacktestConfig(include_holdout=True).effective_end is None


def test_notify_timezone_validated() -> None:
    assert NotifyConfig(timezone="UTC").timezone == "UTC"
    with pytest.raises(ValidationError, match="zona horaria"):
        NotifyConfig(timezone="Marte/Olympus")


def test_parse_set_types_and_nesting() -> None:
    result = parse_set(
        [
            "risk.max_positions=2",
            "strategy.params.ema_fast=15",
            "strategy.params.entry_mode=state",
            "mode=paper",
            "backtest.include_holdout=true",
            "strategy.pairs=[BTC/USDT, ETH/USDT]",
        ]
    )
    assert result == {
        "risk": {"max_positions": 2},
        "strategy": {
            "params": {"ema_fast": 15, "entry_mode": "state"},
            "pairs": ["BTC/USDT", "ETH/USDT"],
        },
        "mode": "paper",
        "backtest": {"include_holdout": True},
    }
    assert parse_set(["strategy.name="])["strategy"]["name"] == ""
    assert parse_set([]) == {}


def test_parse_set_errors() -> None:
    with pytest.raises(ConfigError, match="formato esperado"):
        parse_set(["sin_igual"])
    with pytest.raises(ConfigError, match="formato esperado"):
        parse_set(["=valor"])
    with pytest.raises(ConfigError, match="escalar"):
        parse_set(["a=1", "a.b=2"])
    with pytest.raises(ConfigError, match="clave vacía"):
        parse_set(["a..b=1"])
    with pytest.raises(ConfigError, match="valor inválido"):
        parse_set(["a=[unclosed"])


def test_parse_set_feeds_load() -> None:
    cfg = load(deep_merge(MINIMAL, parse_set(["risk.max_positions=1", "strategy.timeframe=1h"])))
    assert cfg.risk.max_positions == 1
    assert cfg.strategy.timeframe is Timeframe.H1


def test_public_dump_round_trips() -> None:
    cfg = load(yaml_path=ROOT / "configs" / "paper.example.yaml")
    reloaded = load(cfg.public_dump())
    assert reloaded == cfg
    assert reloaded.strategy.pairs == cfg.strategy.pairs


def test_dotenv_is_read_with_expected_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = write_yaml(
        tmp_path, "strategy: {name: ema_trend, pairs: [BTC/USDT]}\nrisk: {max_positions: 5}\n"
    )
    env_path = tmp_path / ".env"
    env_path.write_text(
        "TRADINGBOT_RISK__MAX_POSITIONS=4\n"
        "BINANCE_API_KEY=from-dotenv\n"
        "LOG_LEVEL=debug\n"  # clave ajena: no debe romper ni filtrarse
        "BINANCE_API_SECERT=typo-secreto\n",
        encoding="utf-8",
    )
    cfg = BotConfig.load(yaml_path, env_file=env_path)
    assert cfg.risk.max_positions == 4
    assert cfg.binance_api_key is not None
    assert cfg.binance_api_key.get_secret_value() == "from-dotenv"
    assert cfg.binance_api_secret is None

    monkeypatch.setenv("TRADINGBOT_RISK__MAX_POSITIONS", "3")
    assert BotConfig.load(yaml_path, env_file=env_path).risk.max_positions == 3


def test_secrets_via_overrides_are_rejected() -> None:
    with pytest.raises(ConfigError, match="no se pasan por --set"):
        load(MINIMAL | {"binance_api_key": "x"})
    with pytest.raises(ConfigError, match=r"strategy\.params\.anthropic_api_key"):
        load(
            {"strategy": {"name": "s", "pairs": ["BTC/USDT"], "params": {"anthropic_api_key": "x"}}}
        )


def test_nested_secrets_in_yaml_are_rejected(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        "strategy:\n  name: x\n  pairs: [BTC/USDT]\n  params:\n    telegram_bot_token: abc\n",
    )
    with pytest.raises(ConfigError, match=r"strategy\.params\.telegram_bot_token"):
        load(yaml_path=path)


def test_backtest_start_inside_holdout_is_rejected() -> None:
    with pytest.raises(ValidationError, match="dentro del holdout"):
        BacktestConfig(start=date(2025, 10, 1))
    assert BacktestConfig(start=date(2025, 10, 1), include_holdout=True).start == date(2025, 10, 1)


def test_strategy_name_length_limit() -> None:
    assert StrategyConfig(name="ema_trend_v1", pairs=["BTC/USDT"]).name == "ema_trend_v1"
    with pytest.raises(ValidationError, match=r"máx\. 12"):
        StrategyConfig(name="ema_trend_v1b", pairs=["BTC/USDT"])


def test_deep_merge() -> None:
    base = {"a": {"x": 1, "y": 2}, "b": 1}
    merged = deep_merge(base, {"a": {"y": 3, "z": 4}, "c": 5})
    assert merged == {"a": {"x": 1, "y": 3, "z": 4}, "b": 1, "c": 5}
    assert base == {"a": {"x": 1, "y": 2}, "b": 1}
    assert deep_merge({"a": {"x": 1}}, {"a": 2}) == {"a": 2}
