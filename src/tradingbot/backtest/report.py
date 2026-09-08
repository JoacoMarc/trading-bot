"""Reporte de una corrida: `REPORT.md` (plantilla de `experiments/TEMPLATE_REPORT.md`),
`equity.png` (equity normalizada + drawdown), `trades.csv` y `equity.csv`."""

from __future__ import annotations

import csv
import io
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from tradingbot.backtest.metrics import EquityPoint, Metrics, yearly_breakdown
from tradingbot.domain.money import ZERO
from tradingbot.domain.positions import Trade


@dataclass(frozen=True, slots=True)
class ReportContext:
    run_id: str
    title: str
    strategy: str
    spec_path: str | None
    params: Mapping[str, Any]
    data_line: str
    costs_line: str
    risk_line: str
    reproducibility_line: str
    metrics: Metrics
    benchmarks: Mapping[str, Metrics]
    equity: Sequence[EquityPoint]
    trades: Sequence[Trade]
    events: Sequence[tuple[str, int]] = ()  # (kind/reason, count)
    notes: str = ""


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M")


def _pct(value: Decimal | float | None) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:+.2f} %"


def _num(value: float | Decimal | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def _money(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}"


def metrics_table(metrics: Metrics, benchmarks: Mapping[str, Metrics]) -> str:
    columns = ["Estrategia", *benchmarks]
    rows: list[tuple[str, list[str]]] = [
        ("Retorno total", [_pct(m.total_return) for m in (metrics, *benchmarks.values())]),
        ("CAGR", [_pct(m.cagr) for m in (metrics, *benchmarks.values())]),
        ("Sharpe (diario)", [_num(m.sharpe) for m in (metrics, *benchmarks.values())]),
        ("Sortino (diario)", [_num(m.sortino) for m in (metrics, *benchmarks.values())]),
        ("Calmar", [_num(m.calmar) for m in (metrics, *benchmarks.values())]),
        (
            "Max drawdown / mayor tramo bajo agua",
            [
                f"{_pct(m.max_drawdown)} / {m.longest_underwater_days:.0f} d"
                for m in (metrics, *benchmarks.values())
            ],
        ),
        ("Profit factor", [_num(m.profit_factor) for m in (metrics, *benchmarks.values())]),
        ("Win rate", [_pct(m.win_rate) for m in (metrics, *benchmarks.values())]),
        ("Expectancy por trade", [_money(m.expectancy) for m in (metrics, *benchmarks.values())]),
        (
            "Trades / duración media",
            [
                f"{m.trades} / {_num(m.avg_trade_hours, 1)} h"
                for m in (metrics, *benchmarks.values())
            ],
        ),
        ("Exposición", [_pct(m.exposure) for m in (metrics, *benchmarks.values())]),
        (
            "Fees pagados / shortfall medio",
            [
                f"{_money(m.fees_quote)} / {_num(m.avg_shortfall_bps, 1)} bps"
                for m in (metrics, *benchmarks.values())
            ],
        ),
    ]
    header = "| Métrica | " + " | ".join(columns) + " |\n|---|" + "---|" * len(columns) + "\n"
    body = "\n".join(f"| {name} | " + " | ".join(values) + " |" for name, values in rows)
    return header + body + "\n"


def _trades_table(trades: Sequence[Trade]) -> str:
    if not trades:
        return "_Sin trades._\n"
    lines = ["| Par | Entrada | Salida | Motivo | PnL | PnL % |", "|---|---|---|---|---|---|"]
    for t in trades:
        lines.append(
            f"| {t.pair.symbol} | {_iso(t.entry_time)} @ {t.entry_price} | "
            f"{_iso(t.exit_time)} @ {t.exit_price} | {t.exit_reason.value} | "
            f"{_money(t.pnl)} | {_pct(t.pnl_pct)} |"
        )
    return "\n".join(lines) + "\n"


def render_report(ctx: ReportContext) -> str:
    m = ctx.metrics
    params = "\n".join(f"| `{k}` | `{v}` |" for k, v in sorted(ctx.params.items())) or "| — | — |"
    years = yearly_breakdown(ctx.equity, ctx.trades)
    year_rows = "\n".join(
        f"| {r['year']} | {_pct(r['return'])} | {_pct(r['max_drawdown'])} | {r['trades']} | "
        f"{_money(Decimal(r['pnl']))} |"
        for r in years
    )
    by_pair: dict[str, list[Trade]] = {}
    for t in ctx.trades:
        by_pair.setdefault(t.pair.symbol, []).append(t)
    pair_rows = (
        "\n".join(
            f"| {pair} | {len(ts)} | {_money(sum((t.pnl for t in ts), ZERO))} | "
            f"{_pct(sum(1 for t in ts if t.pnl > ZERO) / len(ts))} |"
            for pair, ts in sorted(by_pair.items())
        )
        or "| — | 0 | — | — |"
    )
    ordered = sorted(ctx.trades, key=lambda t: t.pnl)
    worst, best = ordered[:5], list(reversed(ordered[-5:]))
    exits = Counter(t.exit_reason.value for t in ctx.trades)
    exit_rows = "\n".join(f"| {k} | {v} |" for k, v in sorted(exits.items())) or "| — | 0 |"
    event_rows = "\n".join(f"| {k} | {v} |" for k, v in ctx.events) or "| — | 0 |"
    spec = f"`{ctx.spec_path}`" if ctx.spec_path else "—"
    range_line = (
        f"Rango: {_iso(m.start_ts)} → {_iso(m.end_ts)} UTC ({m.days:.0f} días, {m.bars} velas). "
        f"Equity inicial {_money(m.initial_equity)} → final {_money(m.final_equity)} USDT."
    )

    return f"""# {ctx.run_id} — {ctx.title}

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `{ctx.strategy}` · spec: {spec}
- Datos: {ctx.data_line}
- Costos: {ctx.costs_line}
- Riesgo: {ctx.risk_line}
- Reproducibilidad: {ctx.reproducibility_line}

| Parámetro | Valor |
|---|---|
{params}

## Métricas

{metrics_table(m, ctx.benchmarks)}
{range_line}

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
{year_rows or "| — | — | — | — | — |"}

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
{pair_rows}

### Motivos de salida

| Motivo | Trades |
|---|---|
{exit_rows}

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
{event_rows}

### Peores 5 trades

{_trades_table(worst)}
### Mejores 5 trades

{_trades_table(best)}
## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: pendiente
- **Por qué**: {ctx.notes or ""}
- **Qué se aprendió**:
- **Siguiente experimento propuesto**:
"""


def trades_csv(trades: Sequence[Trade]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "pair",
            "strategy",
            "entry_time",
            "entry_price",
            "exit_time",
            "exit_price",
            "exit_reason",
            "qty",
            "fees_quote",
            "pnl",
            "pnl_pct",
            "duration_hours",
            "entry_client_order_id",
            "exit_client_order_id",
        ]
    )
    for t in trades:
        writer.writerow(
            [
                t.pair.symbol,
                t.strategy,
                _iso(t.entry_time),
                str(t.entry_price),
                _iso(t.exit_time),
                str(t.exit_price),
                t.exit_reason.value,
                str(t.qty),
                str(t.fees_quote),
                str(t.pnl),
                f"{float(t.pnl_pct):.6f}",
                f"{t.duration_ms / 3_600_000:.2f}",
                t.entry_client_order_id,
                t.exit_client_order_id,
            ]
        )
    return buffer.getvalue()


