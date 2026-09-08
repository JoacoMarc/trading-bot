# ADR-0006: Registro de experimentos como artefactos versionados

- Estado: aceptado
- Fecha: 2026-09-08
- Fase: 4

## Contexto

Una estrategia se acepta o descarta por evidencia acumulada a lo largo de meses: backtests, walk-forwards, optimizaciones y comparaciones paper/backtest. freqtrade guarda resultados en JSON sueltos sin historial ni veredicto; con eso es fácil re-correr lo mismo, perder el contexto de por qué se descartó una variante o comparar corridas con datos o costos distintos sin darse cuenta. El principio 5 del plan pide que cada corrida quede registrada con metadatos de reproducibilidad y un veredicto humano.

## Decisión

- Toda corrida se ejecuta por CLI (`tradingbot backtest | benchmark | walkforward | optimize | parity`) y se registra automáticamente en `experiments/runs/<ID>-<slug>/` con:
  - `config.yaml`: la configuración pública congelada (`BotConfig.public_dump()`, sin secretos), recargable con `BotConfig.load(overrides=...)`. **Nunca se edita.**
  - `metrics.json`: `{"id", "kind", "label", "metrics", "benchmarks", "meta"}`. El bloque `metrics` es el comparable (Decimal como string, ratios como float); `meta` lleva git sha (+ flag de árbol sucio), hash de los parquet usados, hash de parámetros, host, duración, versión, rango y si incluye holdout.
  - `trades.csv`, `equity.csv` (con los benchmarks), `equity.png` (equity base 100 + drawdown).
  - `REPORT.md`: autogenerado desde `experiments/TEMPLATE_REPORT.md`; la sección **Notas y veredicto** es la única que se escribe a mano (usuario o `backtest-analyst`), con `- **Veredicto**: go | no-go | iterar`.
- IDs por tipo con numeración propia: `EXP-` backtest y benchmarks, `WF-` walk-forward, `OPT-` optimización, `PAR-` paridad paper/backtest. El siguiente número se toma del directorio; una corrida existente jamás se sobreescribe.
- `experiments/REGISTRY.md` es una vista: `tradingbot experiments sync` lo regenera desde `runs/*/metrics.json` y los veredictos. No se edita a mano.
- Los benchmarks buy & hold se calculan aparte del `Engine` (`backtest/benchmark.py`) con los mismos costos, y acompañan a cada backtest en el reporte; además se registran como corridas propias (EXP-0001 BTC, EXP-0002 equiponderado) para que el registro tenga la referencia explícita.
- Sin base de datos para experimentos en v1: los artefactos en disco son la fuente de verdad y se versionan en git (los PNG pesan ~100 KB; el límite de pre-commit es 2 MB por archivo).

## Alternativas consideradas

- **SQLite de experimentos** (`experiments.db`): duplica `metrics.json` y mete un binario en una carpeta versionada; el revisor de la Fase 4 del plan lo marcó como sobreingeniería. Queda en backlog si el registro supera las decenas de corridas.
- **Un solo JSON acumulativo**: conflictos al mergear y sin lugar natural para el reporte y los CSV.
- **No registrar benchmarks como corridas**: dejaría el registro sin línea base visible.

## Consecuencias

- Reproducibilidad verificable: mismo `config.yaml` + mismo hash de datos → mismo bloque `metrics` (test de la Fase 4 con `rtol 1e-9`).
- Reglas duras (`CLAUDE.md` 6): experimentos solo por CLI; no editar `config.yaml` registrado; `REGISTRY.md` regenerado.
- Cada corrida agrega ~150–400 KB al repo (CSV + PNG). Si molesta, se puede gitignorar `equity.png` y regenerarlo desde `equity.csv`.
- El campo `git_dirty` avisa cuando una corrida se hizo con cambios sin commitear en archivos **trackeados** (los artefactos nuevos de otras corridas no cuentan): esas corridas se marcan con `*` en el REGISTRY y no son citables como evidencia final. Flujo: commit del código → corridas → commit de los artefactos.
