"""Comandos de datos de la CLI: `download-data`, `data-info`, `data-check`, `data-markets`.

Trabajan sobre `DataConfig` (defaults del universo v1) sin exigir un YAML de estrategia. El
exchange se construye con `make_exchange`, reemplazable en tests por un cliente falso.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from tradingbot.config.models import DataConfig
from tradingbot.data.downloader import Downloader
from tradingbot.data.quality import Gap, GapRegistry, QualityReport, check_frame
from tradingbot.data.store import ParquetStore
from tradingbot.domain.errors import TradingBotError
from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe
from tradingbot.exchange.binance import (
    BinanceExchange,
    MarketsSnapshot,
    build_markets_snapshot,
    default_snapshot_path,
    load_markets_snapshot,
    save_markets_snapshot,
)

data_app = typer.Typer(add_completion=False)

ExchangeFactory = Callable[[], BinanceExchange]


def make_exchange() -> BinanceExchange:
    """Cliente público de Binance (sin claves: los datos no las necesitan)."""
    return BinanceExchange.create()


# Punto de inyección para tests: `monkeypatch.setattr(data_commands, "exchange_factory", ...)`.
exchange_factory: ExchangeFactory = make_exchange


def _date_to_ms(value: date) -> int:
    return int(datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp() * 1000)


def _ms_to_iso(ts_ms: int | None) -> str:
    if ts_ms is None:
        return "-"
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M")


def _split(values: Sequence[str]) -> list[str]:
    """Acepta la opción repetida (`-p A -p B`) o separada por comas (`-p A,B`)."""
    return [item for value in values for item in value.replace(",", " ").split() if item]


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        msg = f"fecha inválida {value!r}; formato YYYY-MM-DD"
        raise typer.BadParameter(msg) from exc


def _resolve(
    data_dir: Path | None,
    pairs: Sequence[str] | None,
    timeframes: Sequence[str] | None,
    since: str | None = None,
) -> tuple[DataConfig, tuple[Pair, ...], tuple[Timeframe, ...]]:
    overrides: dict[str, Any] = {}
    if data_dir is not None:
        overrides["data_dir"] = data_dir
    if pairs:
        overrides["universe"] = _split(pairs)
    if timeframes:
        overrides["timeframes"] = _split(timeframes)
    if since:
        overrides["since"] = _parse_date(since)
    try:
        cfg = DataConfig(**overrides)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    return cfg, cfg.universe, cfg.timeframes


def _fail(exc: Exception) -> None:
    typer.echo(f"error: {exc}", err=True)
    raise typer.Exit(code=1) from exc


DataDirOption = Annotated[
    Path | None, typer.Option("--data-dir", help="Directorio raíz de datos (default: data).")
]
PairsOption = Annotated[
    list[str] | None,
    typer.Option("--pairs", "-p", help="Pares: -p BTC/USDT,ETH/USDT (default: universo v1)."),
]
TimeframesOption = Annotated[
    list[str] | None,
    typer.Option("--timeframes", "-t", help="Timeframes: -t 1h,4h (default: 1h 4h)."),
]


@data_app.command("download-data")
def download_data(
    data_dir: DataDirOption = None,
    pairs: PairsOption = None,
    timeframes: TimeframesOption = None,
    since: Annotated[
        str | None, typer.Option("--since", help="Desde (YYYY-MM-DD, UTC). Default: 2019-01-01.")
    ] = None,
    until: Annotated[
        str | None, typer.Option("--until", help="Hasta (YYYY-MM-DD, exclusivo). Default: ahora.")
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Solo el resumen final.")] = False,
) -> None:
    """Descarga velas cerradas de Binance de forma incremental e idempotente."""
    cfg, pair_list, tf_list = _resolve(data_dir, pairs, timeframes, since)
    since_ms = _date_to_ms(cfg.since)
    until_ms = _date_to_ms(_parse_date(until)) if until else None
    store = ParquetStore(cfg.data_dir)
    try:
        exchange = exchange_factory()
        markets = exchange.load_markets()
        missing = [p.symbol for p in pair_list if p not in markets]
        if missing:
            msg = f"pares no listados en Binance Spot: {', '.join(missing)}"
            raise TradingBotError(msg)
        snapshot = build_markets_snapshot(exchange, pair_list)
        save_markets_snapshot(snapshot, store.exchange_dir / "markets.json")
        downloader = Downloader(
            exchange, store, progress=None if quiet else lambda m: typer.echo(f"  {m}")
        )
        results = downloader.download_many(pair_list, tf_list, since_ms, until_ms)
    except TradingBotError as exc:
        _fail(exc)
        return
    typer.echo(f"{'par':<10} {'tf':<4} {'nuevas':>7} {'actual.':>7} {'total':>7}  rango")
    for r in results:
        typer.echo(
            f"{r.pair.symbol:<10} {r.timeframe.value:<4} {r.added:>7} {r.updated:>7} "
            f"{r.total_rows:>7}  {_ms_to_iso(r.first_open_time)} -> {_ms_to_iso(r.last_open_time)}"
        )
    typer.echo(f"datos en {store.exchange_dir}")


@data_app.command("data-info")
def data_info(data_dir: DataDirOption = None) -> None:
    """Lista los datasets almacenados con filas, rango y velas faltantes."""
    cfg, _, _ = _resolve(data_dir, None, None)
    store = ParquetStore(cfg.data_dir)
    datasets = store.list_datasets()
    if not datasets:
        typer.echo(f"sin datos en {store.exchange_dir} (correr download-data)")
        return
    typer.echo(f"{'par':<10} {'tf':<4} {'filas':>7} {'faltan':>7} {'MB':>6}  rango")
    for pair, timeframe in datasets:
        info = store.info(pair, timeframe)
        if info is None:
            typer.echo(f"{pair.symbol:<10} {timeframe.value:<4} {'vacío':>7}")
            continue
        typer.echo(
            f"{pair.symbol:<10} {timeframe.value:<4} {info.rows:>7} {info.missing_rows:>7} "
            f"{info.size_bytes / 1_048_576:>6.2f}  "
            f"{_ms_to_iso(info.first_open_time)} -> {_ms_to_iso(info.last_open_time)}"
        )


def _print_report(report: QualityReport, known: list[Gap]) -> bool:
    findings = report.findings(known)
    registered = len(report.gaps) - len(report.unregistered_gaps(known))
    status = "OK  " if not findings else "FAIL"
    extra = f", {registered} huecos registrados" if registered else ""
    head = f"[{status}] {report.pair.symbol:<10} {report.timeframe.value:<4}"
    typer.echo(f"{head} {report.rows} velas{extra}")
    for finding in findings:
        typer.echo(f"       - {finding}")
    return not findings


@data_app.command("data-check")
def data_check(
    data_dir: DataDirOption = None,
    pairs: PairsOption = None,
    timeframes: TimeframesOption = None,
    gaps_file: Annotated[
        Path | None, typer.Option("--gaps-file", help="Registro de huecos conocidos (JSON).")
    ] = None,
    register: Annotated[
        bool,
        typer.Option(
            "--register",
            help=(
                "Verifica cada hueco contra Binance: si el exchange tiene las velas, las guarda; "
                "si no, lo registra como hueco real (revisar antes de commitear)."
            ),
        ),
    ] = False,
) -> None:
    """Chequea huecos, duplicados, alineación y OHLC. Sale con 1 si hay hallazgos no registrados."""
    cfg, pair_list, tf_list = _resolve(data_dir, pairs, timeframes)
    store = ParquetStore(cfg.data_dir)
    gaps_path = gaps_file or cfg.gaps_file
    try:
        registry = GapRegistry.load(gaps_path)
        downloader = Downloader(exchange_factory(), store) if register else None
    except TradingBotError as exc:
        _fail(exc)
        return
    all_ok = True
    newly_registered = filled_total = 0
    for pair in pair_list:
        for timeframe in tf_list:
            if not store.exists(pair, timeframe):
                typer.echo(f"[SKIP] {pair.symbol:<10} {timeframe.value:<4} sin datos")
                continue
            try:
                report = check_frame(store.read(pair, timeframe), pair, timeframe)
                known = registry.known(pair, timeframe)
                if downloader is not None:
                    added, filled = _verify_gaps(
                        downloader, registry, pair, timeframe, report.unregistered_gaps(known)
                    )
                    newly_registered += added
                    filled_total += filled
                    if filled:
                        report = check_frame(store.read(pair, timeframe), pair, timeframe)
                    known = registry.known(pair, timeframe)
            except TradingBotError as exc:
                typer.echo(f"[FAIL] {pair.symbol:<10} {timeframe.value:<4} {exc}")
                all_ok = False
                continue
            all_ok = _print_report(report, known) and all_ok
    if newly_registered:
        registry.save(gaps_path)
        typer.echo(f"{newly_registered} huecos confirmados y agregados a {gaps_path}")
    if filled_total:
        typer.echo(f"{filled_total} velas recuperadas del exchange")
    if not all_ok:
        raise typer.Exit(code=1)


def _verify_gaps(
    downloader: Downloader,
    registry: GapRegistry,
    pair: Pair,
    timeframe: Timeframe,
    gaps: Sequence[Gap],
) -> tuple[int, int]:
    """Re-pide los huecos al exchange. Devuelve (huecos registrados, velas recuperadas)."""
    registered = filled = 0
    stamp = datetime.now(UTC).date().isoformat()
    for result in downloader.fill_gaps(pair, timeframe, gaps):
        if result.confirmed_empty:
            note = f"confirmado vacío en Binance por data-check --register {stamp}"
            if registry.add(pair, timeframe, result.gap, note):
                registered += 1
        else:
            filled += result.filled
    return registered, filled


@data_app.command("data-markets")
def data_markets(
    data_dir: DataDirOption = None,
    pairs: PairsOption = None,
    refresh: Annotated[
        bool, typer.Option("--refresh", help="Consulta Binance en vez de leer el snapshot.")
    ] = False,
    update_snapshot: Annotated[
        bool,
        typer.Option(
            "--update-snapshot",
            help="Con --refresh: sobreescribe el snapshot empaquetado en exchange/.",
        ),
    ] = False,
) -> None:
    """Muestra tick/step/minNotional de los pares del universo (snapshot o Binance en vivo)."""
    cfg, pair_list, _ = _resolve(data_dir, pairs, None)
    store = ParquetStore(cfg.data_dir)
    try:
        if refresh:
            snapshot = build_markets_snapshot(exchange_factory(), pair_list)
            save_markets_snapshot(snapshot, store.exchange_dir / "markets.json")
            if update_snapshot:
                save_markets_snapshot(snapshot, default_snapshot_path())
                typer.echo(f"snapshot actualizado: {default_snapshot_path()}")
        else:
            local = store.exchange_dir / "markets.json"
            snapshot = load_markets_snapshot(local if local.is_file() else None)
    except (TradingBotError, OSError, ValueError) as exc:
        _fail(exc)
        return
    _print_snapshot(snapshot, pair_list)


def _print_snapshot(snapshot: MarketsSnapshot, pair_list: tuple[Pair, ...]) -> None:
    typer.echo(f"fuente: {snapshot.source} ({snapshot.fetched_at})")
    limits = snapshot.rate_limits
    typer.echo(
        f"límites: {limits.request_weight_per_minute} weight/min, "
        f"{limits.orders_per_10s} órdenes/10 s, {limits.orders_per_day} órdenes/día"
    )
    typer.echo(f"{'par':<10} {'tick':>12} {'step':>12} {'minQty':>12} {'minNotional':>12} activo")
    by_pair = snapshot.by_pair()
    for pair in pair_list:
        market = by_pair.get(pair)
        if market is None:
            typer.echo(f"{pair.symbol:<10} {'(no está en el snapshot)':>12}")
            continue
        typer.echo(
            f"{pair.symbol:<10} {market.tick_size:>12f} {market.step_size:>12f} "
            f"{market.min_qty:>12f} {market.min_notional:>12f} {'sí' if market.active else 'no'}"
        )
