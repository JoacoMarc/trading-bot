"""Registro de experimentos (ADR-0006): artefactos por corrida y `REGISTRY.md` regenerado.

```
experiments/runs/EXP-0007-ema_trend-4h/
  config.yaml   config pública congelada (sin secretos; recargable con BotConfig.load)
  metrics.json  {"id", "kind", "label", "metrics", "benchmarks", "meta"}
  trades.csv    equity.csv    equity.png    REPORT.md (+ analysis.md opcional, Fase 9)
```
`REGISTRY.md` **no se edita a mano**: `sync_registry` lo regenera desde `runs/*/metrics.json`
tomando el veredicto de la sección "Notas y veredicto" de cada `REPORT.md`.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from tradingbot import __version__
from tradingbot.domain.errors import DataError
from tradingbot.persistence.files import atomic_write_text

RUNS_DIRNAME = "runs"
REGISTRY_FILENAME = "REGISTRY.md"
KINDS = ("EXP", "WF", "OPT", "PAR")
_ID_RE = re.compile(r"^(?P<kind>[A-Z]+)-(?P<num>\d{4})(?:-(?P<slug>.+))?$")
_VERDICT_RE = re.compile(r"^\s*-\s*\*\*Veredicto\*\*\s*:\s*(?P<value>.+?)\s*$", re.MULTILINE)
_SLUG_RE = re.compile(r"[^a-z0-9_]+")

REGISTRY_HEADER = (
    "# Registro de experimentos\n\n"
    "Índice de todas las corridas registradas. **No se edita a mano**: lo regenera "
    "`tradingbot experiments sync` a partir de `runs/*/metrics.json` y de la sección "
    '"Notas y veredicto" de cada `REPORT.md`. Prefijos: `EXP-` backtest · `WF-` walk-forward · '
    "`OPT-` optimización · `PAR-` paridad paper/backtest.\n\n"
    "Holdout reservado: desde 2025-09-01 (ver `docs/GATES.md`). Ninguna corrida lo incluye "
    'salvo que la columna "Datos" diga `+holdout`.\n\n'
    "| Id | Fecha | Estrategia | Params (hash) | Datos | Pares | TF | Retorno | Sharpe | "
    "Max DD | Trades | Veredicto |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
)


@dataclass(frozen=True, slots=True)
class ExperimentMeta:
    created_at: str
    git_sha: str
    git_dirty: bool
    data_hash: str
    host: str
    python: str
    tradingbot_version: str
    duration_s: float
    strategy: str
    timeframe: str
    pairs: list[str]
    start: str | None
    end: str | None
    include_holdout: bool
    params_hash: str
    extra: dict[str, Any] = field(default_factory=dict)


def slugify(text: str, max_length: int = 40) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug[:max_length].rstrip("-") or "run"


def parse_run_id(name: str) -> tuple[str, int, str | None] | None:
    match = _ID_RE.match(name)
    if not match:
        return None
    return match.group("kind"), int(match.group("num")), match.group("slug")


def next_run_id(runs_dir: Path, kind: str) -> str:
    if kind not in KINDS:
        msg = f"tipo de corrida desconocido {kind!r}; válidos: {', '.join(KINDS)}"
        raise ValueError(msg)
    highest = 0
    if runs_dir.exists():
        for child in runs_dir.iterdir():
            parsed = parse_run_id(child.name)
            if parsed and parsed[0] == kind:
                highest = max(highest, parsed[1])
    return f"{kind}-{highest + 1:04d}"


def params_hash(params: Mapping[str, Any]) -> str:
    payload = json.dumps(params, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:10]


def data_hash(paths: Iterable[Path]) -> str:
    """sha256 del contenido de los parquet usados (orden estable), 12 hex."""
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode("utf-8"))
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
    return digest.hexdigest()[:12]


def git_info(root: Path) -> tuple[str, bool]:
    """(sha corto, árbol sucio). Sin git o fuera de un repo → ('unknown', True)."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown", True
    return sha, bool(status)


def build_meta(
    *,
    strategy: str,
    timeframe: str,
    pairs: Iterable[str],
    start: str | None,
    end: str | None,
    include_holdout: bool,
    params: Mapping[str, Any],
    data_files: Iterable[Path],
    duration_s: float,
    root: Path,
    extra: Mapping[str, Any] | None = None,
) -> ExperimentMeta:
    sha, dirty = git_info(root)
    return ExperimentMeta(
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        git_sha=sha,
        git_dirty=dirty,
        data_hash=data_hash(data_files),
        host=platform.node(),
        python=platform.python_version(),
        tradingbot_version=__version__,
        duration_s=round(duration_s, 3),
        strategy=strategy,
        timeframe=timeframe,
        pairs=sorted(pairs),
        start=start,
        end=end,
        include_holdout=include_holdout,
        params_hash=params_hash(params),
        extra=dict(extra or {}),
    )


@dataclass(frozen=True, slots=True)
class RunArtifacts:
    run_id: str
    kind: str
    label: str
    config: Mapping[str, Any]
    metrics: Mapping[str, Any]
    benchmarks: Mapping[str, Mapping[str, Any]]
    meta: ExperimentMeta
    report_md: str
    trades_csv: str
    equity_csv: str
    equity_png: bytes | None = None


