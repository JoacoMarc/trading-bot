"""CLI principal. Fase 0: `--version` y `doctor`; Fase 2: datos. El resto llega por fase."""

from __future__ import annotations

import contextlib
import sys
from typing import Annotated

import typer

from tradingbot import __version__
from tradingbot.cli.backtest_commands import bt_app, experiments_app
from tradingbot.cli.data_commands import data_app
from tradingbot.cli.risk_commands import risk_app
from tradingbot.doctor import CheckResult, run_all

app = typer.Typer(
    name="tradingbot",
    help="Bot de trading propio para Binance Spot: backtest, paper y live con un solo motor.",
    no_args_is_help=True,
    add_completion=False,
)
# Los comandos de datos se registran al mismo nivel (`tradingbot download-data`, no un subgrupo).
for command in (
    *data_app.registered_commands,
    *bt_app.registered_commands,
    *risk_app.registered_commands,
):
    app.registered_commands.append(command)
app.add_typer(experiments_app, name="experiments")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"tradingbot {__version__}")
        raise typer.Exit()


VersionOption = Annotated[
    bool,
    typer.Option(
        "--version",
        "-V",
        help="Muestra la versión y sale.",
        callback=_version_callback,
        is_eager=True,
    ),
]


@app.callback()
def root(version: VersionOption = False) -> None:
    """Bot de trading propio para Binance Spot."""


def _format(result: CheckResult) -> str:
    mark = "OK  " if result.ok else "FAIL"
    return f"[{mark}] {result.name:<8} {result.detail}"


@app.command()
def doctor() -> None:
    """Verifica el entorno: Python, variables de entorno, conexión y reloj vs Binance."""
    results = run_all()
    for result in results:
        typer.echo(_format(result))
    if not all(result.ok for result in results):
        raise typer.Exit(code=1)


def _tolerate_console_encoding() -> None:
    """Las consolas de Windows en cp1252 no codifican todo Unicode: reemplazar, no crashear.

    La salida de la CLI usa ASCII para símbolos (`->`, `>=`), pero un nombre de activo o un
    mensaje de error del exchange puede traer cualquier carácter.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(Exception):
                reconfigure(errors="replace")


def main() -> None:
    """Punto de entrada del script `tradingbot`."""
    _tolerate_console_encoding()
    app()