def equity_csv(
    equity: Sequence[EquityPoint], benchmarks: Mapping[str, Sequence[EquityPoint]]
) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    names = list(benchmarks)
    writer.writerow(["ts", "datetime_utc", "equity", *names])
    lookups = {name: dict(points) for name, points in benchmarks.items()}
    last: dict[str, Decimal] = {}
    for ts, value in equity:
        row: list[str] = [str(ts), _iso(ts), str(value)]
        for name in names:
            if ts in lookups[name]:
                last[name] = lookups[name][ts]
            row.append(str(last[name]) if name in last else "")
        writer.writerow(row)
    return buffer.getvalue()


def plot_equity(
    equity: Sequence[EquityPoint],
    benchmarks: Mapping[str, Sequence[EquityPoint]],
    title: str,
) -> bytes:
    """PNG con equity normalizada (base 100) de la estrategia y los benchmarks, y el drawdown."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def normalized(points: Sequence[EquityPoint]) -> tuple[list[datetime], list[float]]:
        base = float(points[0][1]) if points and points[0][1] > ZERO else 1.0
        xs = [datetime.fromtimestamp(ts / 1000, tz=UTC) for ts, _ in points]
        ys = [float(v) / base * 100.0 for _, v in points]
        return xs, ys

    fig, (ax_equity, ax_dd) = plt.subplots(
        2, 1, figsize=(11, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    xs, ys = normalized(equity)
    ax_equity.plot(xs, ys, label="estrategia", linewidth=1.4)
    for name, points in benchmarks.items():
        bx, by = normalized(points)
        ax_equity.plot(bx, by, label=name, linewidth=1.0, alpha=0.8)
    ax_equity.set_ylabel("equity (base 100)")
    ax_equity.set_title(title)
    ax_equity.grid(alpha=0.3)
    ax_equity.legend(loc="upper left")

    peak = 0.0
    dd: list[float] = []
    for y in ys:
        peak = max(peak, y)
        dd.append((y / peak - 1.0) * 100.0 if peak > 0 else 0.0)
    ax_dd.fill_between(xs, dd, 0.0, color="tab:red", alpha=0.35)
    ax_dd.set_ylabel("drawdown %")
    ax_dd.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110)
    plt.close(fig)
    return buffer.getvalue()
