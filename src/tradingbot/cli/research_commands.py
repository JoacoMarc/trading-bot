"""Dataset, modelos mensuales y predicciones registrados por CLI."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast

import pandas as pd
import typer

from tradingbot.cli.backtest_commands import ConfigOption, _fail, _load_config
from tradingbot.data.store import ParquetStore
from tradingbot.features.market import FEATURE_VERSION, FEATURES, SYMBOLS, feature_frame
from tradingbot.persistence.experiments import (
    RunArtifacts,
    build_meta,
    data_hash,
    next_run_id,
    write_run,
)
from tradingbot.research.dataset import labeled_frame
from tradingbot.research.models import (
    ModelKind,
    digest,
    predict,
    stamp,
    train_month,
    validate_model,
)
from tradingbot.strategy.base import OhlcvArrays

research_app = typer.Typer(no_args_is_help=True)
DirOption = Annotated[Path, typer.Option("--experiments-dir")]


def register_research(
    config: dict[str, Any],
    label: str,
    files: list[Path],
    extra: dict[str, Any],
    *,
    experiments_dir: Path,
    started: float,
) -> Path:
    meta = build_meta(
        strategy=label,
        timeframe="4h",
        pairs=config.get("pairs", []),
        start=config.get("start"),
        end=config.get("end"),
        include_holdout=bool(config.get("include_holdout", False)),
        params=config,
        data_files=files,
        duration_s=time.perf_counter() - started,
        root=Path.cwd(),
        extra=extra,
    )
    return write_run(
        experiments_dir,
        RunArtifacts(
            run_id=next_run_id(experiments_dir / "runs", "RES"),
            kind="RES",
            label=label,
            config=config,
            metrics={},
            benchmarks={},
            meta=meta,
            report_md=(
                f"# {label}\n\nArtefacto de investigación, sin veredicto financiero.\n\n"
                f"```json\n{json.dumps(extra, indent=2)}\n```\n"
            ),
            trades_csv="",
            equity_csv="",
        ),
    )


@research_app.command()
def dataset(
    config: ConfigOption,
    experiments_dir: DirOption = Path("experiments"),
    final_holdout_family: Annotated[str | None, typer.Option("--final-holdout-family")] = None,
) -> None:
    """Features causales y etiquetas24h; excluye holdout y velas sin etiqueta completa."""
    started = time.perf_counter()
    cfg = _load_config(config, {})
    if cfg.backtest.include_holdout and not final_holdout_family:
        _fail(ValueError("holdout exige --final-holdout-family y registro final explícito"))
    if final_holdout_family:
        import re

        if not cfg.backtest.include_holdout or not re.fullmatch(
            r"[a-z0-9_-]{1,40}", final_holdout_family
        ):
            _fail(ValueError("familia holdout inválida o include_holdout desactivado"))
        ledger = experiments_dir / "holdout-consumption" / f"{final_holdout_family}.json"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("x") as handle:
            json.dump(
                {
                    "family": final_holdout_family,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "config": cfg.public_dump(),
                    "previously_observed_other_families": True,
                },
                handle,
            )

    store = ParquetStore(cfg.data.data_dir)
    from tradingbot.backtest.runner import date_to_ms
    from tradingbot.config.models import HOLDOUT_START
    from tradingbot.domain import Pair

    end = date_to_ms(cfg.backtest.effective_end or HOLDOUT_START)
    if not final_holdout_family:
        end = min(end, date_to_ms(HOLDOUT_START))
    arrays = {
        p: OhlcvArrays.from_candles(store.read_candles(p, cfg.strategy.timeframe, end_ms=end))
        for p in cfg.strategy.pairs
    }
    btc = arrays[Pair.parse("BTC/USDT")]
    labeled = pd.concat(
        [labeled_frame(a, btc) for a in arrays.values()], ignore_index=True
    ).sort_values(["signal_ts", "pair"])
    # Inferencia incluye también cierres aún sin etiqueta; la etiqueta jamás se usa como feature.
    features = pd.concat(
        [feature_frame(a, btc).assign(pair=p.symbol).reset_index() for p, a in arrays.items()],
        ignore_index=True,
    ).sort_values(["signal_ts", "pair"])
    files = [store.path(p, cfg.strategy.timeframe) for p in arrays]
    manifest = {
        "universe": list(SYMBOLS),
        "feature_version": FEATURE_VERSION,
        "features": list(FEATURES),
        "source_start": int(btc.open_time[0]),
        "source_end": end,
        "data_hash": data_hash(files),
        "rows": len(labeled),
        "feature_rows": len(features),
    }
    path = register_research(
        {
            "config": cfg.public_dump(),
            "include_holdout": cfg.backtest.include_holdout,
            "pairs": [p.symbol for p in arrays],
        },
        "ml-dataset",
        files,
        manifest,
        experiments_dir=experiments_dir,
        started=started,
    )
    labeled.to_parquet(path / "dataset.parquet", index=False)
    features.to_parquet(path / "features.parquet", index=False)
    manifest["dataset_sha256"] = hashlib.sha256((path / "dataset.parquet").read_bytes()).hexdigest()
    manifest["features_sha256"] = hashlib.sha256(
        (path / "features.parquet").read_bytes()
    ).hexdigest()
    (path / "manifest.json").write_text(json.dumps(manifest, indent=2))
    typer.echo(path)


def read_dataset(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    manifest = json.loads((path / "manifest.json").read_text())
    if (
        manifest.get("feature_version") != FEATURE_VERSION
        or manifest.get("features") != list(FEATURES)
        or manifest.get("universe") != list(SYMBOLS)
    ):
        raise ValueError("schema de dataset incompatible")
    for name, key in (("dataset", "dataset_sha256"), ("features", "features_sha256")):
        if hashlib.sha256((path / f"{name}.parquet").read_bytes()).hexdigest() != manifest[key]:
            raise ValueError("dataset alterado")
    return (
        pd.read_parquet(path / "dataset.parquet"),
        pd.read_parquet(path / "features.parquet"),
        manifest,
    )


@research_app.command()
def train(
    dataset_dir: Path,
    kind: Annotated[str, typer.Option("--kind")] = "logistic",
    start: Annotated[str, typer.Option("--from")] = "2019-08-01",
    end: Annotated[str, typer.Option("--to")] = "2025-09-01",
    seed: int = 42,
    months: int = 24,
    experiments_dir: DirOption = Path("experiments"),
) -> None:
    """Receta mensual21m+3m; fechas sin modelo quedan registradas como falta de cobertura."""
    if kind not in {"logistic", "lightgbm"}:
        _fail(ValueError("kind: logistic | lightgbm"))
    if months <= 3:
        _fail(ValueError("months debe superar la calibración de3m"))
    started = time.perf_counter()
    frame, _, manifest = read_dataset(dataset_dir)
    cuts = pd.date_range(start=start, end=end, freq="MS", tz="UTC", inclusive="left")
    if len(cuts) == 0 or stamp(cuts[-1]) > manifest["source_end"]:
        _fail(ValueError("rango de entrenamiento inválido"))
    path = register_research(
        {
            "kind": kind,
            "start": start,
            "end": end,
            "seed": seed,
            "months": months,
            "dataset": str(dataset_dir),
        },
        f"ml-train-{kind}",
        [dataset_dir / "dataset.parquet"],
        manifest,
        experiments_dir=experiments_dir,
        started=started,
    )
    schedule = []
    for cut in cuts:
        try:
            model = train_month(
                frame,
                cut,
                cast(ModelKind, kind),
                source_start=manifest["source_start"],
                data_hash=manifest["dataset_sha256"],
                seed=seed,
                months=months,
            )
        except ValueError as exc:
            schedule.append({"cut": stamp(cut), "error": str(exc)})
            continue
        name = f"{cut.strftime('%Y-%m')}.json"
        (path / name).write_text(json.dumps(model))
        schedule.append({"cut": stamp(cut), "file": name, "model_hash": model["model_hash"]})
        typer.echo(
            f"{cut:%Y-%m}: {model['fit_rows']} fit / {model['calibration_rows']} calibración"
        )
    (path / "schedule.json").write_text(
        json.dumps({"dataset_manifest": manifest, "models": schedule}, indent=2)
    )
    typer.echo(path)


@research_app.command("predict")
def predict_command(
    dataset_dir: Path, models_dir: Path, experiments_dir: DirOption = Path("experiments")
) -> None:
    """Replay de artefactos mensuales; nunca aplica el último modelo a fechas pasadas."""
    started = time.perf_counter()
    _, features, manifest = read_dataset(dataset_dir)
    schedule = json.loads((models_dir / "schedule.json").read_text())
    training_manifest = schedule["dataset_manifest"]
    if any(
        training_manifest.get(k) != manifest.get(k)
        for k in ("feature_version", "features", "universe")
    ):
        _fail(ValueError("schema de inferencia incompatible con entrenamiento"))
    chunks = []
    coverage = features[["pair", "signal_ts"]].copy()
    coverage["reason"] = "model_missing"
    models = []
    from sklearn.metrics import brier_score_loss, log_loss

    labeled = pd.read_parquet(dataset_dir / "dataset.parquet")
    for item in schedule["models"]:
        if "file" not in item:
            continue
        model = json.loads((models_dir / item["file"]).read_text())
        validate_model(model, model["available_at"])
        if model["model_hash"] != item["model_hash"]:
            _fail(ValueError("schedule alterado"))
        batch = features.loc[
            (features.signal_ts >= model["available_at"])
            & (features.signal_ts < model["expires_at"])
        ].copy()
        coverage.loc[batch.index, "reason"] = "features_invalid"
        batch = batch.dropna(subset=list(FEATURES))
        coverage.loc[batch.index, "reason"] = "ok"
        models.append(
            {
                k: model[k]
                for k in (
                    "model_hash",
                    "available_at",
                    "expires_at",
                    "cut",
                    "fit_label_end_max",
                    "calibration_label_end_max",
                    "calibration_cut",
                )
            }
        )
        if batch.empty:
            continue
        batch["probability"] = predict(model, batch)
        batch["available_at"] = model["available_at"]
        batch["expires_at"] = model["expires_at"]
        batch["model_hash"] = model["model_hash"]
        chunks.append(
            batch[["pair", "signal_ts", "probability", "available_at", "expires_at", "model_hash"]]
        )
    if not chunks:
        _fail(ValueError("sin modelos válidos"))
    predictions = pd.concat(chunks, ignore_index=True)
    scored = predictions.merge(
        labeled[["pair", "signal_ts", "label"]], on=["pair", "signal_ts"], validate="one_to_one"
    )
    scores = {
        "brier": None
        if scored.empty
        else float(brier_score_loss(scored.label, scored.probability)),
        "log_loss": None
        if scored.empty
        else float(log_loss(scored.label, scored.probability, labels=[0, 1])),
        "scored_rows": len(scored),
    }
    path = register_research(
        {"models": str(models_dir), "dataset": str(dataset_dir)},
        "ml-predictions",
        [models_dir / "schedule.json", dataset_dir / "features.parquet"],
        scores,
        experiments_dir=experiments_dir,
        started=started,
    )
    predictions.to_parquet(path / "predictions.parquet", index=False)
    coverage.to_parquet(path / "coverage.parquet", index=False)
    info = {
        "coverage_sha256": hashlib.sha256((path / "coverage.parquet").read_bytes()).hexdigest(),
        "feature_version": FEATURE_VERSION,
        "models": models,
        "predictions_sha256": hashlib.sha256(
            (path / "predictions.parquet").read_bytes()
        ).hexdigest(),
        "dataset": manifest,
        "training_dataset": training_manifest,
        "created_at": datetime.now(UTC).isoformat(),
        "scores": scores,
    }
    info["manifest_hash"] = digest(info)
    (path / "manifest.json").write_text(json.dumps(info, indent=2))
    typer.echo(path)


@research_app.command()
def publish(model_path: Path, output: Path) -> None:
    """Publica un modelo local vigente para paper, registrando hora efectiva de publicación."""
    from tradingbot.persistence.files import atomic_write_text

    model = json.loads(model_path.read_text())
    now = int(datetime.now(UTC).timestamp() * 1000)
    validate_model(model, now)
    atomic_write_text(output, json.dumps({"model": model, "published_at": now}))
    typer.echo(f"Publicado {model['model_hash']} en {output}")


@research_app.command()
def compare(
    base_run: Path, candidate_run: Path, experiments_dir: DirOption = Path("experiments")
) -> None:
    """Diferencia Sharpe y CI95% por bloques emparejados; ambos deben cubrir los mismos días."""
    from tradingbot.research.comparison import paired_comparison

    started = time.perf_counter()
    files = [base_run / "equity.csv", candidate_run / "equity.csv"]
    result = paired_comparison(pd.read_csv(files[0]), pd.read_csv(files[1]))
    path = register_research(
        {"base": str(base_run), "candidate": str(candidate_run)},
        "paired-comparison",
        files,
        result,
        experiments_dir=experiments_dir,
        started=started,
    )
    (path / "comparison.json").write_text(json.dumps(result, indent=2))
    typer.echo(json.dumps(result, indent=2))
    typer.echo(path)
