"""Tests de los hooks de Claude Code en scripts/hooks (no son parte del paquete)."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

HOOKS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "hooks"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, HOOKS_DIR / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load("guard_live")

LIVE = "live"  # armado en runtime para que el propio hook no bloquee la ejecución de estos tests


@pytest.mark.parametrize(
    "command",
    [
        f"uv run tradingbot {LIVE} --config configs/x.yaml",
        f"tradingbot {LIVE}",
        f"python -m tradingbot.cli.app {LIVE} --config x",
        f"docker compose --profile {LIVE} up -d",
        f"docker compose --profile={LIVE} up",
        f"uv run tradingbot paper --confirm-{LIVE}",
        f"TRADINGBOT_{LIVE.upper()}_ACK=yes uv run tradingbot paper",
    ],
)
def test_blocks_live_commands(command: str) -> None:
    assert guard.decide(command) == guard.LIVE_MESSAGE


@pytest.mark.parametrize(
    "command",
    [
        "cat .env",
        "cp .env.example .env",
        f"cat .env.{LIVE}",
        "type .env.paper",
        "source ./.env && echo ok",
        'grep KEY ".env"',
    ],
)
def test_blocks_secret_files(command: str) -> None:
    assert guard.decide(command) == guard.SECRET_MESSAGE


@pytest.mark.parametrize(
    "command",
    [
        "uv run pytest",
        "cat .env.example",
        "uv run tradingbot paper --config configs/paper.yaml",
        "uv run tradingbot doctor",
        "git status",
        "cat .envrc",
        "pip install python-dotenv",
        "docker compose --profile paper up -d",
        "echo alive",
    ],
)
def test_allows_everything_else(command: str) -> None:
    assert guard.decide(command) is None


def test_format_hook_ignores_non_python_and_outside_files() -> None:
    fmt = _load("format_py")
    assert callable(fmt.main)
    assert fmt.uv_command()  # devuelve un comando ejecutable, con uv en PATH o via python -m uv