def write_run(experiments_dir: Path, artifacts: RunArtifacts) -> Path:
    """Escribe la carpeta de la corrida (falla si ya existe) y regenera el registro."""
    runs_dir = experiments_dir / RUNS_DIRNAME
    run_dir = runs_dir / f"{artifacts.run_id}-{slugify(artifacts.label)}"
    if run_dir.exists():
        msg = f"la corrida {run_dir.name} ya existe; las corridas registradas no se sobreescriben"
        raise DataError(msg)
    run_dir.mkdir(parents=True)
    atomic_write_text(
        run_dir / "config.yaml",
        yaml.safe_dump(dict(artifacts.config), sort_keys=True, allow_unicode=True),
    )
    payload = {
        "id": artifacts.run_id,
        "kind": artifacts.kind,
        "label": artifacts.label,
        "metrics": dict(artifacts.metrics),
        "benchmarks": {k: dict(v) for k, v in artifacts.benchmarks.items()},
        "meta": asdict(artifacts.meta),
    }
    atomic_write_text(
        run_dir / "metrics.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    )
    atomic_write_text(run_dir / "trades.csv", artifacts.trades_csv)
    atomic_write_text(run_dir / "equity.csv", artifacts.equity_csv)
    atomic_write_text(run_dir / "REPORT.md", artifacts.report_md)
    if artifacts.equity_png is not None:
        (run_dir / "equity.png").write_bytes(artifacts.equity_png)
    sync_registry(experiments_dir)
    return run_dir


@dataclass(frozen=True, slots=True)
class RunSummary:
    run_id: str
    kind: str
    label: str
    path: Path
    metrics: dict[str, Any]
    benchmarks: dict[str, dict[str, Any]]
    meta: dict[str, Any]
    verdict: str

    @property
    def number(self) -> int:
        parsed = parse_run_id(self.run_id)
        return parsed[1] if parsed else 0


def read_verdict(report_path: Path) -> str:
    if not report_path.exists():
        return "pendiente"
    match = _VERDICT_RE.search(report_path.read_text(encoding="utf-8"))
    if not match:
        return "pendiente"
    value = match.group("value").strip()
    return (
        value
        if value and value.lower() not in {"go | no-go | iterar", "pendiente"}
        else "pendiente"
    )


def load_runs(experiments_dir: Path) -> list[RunSummary]:
    runs_dir = experiments_dir / RUNS_DIRNAME
    summaries: list[RunSummary] = []
    if not runs_dir.exists():
        return summaries
    for child in sorted(runs_dir.iterdir()):
        metrics_path = child / "metrics.json"
        if not child.is_dir() or not metrics_path.exists():
            continue
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        summaries.append(
            RunSummary(
                run_id=str(payload["id"]),
                kind=str(payload.get("kind", "EXP")),
                label=str(payload.get("label", "")),
                path=child,
                metrics=dict(payload.get("metrics", {})),
                benchmarks={k: dict(v) for k, v in payload.get("benchmarks", {}).items()},
                meta=dict(payload.get("meta", {})),
                verdict=read_verdict(child / "REPORT.md"),
            )
        )
    summaries.sort(key=lambda s: (KINDS.index(s.kind) if s.kind in KINDS else 99, s.number))
    return summaries


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:+.1f} %"
    except (TypeError, ValueError):
        return "—"


def _fmt_num(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def registry_row(summary: RunSummary) -> str:
    meta, metrics = summary.meta, summary.metrics
    data = f"{meta.get('start') or '…'} → {meta.get('end') or '…'}"
    if meta.get("include_holdout"):
        data += " +holdout"
    pairs = ", ".join(p.replace("/USDT", "") for p in meta.get("pairs", []))
    created = str(meta.get("created_at", ""))[:10]
    # `*` = corrida con árbol de git sucio: no citable como evidencia final (ADR-0006).
    run_id = f"{summary.run_id}*" if meta.get("git_dirty") else summary.run_id
    cells = [
        run_id,
        created,
        str(meta.get("strategy", "")),
        str(meta.get("params_hash", "")),
        data,
        pairs,
        str(meta.get("timeframe", "")),
        _fmt_pct(metrics.get("total_return")),
        _fmt_num(metrics.get("sharpe")),
        _fmt_pct(metrics.get("max_drawdown")),
        str(metrics.get("trades", "—")),
        summary.verdict,
    ]
    return "| " + " | ".join(cells) + " |"


def render_registry(summaries: list[RunSummary]) -> str:
    rows = [registry_row(s) for s in summaries] or [
        "| — | — | — | — | — | — | — | — | — | — | — | Sin corridas todavía |"
    ]
    return REGISTRY_HEADER + "\n".join(rows) + "\n"


def sync_registry(experiments_dir: Path) -> Path:
    path = experiments_dir / REGISTRY_FILENAME
    atomic_write_text(path, render_registry(load_runs(experiments_dir)))
    return path
