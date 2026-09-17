"""CLI de paper trading (ADR-0011): `paper`, `status` y `trades`.

`paper` corre el proceso de larga duración (en Docker lo lanza el usuario con
`docker compose --profile paper up -d`); `status` lee `logs/status.json` sin abrir la DB
(`--check` es el HEALTHCHECK); `trades` lista los round trips de la DB de un modo.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from tradingbot.config.overrides import deep_merge, parse_set
from tradingbot.config.settings import BotConfig
from tradingbot.domain.errors import TradingBotError
from tradingbot.exchange.binance import BinanceExchange
from tradingbot.observability.status import heartbeat_age_ms, is_stale, read_status
from tradingbot.paper.runner import PaperExchange, build_paper_session
from tradingbot.persistence.sqlite import SqliteStore
from tradingbot.validation.parity import (
    FILL_DEVIATION_MAX_BPS,
    SIGNAL_MATCH_MIN,
    run_parity,
)

paper_app = typer.Typer(add_completion=False)

DEFAULT_CONFIG = Path("configs") / "paper.yaml"
DEFAULT_STATUS = Path("logs") / "status.json"
ExchangeFactory = Callable[[BotConfig], PaperExchange]


def make_exchange(config: BotConfig) -> PaperExchange:
    """Cliente público de Binance: el paper no necesita claves."""
    return BinanceExchange.create(
        timeout_ms=config.exchange.request_timeout_ms,
        recv_window_ms=config.exchange.recv_window_ms,
    )


# Punto de inyección para tests.
exchange_factory: ExchangeFactory = make_exchange


def _fail(exc: Exception) -> None:
    typer.echo(f"error: {exc}", err=True)
    raise typer.Exit(code=1)


def _load_config(config: Path, overrides: Mapping[str, Any]) -> BotConfig:
    if not config.exists():
        msg = f"no existe {config}; copiar configs/paper.example.yaml a {config}"
        raise TradingBotError(msg)
    return BotConfig.load(config, overrides=overrides)


def _iso(ts_ms: Any) -> str:
    try:
        return datetime.fromtimestamp(int(ts_ms) / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError, OSError):
        return "-"


@paper_app.command("paper")
def paper(
    config: Annotated[
        Path, typer.Option("--config", "-c", help="YAML de configuración (mode: paper).")
    ] = DEFAULT_CONFIG,
    set_values: Annotated[
        list[str] | None, typer.Option("--set", "-s", help="Override clave.sub=valor (repetible).")
    ] = None,
    max_bars: Annotated[
        int | None, typer.Option("--max-bars", min=1, help="Procesar N velas y salir (pruebas).")
    ] = None,
    log_level: Annotated[str, typer.Option("--log-level", help="DEBUG, INFO, WARNING.")] = "INFO",
) -> None:
    """Paper trading con precios en vivo de Binance y órdenes simuladas (ADR-0011)."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        overrides: dict[str, Any] = {}
        for item in set_values or []:
            overrides = deep_merge(overrides, parse_set(item))
        cfg = _load_config(config, overrides)
        session = build_paper_session(cfg, exchange_factory(cfg))
        typer.echo(
            f"paper {session.strategy.name} {cfg.strategy.timeframe.value} "
            f"{', '.join(p.symbol for p in cfg.strategy.pairs)} -> {session.store.path}; "
            f"status en {session.status.path}; avisos por {session.notifier.status()['backend']}; "
            f"{'reanudado desde la DB' if session.restored else 'arranque limpio'}"
        )
        processed = asyncio.run(session.run(max_bars=max_bars))
        typer.echo(f"paper detenido tras {processed} velas")
    except (TradingBotError, ValueError, OSError) as exc:
        _fail(exc)


