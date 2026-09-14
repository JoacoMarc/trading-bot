"""Paridad paper ↔ backtest (ADR-0011; criterio del Gate 2 en `docs/GATES.md`).

Re-ejecuta el backtest sobre el período del paper con la misma config y compara **orden a orden**
por `client_order_id` (determinístico: misma decisión → mismo id) y **fill a fill** (precio del
paper vs precio del backtest, en bps, con signo positivo = peor para nosotros). El resultado se
registra como `PAR-NNNN` en `experiments/runs/`.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from tradingbot.backtest.runner import (
    BacktestRun,
    costs_line,
    frozen_config,
    risk_line,
    run_backtest,
)
from tradingbot.config.models import BacktestConfig
from tradingbot.config.settings import BotConfig
from tradingbot.domain.enums import Side
from tradingbot.domain.orders import Fill, Order
from tradingbot.persistence.experiments import (
    RUNS_DIRNAME,
    RunArtifacts,
    build_meta,
    next_run_id,
    write_run,
)
from tradingbot.persistence.sqlite import SqliteStore

SIGNAL_MATCH_MIN = 0.95
FILL_DEVIATION_MAX_BPS = 15.0
_BPS = Decimal(10_000)


def _bps(numerator: Decimal, denominator: Decimal) -> float:
    return float(numerator / denominator * _BPS) if denominator else 0.0


@dataclass(frozen=True, slots=True)
class FillMatch:
    client_order_id: str
    pair: str
    side: Side
    paper_price: Decimal
    backtest_price: Decimal
    paper_ref: Decimal
    backtest_ref: Decimal
    paper_ts: int
    backtest_ts: int

    @property
    def deviation_bps(self) -> float:
        """Precio del paper vs el del backtest; positivo = peor para nosotros."""
        diff = self.paper_price - self.backtest_price
        if self.side is Side.SELL:
            diff = -diff
        return _bps(diff, self.backtest_price)

    @property
    def ref_deviation_bps(self) -> float:
        """Diferencia del precio de referencia (open) entre paper y backtest, con signo."""
        return _bps(self.paper_ref - self.backtest_ref, self.backtest_ref)


@dataclass(frozen=True, slots=True)
class ParityResult:
    start_ms: int
    end_ms: int
    paper_ids: tuple[str, ...]
    backtest_ids: tuple[str, ...]
    matched: tuple[FillMatch, ...]
    only_paper: tuple[str, ...]
    only_backtest: tuple[str, ...]
    paper_trades: int
    backtest_trades: int

    @property
    def common_ids(self) -> int:
        return len(set(self.paper_ids) & set(self.backtest_ids))

    @property
    def signal_match_rate(self) -> float:
        union = set(self.paper_ids) | set(self.backtest_ids)
        return 1.0 if not union else self.common_ids / len(union)

    @property
    def mean_deviation_bps(self) -> float:
        return (
            sum(m.deviation_bps for m in self.matched) / len(self.matched) if self.matched else 0.0
        )

    @property
    def mean_abs_deviation_bps(self) -> float:
        if not self.matched:
            return 0.0
        return sum(abs(m.deviation_bps) for m in self.matched) / len(self.matched)

    @property
    def max_abs_deviation_bps(self) -> float:
        return max((abs(m.deviation_bps) for m in self.matched), default=0.0)

    @property
    def mean_ref_deviation_bps(self) -> float:
        if not self.matched:
            return 0.0
        return sum(abs(m.ref_deviation_bps) for m in self.matched) / len(self.matched)

    @property
    def passes_gate2(self) -> bool:
        return (
            self.signal_match_rate >= SIGNAL_MATCH_MIN
            and self.mean_abs_deviation_bps <= FILL_DEVIATION_MAX_BPS
        )

    def to_metrics(self) -> dict[str, Any]:
        return {
            "signal_match_rate": self.signal_match_rate,
            "orders_paper": len(self.paper_ids),
            "orders_backtest": len(self.backtest_ids),
            "orders_common": self.common_ids,
            "orders_only_paper": len(self.only_paper),
            "orders_only_backtest": len(self.only_backtest),
            "fills_matched": len(self.matched),
            "mean_deviation_bps": self.mean_deviation_bps,
            "mean_abs_deviation_bps": self.mean_abs_deviation_bps,
            "max_abs_deviation_bps": self.max_abs_deviation_bps,
            "mean_ref_deviation_bps": self.mean_ref_deviation_bps,
            "trades_paper": self.paper_trades,
            "trades_backtest": self.backtest_trades,
            "gate2_parity": self.passes_gate2,
        }


def compare(
    paper_orders: Sequence[Order],
    paper_fills: Sequence[Fill],
    backtest_orders: Sequence[Order],
    backtest_fills: Sequence[Fill],
    *,
    start_ms: int,
    end_ms: int,
    paper_trades: int = 0,
    backtest_trades: int = 0,
) -> ParityResult:
    """Cruza órdenes por `client_order_id` dentro de `[start_ms, end_ms)` (por `created_ts`)."""

    def ids_in_range(orders: Sequence[Order]) -> tuple[str, ...]:
        return tuple(
            sorted({o.client_order_id for o in orders if start_ms <= o.created_ts < end_ms})
        )

    def first_fill(fills: Sequence[Fill]) -> dict[str, Fill]:
        out: dict[str, Fill] = {}
        for fill in fills:
            out.setdefault(fill.client_order_id, fill)
        return out

    paper_ids = ids_in_range(paper_orders)
    backtest_ids = ids_in_range(backtest_orders)
    paper_by_id = first_fill(paper_fills)
    backtest_by_id = first_fill(backtest_fills)
    matched: list[FillMatch] = []
    for cid in sorted(set(paper_ids) & set(backtest_ids)):
        p, b = paper_by_id.get(cid), backtest_by_id.get(cid)
        if p is None or b is None:
            continue
        matched.append(
            FillMatch(
                client_order_id=cid,
                pair=p.pair.symbol,
                side=p.side,
                paper_price=p.price,
                backtest_price=b.price,
                paper_ref=p.ref_price,
                backtest_ref=b.ref_price,
                paper_ts=p.fill_ts,
                backtest_ts=b.fill_ts,
            )
        )
    return ParityResult(
        start_ms=start_ms,
        end_ms=end_ms,
        paper_ids=paper_ids,
        backtest_ids=backtest_ids,
        matched=tuple(matched),
        only_paper=tuple(sorted(set(paper_ids) - set(backtest_ids))),
        only_backtest=tuple(sorted(set(backtest_ids) - set(paper_ids))),
        paper_trades=paper_trades,
        backtest_trades=backtest_trades,
    )


def backtest_config_for(config: BotConfig, start: date, end: date) -> BotConfig:
    """La misma config sobre el rango del paper. El período puede caer en el holdout: la paridad
    compara mecánica, no evalúa el edge, así que `include_holdout` va en True."""
    backtest = BacktestConfig.model_validate(
        {
            **config.backtest.model_dump(mode="json"),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "include_holdout": True,
        }
    )
    return config.model_copy(update={"backtest": backtest})


def _matches_csv(result: ParityResult) -> str:
    lines = [
        "client_order_id,pair,side,paper_price,backtest_price,deviation_bps,paper_ref,"
        "backtest_ref,ref_deviation_bps,paper_fill_ts,backtest_fill_ts"
    ]
    for m in result.matched:
        lines.append(
            f"{m.client_order_id},{m.pair},{m.side.value},{m.paper_price},{m.backtest_price},"
            f"{m.deviation_bps:.2f},{m.paper_ref},{m.backtest_ref},{m.ref_deviation_bps:.2f},"
            f"{m.paper_ts},{m.backtest_ts}"
        )
    return "\n".join(lines) + "\n"


def render_report(
    run_id: str, result: ParityResult, config: BotConfig, db_path: Path, run: BacktestRun
) -> str:
    ok = "OK" if result.signal_match_rate >= SIGNAL_MATCH_MIN else "FALLA"
    ok_dev = "OK" if result.mean_abs_deviation_bps <= FILL_DEVIATION_MAX_BPS else "FALLA"
    lines = [
        f"# {run_id} — paridad paper ↔ backtest {config.strategy.name} {config.strategy.timeframe.value}",
        "",
        "> Sección autogenerada por `tradingbot parity`. Solo **Notas y veredicto** se escribe a mano.",
        "",
        "## Configuración",
        "",
        f"- DB del paper: `{db_path}` · pares {', '.join(p.symbol for p in config.strategy.pairs)}",
        f"- Backtest de referencia sobre el mismo rango: {run.start_ms} → {run.end_ms} "
        f"({run.metrics.trades} trades, warmup {run.warmup})",
        f"- Costos: {costs_line(config)}",
        f"- Riesgo: {risk_line(config)}",
        "",
        "## Resultado",
        "",
        "| Métrica | Valor | Umbral (Gate 2) | Resultado |",
        "|---|---|---|---|",
        f"| Señales coincidentes (ids comunes / unión) | {result.signal_match_rate * 100:.1f} % "
        f"({result.common_ids} / {len(set(result.paper_ids) | set(result.backtest_ids))}) | "
        f">= {SIGNAL_MATCH_MIN * 100:.0f} % | {ok} |",
        f"| Desvío medio absoluto del fill | {result.mean_abs_deviation_bps:.2f} bps | "
        f"<= {FILL_DEVIATION_MAX_BPS:.0f} bps | {ok_dev} |",
        f"| Desvío medio con signo (positivo = peor) | {result.mean_deviation_bps:+.2f} bps | — | — |",
        f"| Desvío máximo absoluto | {result.max_abs_deviation_bps:.2f} bps | — | — |",
        f"| Desvío medio del precio de referencia (open) | {result.mean_ref_deviation_bps:.2f} bps "
        "| — | — |",
        f"| Órdenes paper / backtest | {len(result.paper_ids)} / {len(result.backtest_ids)} | — | — |",
        f"| Solo en paper / solo en backtest | {len(result.only_paper)} / {len(result.only_backtest)} "
        "| — | — |",
        f"| Trades cerrados paper / backtest | {result.paper_trades} / {result.backtest_trades} | — | — |",
        "",
        f"Gate 2 (paridad): **{'aprobado' if result.passes_gate2 else 'no aprobado'}**.",
        "",
    ]
    if result.only_paper or result.only_backtest:
        lines += ["## Órdenes sin par", ""]
        for cid in result.only_paper[:20]:
            lines.append(f"- solo paper: `{cid}`")
        for cid in result.only_backtest[:20]:
            lines.append(f"- solo backtest: `{cid}`")
        lines.append("")
    if result.matched:
        lines += [
            "## Fills cruzados (primeros 50)",
            "",
            "| Orden | Lado | Paper | Backtest | Desvío bps | Ref paper | Ref backtest |",
            "|---|---|---|---|---|---|---|",
        ]
        for m in result.matched[:50]:
            lines.append(
                f"| `{m.client_order_id}` | {m.side.value} | {m.paper_price} | {m.backtest_price} | "
                f"{m.deviation_bps:+.2f} | {m.paper_ref} | {m.backtest_ref} |"
            )
        lines.append("")
    lines += [
        "## Notas y veredicto",
        "",
        "- **Veredicto**: pendiente",
        "- **Por qué**:",
        "- **Qué se aprendió**:",
        "- **Siguiente experimento propuesto**:",
        "",
    ]
    return "\n".join(lines)


def run_parity(
    config: BotConfig,
    db_path: Path,
    start: date,
    end: date,
    *,
    experiments_dir: Path,
    root: Path,
    label: str | None = None,
) -> tuple[ParityResult, Path]:
    """Compara la DB del paper con el backtest del mismo rango y registra un `PAR-`."""
    started = time.perf_counter()
    with SqliteStore(db_path) as store:
        paper_orders = store.orders()
        paper_fills = store.fills()
        paper_trades = len(store.trades())
    cfg = backtest_config_for(config, start, end)
    run = run_backtest(cfg, with_benchmarks=False)
    backtest_store = run.engine_result.store
    result = compare(
        paper_orders,
        paper_fills,
        backtest_store.orders(),
        backtest_store.fills(),
        start_ms=run.start_ms,
        end_ms=run.end_ms,
        paper_trades=paper_trades,
        backtest_trades=run.metrics.trades,
    )
    run_id = next_run_id(experiments_dir / RUNS_DIRNAME, "PAR")
    meta = build_meta(
        strategy=config.strategy.name,
        timeframe=config.strategy.timeframe.value,
        pairs=[p.symbol for p in config.strategy.pairs],
        start=start.isoformat(),
        end=end.isoformat(),
        include_holdout=True,
        params=dict(run.strategy.params.model_dump(mode="json")),
        data_files=run.data_files,
        duration_s=time.perf_counter() - started,
        root=root,
        extra={"paper_db": str(db_path), "mode": config.mode.value},
    )
    artifacts = RunArtifacts(
        run_id=run_id,
        kind="PAR",
        label=label or f"paridad {config.strategy.name} {start.isoformat()} {end.isoformat()}",
        config=frozen_config(cfg, run.start_ms, run.end_ms),
        metrics=result.to_metrics(),
        benchmarks={},
        meta=meta,
        report_md=render_report(run_id, result, config, db_path, run),
        trades_csv=_matches_csv(result),
        equity_csv="ts,equity\n",
    )
    return result, write_run(experiments_dir, artifacts)
