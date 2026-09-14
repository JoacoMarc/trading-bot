"""Kill switch por comando (ADR-0007): `tradingbot stop [--flatten]` y `tradingbot resume`.

Escriben o borran el archivo `risk.kill_switch_file` (default `logs/STOP`, bind mount en compose).
El proceso paper/live lo consulta una vez por `Bar`: si existe no abre posiciones; si contiene
`flatten`, además vende todo a mercado al open siguiente. En backtest no se consulta.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
import yaml

from tradingbot.config.models import RiskConfig
from tradingbot.domain.errors import TradingBotError
from tradingbot.risk.protections import FileKillSwitch

risk_app = typer.Typer(add_completion=False)

ENV_VAR = "TRADINGBOT_RISK__KILL_SWITCH_FILE"
ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        "-c",
        help="YAML de configuración; se lee solo risk.kill_switch_file (default: logs/STOP).",
    ),
]


def _switch(config: Path | None) -> FileKillSwitch:
    """Path del interruptor sin construir `BotConfig`: un YAML live sin claves también frena.

    Precedencia: env `TRADINGBOT_RISK__KILL_SWITCH_FILE` > `risk.kill_switch_file` (YAML) > default.
    """
    env = os.environ.get(ENV_VAR)
    if env:
        return FileKillSwitch(Path(env))
    if config is not None:
        if not config.exists():
            msg = f"no existe {config}"
            raise TradingBotError(msg)
        try:
            raw = yaml.safe_load(config.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            msg = f"no se pudo leer {config}: {exc}"
            raise TradingBotError(msg) from exc
        risk = raw.get("risk") if isinstance(raw, dict) else None
        value = risk.get("kill_switch_file") if isinstance(risk, dict) else None
        if value is not None:
            return FileKillSwitch(Path(str(value)))
    return FileKillSwitch(RiskConfig().kill_switch_file)


@risk_app.command("stop")
def stop(
    config: ConfigOption = None,
    flatten: Annotated[
        bool,
        typer.Option("--flatten", help="Además cerrar todas las posiciones a mercado."),
    ] = False,
) -> None:
    """Kill switch: sin nuevas entradas (crea el archivo STOP). Con --flatten cierra todo."""
    try:
        switch = _switch(config)
    except TradingBotError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    switch.activate(flatten=flatten)
    what = "flatten: cerrar todo" if flatten else "sin nuevas entradas"
    typer.echo(f"kill switch activo ({what}): {switch.path}")


@risk_app.command("resume")
def resume(
    config: ConfigOption = None,
    breaker: Annotated[
        bool,
        typer.Option(
            "--breaker",
            help="Además pedir la reanudación manual del circuit breaker (archivo RESUME).",
        ),
    ] = False,
) -> None:
    """Retira el kill switch (borra STOP); con --breaker pide reanudar el circuit breaker."""
    try:
        switch = _switch(config)
    except TradingBotError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if breaker:
        switch.request_resume()
        typer.echo(f"reanudacion del circuit breaker pedida: {switch.resume_path}")
    if not switch.path.exists():
        typer.echo(f"no habia kill switch en {switch.path}")
        return
    switch.clear()
    typer.echo(f"kill switch retirado: {switch.path}")