@paper_app.command("status")
def status(
    file: Annotated[
        Path, typer.Option("--file", "-f", help="Ruta de status.json (default: logs/status.json).")
    ] = DEFAULT_STATUS,
    check: Annotated[
        bool, typer.Option("--check", help="Solo el heartbeat: código 1 si está vencido.")
    ] = False,
    grace_s: Annotated[
        int, typer.Option("--grace", min=0, help="Gracia en segundos sobre 2 x timeframe.")
    ] = 300,
) -> None:
    """Muestra `logs/status.json` (equity, posiciones, protecciones, últimos eventos)."""
    data = read_status(file)
    now_ms = int(time.time() * 1000)
    if data is None:
        typer.echo(f"sin status en {file}", err=True)
        raise typer.Exit(code=1)
    stale = is_stale(data, now_ms, grace_ms=grace_s * 1000)
    age = heartbeat_age_ms(data, now_ms)
    if check:
        typer.echo(
            f"{'VENCIDO' if stale else 'OK'} heartbeat hace "
            f"{'-' if age is None else f'{age // 1000} s'} ({data.get('phase', '-')})"
        )
        raise typer.Exit(code=1 if stale else 0)
    typer.echo(
        f"{data.get('mode', '-')} {data.get('strategy', '-')} {data.get('timeframe', '-')} "
        f"{', '.join(data.get('pairs', []))} · fase {data.get('phase', '-')} · "
        f"heartbeat {data.get('heartbeat_utc', '-')} "
        f"({'-' if age is None else f'hace {age // 1000} s'}{', VENCIDO' if stale else ''})"
    )
    typer.echo(
        f"ultima vela {data.get('last_bar_utc', '-')} · "
        f"proximo cierre {data.get('next_close_utc', '-')}"
    )
    typer.echo(f"equity {data.get('equity', '-')} · cash {data.get('cash', '-')}")
    positions = data.get("positions") or []
    if positions:
        for p in positions:
            typer.echo(
                f"  {p.get('pair')}: qty {p.get('qty')} @ {p.get('entry_price')} stop "
                f"{p.get('stop_price')} mark {p.get('mark')} pnl {p.get('unrealized_pnl')}"
                f"{'' if p.get('stop_published') else ' (SIN STOP PUBLICADO)'}"
            )
    else:
        typer.echo("  sin posiciones")
    pending = data.get("pending_orders") or []
    if pending:
        typer.echo(f"ordenes pendientes: {', '.join(pending)}")
    protections = data.get("protections") or {}
    active = {
        k: v
        for k, v in protections.items()
        if v not in ("False", "", "off", "habilitado") and k != "peak_equity"
    }
    typer.echo(
        f"protecciones: {active if active else 'ninguna activa'} · kill switch "
        f"{'ACTIVO' if data.get('kill_switch_active') else 'off'} ({data.get('kill_switch_file')})"
    )
    stats = data.get("stats") or {}
    typer.echo(
        f"velas {stats.get('bars', 0)}, fills {stats.get('fills', 0)}, rechazos "
        f"{stats.get('rejections', {})}, errores de precio {stats.get('price_errors', 0)}"
    )
    notify = data.get("notify") or {}
    if notify:
        typer.echo(
            f"avisos ({notify.get('backend', '-')}): enviados {notify.get('sent', 0)}, errores "
            f"{notify.get('errors', 0)}, descartados {notify.get('dropped', 0)}, en cola "
            f"{notify.get('queued', 0)}"
        )
    for line in (data.get("recent_events") or [])[-8:]:
        typer.echo(f"  {line}")
    if stale:
        raise typer.Exit(code=1)


@paper_app.command("telegram-test")
def telegram_test(
    config: Annotated[
        Path, typer.Option("--config", "-c", help="YAML de configuración (para notify.*).")
    ] = DEFAULT_CONFIG,
    seconds: Annotated[
        int, typer.Option("--seconds", min=1, help="Cuánto esperar un comando de respuesta.")
    ] = 30,
) -> None:
    """Manda un mensaje de prueba por Telegram y espera un comando: valida token y chat_id.

    Los secretos se leen del entorno (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID); no hace falta que
    `notify.telegram_enabled` esté en true.
    """
    try:
        cfg = _load_config(config, {})
        token, chat_id = cfg.telegram_bot_token, cfg.telegram_chat_id
        if token is None or chat_id is None:
            msg = "faltan TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en el entorno"
            raise TradingBotError(msg)
        from tradingbot.notify.telegram import run_smoke_test  # import pesado: solo acá

        result, received = asyncio.run(
            run_smoke_test(token.get_secret_value(), chat_id.get_secret_value(), seconds=seconds)
        )
    except (TradingBotError, ValueError, OSError) as exc:
        _fail(exc)
        return
    typer.echo(
        f"telegram: enviados {result['sent']}, errores {result['errors']}, "
        f"comandos recibidos {result['commands']}"
    )
    if received:
        typer.echo(f"recibido: {received[0]}")
    else:
        typer.echo(f"no llego ningun mensaje del chat en {seconds} s")
    if not result["sent"]:
        typer.echo("error: el mensaje de prueba no se pudo enviar (token, chat_id o red)", err=True)
        raise typer.Exit(code=1)


@paper_app.command("trades")
def trades(
    db: Annotated[
        Path, typer.Option("--db", help="DB SQLite del modo (p. ej. db/paper.db).")
    ] = Path("db") / "paper.db",
    last: Annotated[int, typer.Option("--last", min=1, help="Cantidad de trades a mostrar.")] = 20,
) -> None:
    """Lista los últimos round trips cerrados de una DB de paper/testnet/live."""
    if not db.exists():
        typer.echo(f"no existe {db}", err=True)
        raise typer.Exit(code=1)
    try:
        with SqliteStore(db) as store:
            rows = store.trades()[-last:]
            positions = store.load_open_positions()
    except TradingBotError as exc:
        _fail(exc)
        return
    if not rows:
        typer.echo("sin trades cerrados")
    for t in rows:
        typer.echo(
            f"{_iso(t.entry_time)} -> {_iso(t.exit_time)} {t.pair.symbol} {t.qty} @ "
            f"{t.entry_price} -> {t.exit_price} {t.exit_reason.value} pnl {t.pnl:+.2f} "
            f"({t.pnl_pct * 100:+.2f} %)"
        )
    if positions:
        typer.echo(
            "abiertas: "
            + ", ".join(f"{p.pair.symbol} {p.qty} @ {p.entry_price}" for p in positions)
        )


@paper_app.command("parity")
def parity(
    config: Annotated[
        Path, typer.Option("--config", "-c", help="YAML con la misma config que corrió el paper.")
    ] = DEFAULT_CONFIG,
    db: Annotated[Path, typer.Option("--db", help="DB SQLite del paper.")] = Path("db")
    / "paper.db",
    start: Annotated[str, typer.Option("--from", help="Desde (YYYY-MM-DD).")] = "",
    end: Annotated[str, typer.Option("--to", help="Hasta, exclusivo (YYYY-MM-DD).")] = "",
    experiments_dir: Annotated[
        Path, typer.Option("--experiments-dir", help="Raíz del registro (default: experiments).")
    ] = Path("experiments"),
    label: Annotated[str | None, typer.Option("--label", help="Etiqueta del PAR-.")] = None,
) -> None:
    """Re-ejecuta el backtest sobre el período del paper y compara señales y fills (Gate 2)."""
    try:
        if not start or not end:
            msg = "--from y --to son obligatorios (YYYY-MM-DD)"
            raise TradingBotError(msg)
        if not db.exists():
            msg = f"no existe {db}"
            raise TradingBotError(msg)
        cfg = _load_config(config, {})
        result, run_dir = run_parity(
            cfg,
            db,
            date.fromisoformat(start),
            date.fromisoformat(end),
            experiments_dir=experiments_dir,
            root=Path.cwd(),
            label=label,
        )
    except (TradingBotError, ValueError, OSError) as exc:
        _fail(exc)
        return
    typer.echo(
        f"paridad {result.signal_match_rate * 100:.1f} % de senales coincidentes "
        f"({result.common_ids} comunes, {len(result.only_paper)} solo paper, "
        f"{len(result.only_backtest)} solo backtest); desvio medio del fill "
        f"{result.mean_abs_deviation_bps:.2f} bps (max {result.max_abs_deviation_bps:.2f})"
    )
    typer.echo(
        f"gate 2 (paridad): {'aprobado' if result.passes_gate2 else 'no aprobado'} "
        f"(>= {SIGNAL_MATCH_MIN * 100:.0f} % y <= {FILL_DEVIATION_MAX_BPS:.0f} bps)"
    )
    typer.echo(f"registrado: {run_dir.name} -> {run_dir}")
